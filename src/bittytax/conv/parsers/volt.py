# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

import re

from ..dataparser import DataParser
from ..exceptions import UnexpectedContentError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

WALLET = "Volt"


def parse_volt(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(
        row_dict["time"], tz="Europe/London", dayfirst=True
    )

    amount, symbol = _get_amount(row_dict["amount"].replace(",", ""))
    if amount is None:
        raise UnexpectedContentError(parser.in_header.index("amount"), "amount", row_dict["amount"])

    if row_dict["status"] == "Received":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=symbol,
            wallet=WALLET,
        )
    elif row_dict["status"] == "OUT":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=amount,
            sell_asset=symbol,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("status"), "status", row_dict["status"])


def _get_amount(amount):
    match = re.match(r"^[-+](\d+|\d+\.\d+) (\w{3,4}) |$", amount)

    if match:
        amount = match.group(1)
        symbol = match.group(2)
        return amount, symbol
    return None, None


DataParser(
    DataParser.TYPE_WALLET,
    "Volt",
    ["time", "status", "address", "amount", "txid"],
    worksheet_name="Volt",
    row_handler=parse_volt,
)

DataParser(
    DataParser.TYPE_WALLET,
    "Volt",
    ["time", "status", "address", "amount", "txid", ""],
    worksheet_name="Volt",
    row_handler=parse_volt,
)
