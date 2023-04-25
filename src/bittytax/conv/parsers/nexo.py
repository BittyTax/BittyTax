# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import re
from decimal import Decimal

from ...config import config
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

WALLET = "Nexo"

ASSET_NORMALISE = {
    "NEXONEXO": "NEXO",
    "NEXOBNB": "NEXO",
    "NEXOBEP2": "NEXO",
    "USDTERC": "USDT",
}


def parse_nexo(data_row, parser, **_kwargs):
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
            buy_quantity = row_dict["Amount"]
            sell_quantity = abs(Decimal(row_dict["Amount"]))
        else:
            match = re.match(r"^-(\d+|\d+\.\d+) / \+(\d+|\d+\.\d+)$", row_dict["Amount"])
            buy_quantity = None
            sell_quantity = None

            if match:
                buy_quantity = match.group(2)
                sell_quantity = match.group(1)
    else:
        buy_quantity = row_dict["Output Amount"]
        sell_quantity = abs(Decimal(row_dict["Input Amount"]))

    if row_dict.get("USD Equivalent") and buy_asset != config.ccy:
        value = DataParser.convert_currency(
            row_dict["USD Equivalent"].strip("$"), "USD", data_row.timestamp
        )
    else:
        value = None

    if row_dict["Type"] in ("Deposit", "ExchangeDepositedOn"):
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=value,
            wallet=WALLET,
        )
    elif row_dict["Type"] in ("Interest", "FixedTermInterest", "InterestAdditional"):
        if ("Amount" in row_dict and Decimal(row_dict["Amount"]) > 0) or (
            "Input Amount" in row_dict and Decimal(row_dict["Input Amount"]) > 0
        ):
            data_row.t_record = TransactionOutRecord(
                TransactionOutRecord.TYPE_INTEREST,
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
            TransactionOutRecord.TYPE_DIVIDEND,
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
    ):
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_GIFT_RECEIVED,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=value,
            wallet=WALLET,
        )

    elif row_dict["Type"] in ("Exchange", "CreditCardStatus"):
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
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
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            sell_value=value,
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Liquidation":
        # Repayment of loan
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_SPEND,
            data_row.timestamp,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            sell_value=value,
            wallet=WALLET,
        )
    elif row_dict["Type"] in (
        "WithdrawalCredit",
        "UnlockingTermDeposit",
        "LockingTermDeposit",
        "Repayment",
    ):
        # Skip loan operations which are not disposals or are just informational
        return
    elif row_dict["Type"] in (
        "DepositToExchange",
        "ExchangeToWithdraw",
        "TransferIn",
        "TransferOut",
    ):
        # Skip internal operations
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    DataParser.TYPE_SAVINGS,
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
    DataParser.TYPE_SAVINGS,
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
    DataParser.TYPE_SAVINGS,
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
    DataParser.TYPE_SAVINGS,
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
