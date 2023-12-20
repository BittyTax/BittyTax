# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

# pylint: disable=too-many-branches

import re
from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Nexo"

ASSET_NORMALISE = {
    "BNBN": "BNB",
    "NEXOBNB": "BNB",
    "LUNA2": "LUNA",
    "NEXONEXO": "NEXO",
    # "NEXOBNB": "NEXO",
    "NEXOBEP2": "NEXO",
    "USDTERC": "USDT",
    "UST": "USTC",
}


def parse_nexo(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date / Time"], tz="Europe/Zurich")

    if "rejected" in row_dict["Details"]:
        # Skip failed transactions
        return

    if "Currency" in row_dict:
        if row_dict["Type"] != "Exchange":
            buy_asset = row_dict["Currency"]
            sell_asset = row_dict["Currency"]
        else:
            buy_asset = row_dict["Currency"].split("/")[1]
            sell_asset = row_dict["Currency"].split("/")[0]
    else:
        buy_asset = row_dict["Output Currency"]
        sell_asset = row_dict["Input Currency"]

    for nexo_asset, asset in ASSET_NORMALISE.items():
        buy_asset = buy_asset.replace(nexo_asset, asset)
        sell_asset = sell_asset.replace(nexo_asset, asset)

    if "Amount" in row_dict:
        if row_dict["Type"] != "Exchange":
            buy_quantity = Decimal(row_dict["Amount"])
            sell_quantity = abs(Decimal(row_dict["Amount"]))
        else:
            match = re.match(r"^-(\d+|\d+\.\d+) / \+(\d+|\d+\.\d+)$", row_dict["Amount"])

            if match:
                buy_quantity = Decimal(match.group(2))
                sell_quantity = Decimal(match.group(1))
            else:
                buy_quantity = None
                sell_quantity = None
    else:
        buy_quantity = Decimal(row_dict["Output Amount"])
        sell_quantity = abs(Decimal(row_dict["Input Amount"]))

    if row_dict.get("USD Equivalent") and buy_asset != config.ccy:
        value = DataParser.convert_currency(
            row_dict["USD Equivalent"].strip("$"), "USD", data_row.timestamp
        )
    else:
        value = None

    # Do not handle credit deposits here.
    if (
        row_dict["Type"] in ("Deposit", "Top up Crypto", "ExchangeDepositedOn")
        and row_dict["Details"].find("Credit") == -1
    ):
        if row_dict["Details"].find("Airdrop") > -1:
            t_type = TrType.AIRDROP
        else:
            t_type = TrType.DEPOSIT

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=value,
            wallet=WALLET,
        )
    # Do not handle overdraft interest here.
    elif row_dict["Type"] in ("Dividend", "FixedTermInterest", "Fixed Term Interest") or (
        row_dict["Type"] == "Interest" and row_dict["Details"].find("Overdraft") == -1
    ):
        if buy_quantity is not None and buy_quantity > 0:
            if row_dict["Type"] == "Dividend":
                t_type = TrType.DIVIDEND
            else:
                t_type = TrType.INTEREST

            data_row.t_record = TransactionOutRecord(
                t_type,
                data_row.timestamp,
                buy_quantity=buy_quantity,
                buy_asset=buy_asset,
                buy_value=value,
                wallet=WALLET,
            )
        # Skip interest with zero amounts.
        else:
            return
    elif row_dict["Type"] in (
        "Bonus",
        "Cashback",
        "Exchange Cashback",
        "ReferralBonus",
        "Referral Bonus",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.GIFT_RECEIVED,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=value,
            wallet=WALLET,
        )
    elif row_dict["Type"] in ("Exchange", "CreditCardStatus"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=value,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            sell_value=value,
            wallet=WALLET,
        )
    elif row_dict["Type"] in ("Withdrawal", "WithdrawExchanged"):
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            sell_value=value,
            wallet=WALLET,
        )
    # Handle loans like a fiat deposit.
    elif row_dict["Type"] in ("WithdrawalCredit", "Loan Withdrawal"):
        data_row.t_record = TransactionOutRecord(
            TrType.LOAN_RECEIVED,
            data_row.timestamp,
            buy_quantity=sell_quantity,
            buy_asset=sell_asset,
            buy_value=sell_quantity,
            wallet=WALLET,
        )
    # Treat credit deposits like a buy order with fiat.
    elif (
        row_dict["Type"] in ("Deposit", "Top up Crypto") and row_dict["Details"].find("Credit") > -1
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=value,
            sell_quantity=value,
            sell_asset=config.ccy,
            sell_value=value,
            wallet=WALLET,
        )
    # These sell orders are used for repayments,
    # but the fiat value isn't recorded in the output columns.
    elif row_dict["Type"] == "Manual Sell Order":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=value,
            buy_asset=config.ccy,
            buy_value=value,
            sell_quantity=buy_quantity,
            sell_asset=buy_asset,
            sell_value=value,
            wallet=WALLET,
        )
    elif row_dict["Type"] in ("Liquidation", "Repayment", "Manual Repayment"):
        data_row.t_record = TransactionOutRecord(
            TrType.LOAN_REPAID,
            data_row.timestamp,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            sell_value=sell_quantity,
            wallet=WALLET,
        )
    # Handle loan interest here. "Interest Additional" is accrued for paying back a loan early.
    elif row_dict["Type"] in ("InterestAdditional", "Interest Additional") or (
        row_dict["Type"] == "Interest" and row_dict["Details"].find("Overdraft") > -1
    ):
        if sell_quantity is not None and sell_quantity > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.LOAN_INTEREST,
                data_row.timestamp,
                buy_quantity=sell_quantity,
                buy_asset=sell_asset,
                buy_value=value,
                wallet=WALLET,
            )
        # Skip interest with zero amounts.
        else:
            return
    # Skip internal and loan operations which are not disposals or are just informational
    elif row_dict["Type"] in (
        "Administrator",
        "Assimilation",
        "DepositToExchange",
        "ExchangeToWithdraw",
        "TransferIn",
        "Transfer In",
        "TransferOut",
        "Transfer Out",
        "UnlockingTermDeposit",
        "Unlocking Term Deposit",
        "LockingTermDeposit",
        "Locking Term Deposit",
    ):
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    ParserType.SAVINGS,
    "Nexo",
    [
        "Transaction",
        "Type",
        "Currency",
        "Amount",
        "USD Equivalent",
        "Details",
        "Outstanding Loan",
        "Date / Time",
    ],
    worksheet_name="Nexo",
    row_handler=parse_nexo,
)

DataParser(
    ParserType.SAVINGS,
    "Nexo",
    [
        "Transaction",
        "Type",
        "Currency",
        "Amount",
        "Details",
        "Outstanding Loan",
        "Date / Time",
    ],
    worksheet_name="Nexo",
    row_handler=parse_nexo,
)

DataParser(
    ParserType.SAVINGS,
    "Nexo",
    [
        "Transaction",
        "Type",
        "Input Currency",
        "Input Amount",
        "Output Currency",
        "Output Amount",
        "USD Equivalent",
        "Details",
        "Outstanding Loan",
        "Date / Time",
    ],
    worksheet_name="Nexo",
    row_handler=parse_nexo,
)

DataParser(
    ParserType.SAVINGS,
    "Nexo",
    [
        "Transaction",
        "Type",
        "Input Currency",
        "Input Amount",
        "Output Currency",
        "Output Amount",
        "USD Equivalent",
        "Details",
        "Date / Time",
    ],
    worksheet_name="Nexo",
    row_handler=parse_nexo,
)
