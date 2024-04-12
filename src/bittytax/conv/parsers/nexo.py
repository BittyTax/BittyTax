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
    "NEXONEXO": "NEXO",
    "NEXOBNB": "NEXO",
    "NEXOBEP2": "NEXO",
    "USDTERC": "USDT",
}


def parse_nexo(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    if "Date / Time" in row_dict:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["Date / Time"], tz="Europe/Zurich")
    else:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["Date / Time (UTC)"])

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

    if row_dict["Type"] in (
        "Deposit",
        "ExchangeDepositedOn",
        "Exchange Deposited On",
        "Top up Crypto",
    ):
        if "Airdrop" in row_dict["Details"]:
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
    elif row_dict["Type"] in (
        "Interest",
        "FixedTermInterest",
        "Fixed Term Interest",
        "InterestAdditional",
        "Interest Additional",
    ):
        if buy_quantity and buy_quantity > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.INTEREST,
                data_row.timestamp,
                buy_quantity=buy_quantity,
                buy_asset=buy_asset,
                buy_value=value,
                wallet=WALLET,
            )
        else:
            # Interest on loan is just informational
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
    elif row_dict["Type"] in ("ReferralBonus", "Referral Bonus"):
        data_row.t_record = TransactionOutRecord(
            TrType.REFERRAL,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=value,
            wallet=WALLET,
        )
    elif row_dict["Type"] in ("Cashback", "Exchange Cashback"):
        data_row.t_record = TransactionOutRecord(
            TrType.CASHBACK,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=value,
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Bonus":
        data_row.t_record = TransactionOutRecord(
            TrType.AIRDROP,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=value,
            wallet=WALLET,
        )
    elif row_dict["Type"] in ("Exchange", "CreditCardStatus", "Credit Card Status"):
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
    elif row_dict["Type"] in ("Withdrawal", "WithdrawExchanged", "Withdraw Exchanged"):
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            sell_value=value,
            wallet=WALLET,
        )
    elif row_dict["Type"] in ("Liquidation", "Repayment", "Manual Repayment", "Manual Sell Order"):
        # Repayment of loan
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            sell_value=value,
            wallet=WALLET,
        )
    elif row_dict["Type"] in (
        "Administrator",
        "Assimilation",
        "WithdrawalCredit",
        "Withdrawal Credit",
        "UnlockingTermDeposit",
        "Unlocking Term Deposit",
        "LockingTermDeposit",
        "Locking Term Deposit",
        "Repayment",
        "Loan Withdrawal",
    ):
        # Skip loan operations which are not disposals or are just informational
        return
    elif row_dict["Type"] in (
        "DepositToExchange",
        "Deposit To Exchange",
        "ExchangeToWithdraw",
        "Exchange To Withdraw",
        "TransferIn",
        "Transfer In",
        "TransferOut",
        "Transfer Out",
    ):
        # Skip internal operations
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
        lambda c: c in ("Date / Time", "Date / Time (UTC)"),
    ],
    worksheet_name="Nexo",
    row_handler=parse_nexo,
)
