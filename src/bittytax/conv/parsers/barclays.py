# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow


def parse_barclays(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["Order Status"] != "Completed":
        return

    if row_dict["Buy/Sell"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]),
            buy_asset=row_dict["Investment"],
            sell_quantity=Decimal(row_dict["Cost/Proceeds"]),
            sell_asset=config.ccy,
            wallet=row_dict["Account"],
        )
    elif row_dict["Buy/Sell"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Cost/Proceeds"]),
            buy_asset=config.ccy,
            sell_quantity=Decimal(row_dict["Quantity"]),
            sell_asset=row_dict["Investment"],
            wallet=row_dict["Account"],
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Buy/Sell"), "Buy/Sell", row_dict["Buy/Sell"]
        )


DataParser(
    ParserType.SHARES,
    "Barclays Smart Investor",
    [
        "Investment",
        "Date",
        "Order Status",
        "Account",
        "Buy/Sell",
        "Quantity",
        "Cost/Proceeds",
    ],
    worksheet_name="Barclays",
    row_handler=parse_barclays,
)
