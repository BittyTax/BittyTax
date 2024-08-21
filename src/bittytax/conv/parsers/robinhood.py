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

WALLET = "Robinhood"


def parse_robinhood(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict

    if "Time Entered" in row_dict:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["Time Entered"])
    else:
        return

    if row_dict["State"] != "Filled":
        return

    if row_dict["Side"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]),
            buy_asset=row_dict["Symbol"],
            sell_quantity=Decimal(row_dict["Notional"].strip(" ($)")),
            sell_asset="USD",
            wallet=WALLET,
        )
    elif row_dict["Side"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Notional"].strip(" ($)")),
            buy_asset="USD",
            sell_quantity=Decimal(row_dict["Quantity"]),
            sell_asset=row_dict["Symbol"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


DataParser(
    ParserType.EXCHANGE,
    "Robinhood",
    [
        "UUID",
        "Time Entered",
        "Symbol",
        "Side",
        "Quantity",
        "State",
        "Order Type",
        "Leaves Quantity",
        "Entered Price",
        "Average Price",
        "Notional",
    ],
    worksheet_name="Robinhood",
    row_handler=parse_robinhood,
)
