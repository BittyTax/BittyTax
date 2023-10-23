# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import MissingValueError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "ii"


def parse_ii(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if not row_dict["Symbol"]:
        return

    if not row_dict["Quantity"]:
        raise MissingValueError(
            parser.in_header.index("Quantity"), "Quantity", row_dict["Quantity"]
        )

    if row_dict["Debit"]:
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]),
            buy_asset=row_dict["Symbol"],
            sell_quantity=Decimal(row_dict["Debit"].strip("£").replace(",", "")),
            sell_asset=config.ccy,
            wallet=WALLET,
        )
    elif row_dict["Credit"]:
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Credit"].strip("£").replace(",", "")),
            buy_asset=config.ccy,
            sell_quantity=Decimal(row_dict["Quantity"]),
            sell_asset=row_dict["Symbol"],
            wallet=WALLET,
        )


DataParser(
    ParserType.SHARES,
    "Interactive Investor",
    [
        "Settlement Date",
        "Date",
        "Symbol",
        "Sedol",
        "ISIN",
        "Quantity",
        "Price",
        "Description",
        "Reference",
        "Debit",
        "Credit",
        "Running Balance",
    ],
    worksheet_name="ii",
    row_handler=parse_ii,
)
