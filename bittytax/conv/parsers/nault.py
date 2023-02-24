# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

WALLET = "Nault"


def parse_nault(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])

    if row_dict["type"] == "receive":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["amount"],
            buy_asset="XNO",
            wallet=WALLET,
        )
    elif row_dict["type"] == "send":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=row_dict["amount"],
            sell_asset="XNO",
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


DataParser(
    DataParser.TYPE_WALLET,
    "Nault",
    ["account", "type", "amount", "hash", "height", "time"],
    worksheet_name="Nault",
    row_handler=parse_nault,
)
