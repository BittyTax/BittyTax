# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Wirex"


def parse_wirex(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    if row_dict[""] == "Create":
        return

    if row_dict[""] == "In":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"].split(" ")[0]),
            buy_asset=row_dict["Amount"].split(" ")[1],
            wallet=WALLET,
        )
    elif row_dict[""] == "Out":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Amount"].split(" ")[0]),
            sell_asset=row_dict["Amount"].split(" ")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index(""), "", row_dict[""])


DataParser(
    ParserType.EXCHANGE,
    "Wirex",
    ["#", "", "Time", "Amount", "Available"],
    worksheet_name="Wirex",
    row_handler=parse_wirex,
)
