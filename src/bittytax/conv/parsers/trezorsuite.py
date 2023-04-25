# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import re

from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError, UnknownCryptoassetError
from ..out_record import TransactionOutRecord

WALLET = "Trezor"


def parse_trezor_suite_v2(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["Timestamp"]))

    if row_dict["Type"] == "RECV":
        # Workaround: we have to ignore the fee as fee is for the sender
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["Amount"],
            buy_asset=row_dict["Amount unit"],
            wallet=WALLET,
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "SENT":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=row_dict["Amount"],
            sell_asset=row_dict["Amount unit"],
            fee_quantity=row_dict["Fee"],
            fee_asset=row_dict["Fee unit"],
            wallet=WALLET,
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "SELF":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=0,
            sell_asset=row_dict["Amount unit"],
            fee_quantity=row_dict["Fee"],
            fee_asset=row_dict["Fee unit"],
            wallet=WALLET,
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "FAILED":
        if row_dict["Label"]:
            note = f'Failure ({row_dict["Label"]})'
        else:
            note = "Failure"

        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_SPEND,
            data_row.timestamp,
            sell_quantity=row_dict["Amount"],
            sell_asset=row_dict["Amount unit"],
            fee_quantity=row_dict["Fee"],
            fee_asset=row_dict["Fee unit"],
            wallet=WALLET,
            note=note,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def parse_trezor_suite_v1(data_row, parser, **kwargs):
    row_dict = data_row.row_dict
    if "Date & Time" in row_dict:
        data_row.timestamp = DataParser.parse_timestamp(
            row_dict["Date & Time"], dayfirst=True, tz="Europe/London"
        )
    else:
        data_row.timestamp = DataParser.parse_timestamp(int(row_dict["Timestamp"]))

    if not kwargs["cryptoasset"]:
        match = re.match(r".+-(\w{3,4})-.*", kwargs["filename"])

        if match:
            symbol = match.group(1).upper()
        else:
            raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet"))
    else:
        symbol = kwargs["cryptoasset"]

    if row_dict["Type"] == "RECV":
        # Workaround: we have to ignore the fee as fee is for the sender
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["Total"],
            buy_asset=symbol,
            wallet=WALLET,
        )
    elif row_dict["Type"] == "SENT":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=row_dict["Total"],
            sell_asset=symbol,
            fee_quantity=row_dict["Fee"],
            fee_asset=symbol,
            wallet=WALLET,
        )
    elif row_dict["Type"] == "SELF":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=0,
            sell_asset=symbol,
            fee_quantity=row_dict["Fee"],
            fee_asset=symbol,
            wallet=WALLET,
        )
    elif row_dict["Type"] == "FAILED":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_SPEND,
            data_row.timestamp,
            sell_quantity=0,
            sell_asset=symbol,
            fee_quantity=row_dict["Fee"],
            fee_asset=symbol,
            wallet=WALLET,
            note="Failure",
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    DataParser.TYPE_WALLET,
    "Trezor Suite",
    [
        "Timestamp",
        "Date",
        "Time",
        "Type",
        "Transaction ID",
        "Fee",
        "Fee unit",
        "Address",
        "Label",
        "Amount",
        "Amount unit",
        "Fiat (GBP)",
        "Other",
    ],
    worksheet_name="Trezor",
    row_handler=parse_trezor_suite_v2,
)

DataParser(
    DataParser.TYPE_WALLET,
    "Trezor Suite",
    ["Date & Time", "Type", "Transaction ID", "Addresses", "Fee", "Total"],
    worksheet_name="Trezor",
    row_handler=parse_trezor_suite_v1,
)
