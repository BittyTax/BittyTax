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

WALLET = "Cryptsy"


def parse_cryptsy(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Timestamp"], tz="US/Eastern")

    if row_dict["OrderType"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]),
            buy_asset=row_dict["Market"].split("/")[0],
            sell_quantity=Decimal(row_dict["Total"]),
            sell_asset=row_dict["Market"].split("/")[1],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Market"].split("/")[1],
            wallet=WALLET,
        )
    elif row_dict["OrderType"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Total"]),
            buy_asset=row_dict["Market"].split("/")[1],
            sell_quantity=Decimal(row_dict["Quantity"]),
            sell_asset=row_dict["Market"].split("/")[0],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Market"].split("/")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("OrderType"), "OrderType", row_dict["OrderType"]
        )


DataParser(
    ParserType.EXCHANGE,
    "Cryptsy",
    [
        "TradeID",
        "OrderType",
        "Market",
        "Price",
        "Quantity",
        "Total",
        "Fee",
        "Net",
        "Timestamp",
    ],
    worksheet_name="Cryptsy",
    row_handler=parse_cryptsy,
)
