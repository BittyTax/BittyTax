# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
from decimal import Decimal

from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError, UnknownCryptoassetError
from ..out_record import TransactionOutRecord

WALLET = "Trezor"


def parse_trezor_labeled(data_row, parser, **kwargs):
    parse_trezor(data_row, parser, **kwargs)


def parse_trezor(data_row, parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(
        row_dict["Date"] + "T" + row_dict["Time"], tz="GMT+1"
    )

    if not kwargs["cryptoasset"]:
        match = re.match(r".+_(\w{3,4})\.csv$", kwargs["filename"])

        if match:
            symbol = match.group(1).upper()
        else:
            raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet"))
    else:
        symbol = kwargs["cryptoasset"]

    if row_dict["TX type"] == "IN":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["Value"],
            buy_asset=symbol,
            fee_quantity=Decimal(row_dict["TX total"]) - Decimal(row_dict["Value"]),
            fee_asset=symbol,
            wallet=WALLET,
            note=row_dict.get("Address Label", ""),
        )
    elif row_dict["TX type"] == "OUT":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=row_dict["Value"],
            sell_asset=symbol,
            fee_quantity=abs(Decimal(row_dict["TX total"])) - Decimal(row_dict["Value"]),
            fee_asset=symbol,
            wallet=WALLET,
            note=row_dict.get("Address Label", ""),
        )
    elif row_dict["TX type"] == "SELF":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=0,
            sell_asset=symbol,
            fee_quantity=abs(Decimal(row_dict["TX total"])),
            fee_asset=symbol,
            wallet=WALLET,
            note=row_dict.get("Address Label", ""),
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("TX type"), "TX type", row_dict["TX type"])


DataParser(
    DataParser.TYPE_WALLET,
    "Trezor",
    [
        "Date",
        "Time",
        "TX id",
        "Address",
        "Address Label",
        "TX type",
        "Value",
        "TX total",
        "Balance",
    ],
    worksheet_name="Trezor",
    row_handler=parse_trezor_labeled,
)

DataParser(
    DataParser.TYPE_WALLET,
    "Trezor",
    ["Date", "Time", "TX id", "Address", "TX type", "Value", "TX total", "Balance"],
    worksheet_name="Trezor",
    row_handler=parse_trezor,
)
