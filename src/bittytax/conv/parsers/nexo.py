# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

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

    if row_dict["Type"] in ("Deposit", "Top up Crypto", "ExchangeDepositedOn"):
        # Skip credit deposits (already handled with "Loan Withdrawal").
        if row_dict["Details"].find("Credit") > -1:
            return

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
    elif row_dict["Type"] in ("Interest", "FixedTermInterest", "Fixed Term Interest"):
        if ("Amount" in row_dict and Decimal(row_dict["Amount"]) > 0) or (
            "Input Amount" in row_dict and Decimal(row_dict["Input Amount"]) > 0
        ):
            data_row.t_record = TransactionOutRecord(
                TrType.INTEREST,
                data_row.timestamp,
                buy_quantity=buy_quantity,
                buy_asset=buy_asset,
                buy_value=value,
                wallet=WALLET,
            )
        else:
            return
    elif row_dict["Type"] == "Dividend":
        data_row.t_record = TransactionOutRecord(
            TrType.DIVIDEND,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=value,
            wallet=WALLET,
        )
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
    elif row_dict["Type"] in ("WithdrawalCredit", "Loan Withdrawal"):
        data_row.t_record = TransactionOutRecord(
            TrType.RECEIVE_LOAN,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=value,
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
            TrType.REPAY_LOAN,
            data_row.timestamp,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            sell_value=sell_quantity,
            wallet=WALLET,
        )
    # "Interest Additional" is a borrowing fee for paying back a loan early. Treat as an expense.
    elif row_dict["Type"] == "Interest Additional":
        data_row.t_record = TransactionOutRecord(
            TrType.BORROWING_FEE,
            data_row.timestamp,
            fee_quantity=sell_quantity,
            fee_asset=sell_asset,
            fee_value=value,
            wallet=WALLET,
        )
    # Skip loan operations which are not disposals or are just informational
    elif row_dict["Type"] in (
        "Assimilation",
        "UnlockingTermDeposit",
        "Unlocking Term Deposit",
        "LockingTermDeposit",
        "Locking Term Deposit",
    ):
        return
    # Skip internal operations
    elif row_dict["Type"] in (
        "Administrator",
        "DepositToExchange",
        "ExchangeToWithdraw",
        "TransferIn",
        "Transfer In",
        "TransferOut",
        "Transfer Out",
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
