# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord
from ..output_csv import OutputBase


def parse_generic(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Timestamp"])

    if row_dict["Type"] not in TransactionOutRecord.ALL_TYPES:
        raise UnexpectedTypeError(0, "Type", row_dict["Type"])

    if row_dict["Buy Quantity"]:
        buy_quantity = row_dict["Buy Quantity"]
    else:
        buy_quantity = None

    if row_dict["Buy Value in GBP"]:
        buy_value = row_dict["Buy Value in GBP"]
    else:
        buy_value = None

    if row_dict["Sell Quantity"]:
        sell_quantity = row_dict["Sell Quantity"]
    else:
        sell_quantity = None

    if row_dict["Sell Value in GBP"]:
        sell_value = row_dict["Sell Value in GBP"]
    else:
        sell_value = None

    if row_dict["Fee Quantity"]:
        fee_quantity = row_dict["Fee Quantity"]
    else:
        fee_quantity = None

    if row_dict["Fee Value in GBP"]:
        fee_value = row_dict["Fee Value in GBP"]
    else:
        fee_value = None

    data_row.t_record = TransactionOutRecord(
        row_dict["Type"],
        data_row.timestamp,
        buy_quantity=buy_quantity,
        buy_asset=row_dict["Buy Asset"],
        buy_value=buy_value,
        sell_quantity=sell_quantity,
        sell_asset=row_dict["Sell Asset"],
        sell_value=sell_value,
        fee_quantity=fee_quantity,
        fee_asset=row_dict["Fee Asset"],
        fee_value=fee_value,
        wallet=row_dict["Wallet"],
        note=row_dict["Note"],
    )

    # Remove TR headers and data
    if len(parser.in_header) > len(OutputBase.BITTYTAX_OUT_HEADER):
        del parser.in_header[0 : len(OutputBase.BITTYTAX_OUT_HEADER)]
    del data_row.row[0 : len(OutputBase.BITTYTAX_OUT_HEADER)]

    parser.worksheet_name = row_dict["Wallet"]


DataParser(
    DataParser.TYPE_GENERIC,
    "Generic",
    [
        "Type",
        "Buy Quantity",
        "Buy Asset",
        "Buy Value in GBP",
        "Sell Quantity",
        "Sell Asset",
        "Sell Value in GBP",
        "Fee Quantity",
        "Fee Asset",
        "Fee Value in GBP",
        "Wallet",
        "Timestamp",
        "Note",
        "Raw Data",
    ],
    worksheet_name="Generic",
    row_handler=parse_generic,
)
