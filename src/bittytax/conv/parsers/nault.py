# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Nault"


def parse_nault(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("hash"), tx_dest_pos=parser.in_header.index("account")
    )

    if row_dict["type"] == "receive":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount"]),
            buy_asset="XNO",
            wallet=WALLET,
        )
    elif row_dict["type"] == "send":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["amount"]),
            sell_asset="XNO",
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


DataParser(
    ParserType.WALLET,
    "Nault",
    ["account", "type", "amount", "hash", "height", "time"],
    worksheet_name="Nault",
    row_handler=parse_nault,
)
