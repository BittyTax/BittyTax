# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Kinesis"


def parse_kinesis(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["DateTime"])

    if row_dict["Transaction_Type"] == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"].replace(",", "")),
            buy_asset=row_dict["Amount_Currency"],
            sell_quantity=Decimal(row_dict["Total"].replace(",", "")),
            sell_asset=row_dict["Trade_Price_Currency"],
            fee_quantity=Decimal(row_dict["Fee"].replace(",", "")),
            fee_asset=row_dict["Fee_Currency"],
            wallet=WALLET,
        )
    elif row_dict["Transaction_Type"] == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Total"].replace(",", "")),
            buy_asset=row_dict["Trade_Price_Currency"],
            sell_quantity=Decimal(row_dict["Amount"].replace(",", "")),
            sell_asset=row_dict["Amount_Currency"],
            fee_quantity=Decimal(row_dict["Fee"].replace(",", "")),
            fee_asset=row_dict["Fee_Currency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Transaction_Type"),
            "Transaction_Type",
            row_dict["Transaction_Type"],
        )


DataParser(
    ParserType.EXCHANGE,
    "Kinesis",
    [
        "DateTime",
        "HIN",
        "Transactions_ID",
        "Order_ID",
        "Currency_Pair",
        "Transaction_Type",
        "Amount",
        "Amount_Currency",
        "Trade_Price",
        "Trade_Price_Currency",
        "Total",
        "Fee",
        "Fee_Currency",
        "Trade_Value_in_USD",
    ],
    worksheet_name="Kinesis",
    row_handler=parse_kinesis,
)
