# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import sys
from decimal import Decimal

from colorama import Fore

from ...constants import WARNING
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

WALLET = "Celsius"


def parse_celsius(data_row, parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date and time"])

    if row_dict["Confirmed"] != "Yes" and not kwargs["unconfirmed"]:
        sys.stderr.write(
            f"{Fore.YELLOW}row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
        )
        sys.stderr.write(
            f"{WARNING} Skipping unconfirmed transaction, use the [-uc] option to include it\n"
        )
        return

    if row_dict["Transaction type"] in (
        "deposit",
        "Deposit",
        "inbound_transfer",
        "Inbound Transfer",
        "Transfer",
    ):
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["Coin amount"],
            buy_asset=row_dict["Coin type"],
            wallet=WALLET,
        )
    elif row_dict["Transaction type"] in (
        "withdrawal",
        "Withdrawal",
        "outbound_transfer",
        "Outbound Transfer",
    ):
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Coin amount"])),
            sell_asset=row_dict["Coin type"],
            wallet=WALLET,
        )
    elif row_dict["Transaction type"] in ("interest", "Interest", "reward", "Reward"):
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_INTEREST,
            data_row.timestamp,
            buy_quantity=row_dict["Coin amount"],
            buy_asset=row_dict["Coin type"],
            buy_value=DataParser.convert_currency(row_dict["USD Value"], "USD", data_row.timestamp),
            wallet=WALLET,
        )
    elif row_dict["Transaction type"] in (
        "promo_code_reward",
        "Promo Code Reward",
        "referred_award",
        "Referred Award",
        "referrer_award",
        "Referrer Award",
        "bonus_token",
        "Bonus Token",
    ):
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_GIFT_RECEIVED,
            data_row.timestamp,
            buy_quantity=row_dict["Coin amount"],
            buy_asset=row_dict["Coin type"],
            buy_value=DataParser.convert_currency(row_dict["USD Value"], "USD", data_row.timestamp),
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Transaction type"),
            "Transaction type",
            row_dict["Transaction type"],
        )


DataParser(
    DataParser.TYPE_SAVINGS,
    "Celsius",
    [
        "Internal id",
        "Date and time",
        "Transaction type",
        "Coin type",
        "Coin amount",
        "USD Value",
        "Original Reward Coin",
        "Reward Amount In Original Coin",
        "Confirmed",
    ],
    worksheet_name="Celsius",
    row_handler=parse_celsius,
)

DataParser(
    DataParser.TYPE_SAVINGS,
    "Celsius",
    [
        "Internal id",
        "Date and time",
        "Transaction type",
        "Coin type",
        "Coin amount",
        "USD Value",
        "Original Interest Coin",
        "Interest Amount In Original Coin",
        "Confirmed",
    ],
    worksheet_name="Celsius",
    row_handler=parse_celsius,
)
