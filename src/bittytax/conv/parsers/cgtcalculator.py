# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ...constants import TZ_UTC
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedContentError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "CGTCalculator"


def parse_cgtcalculator(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["B/S"] == "B":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Shares"]),
            buy_asset=row_dict["Company"],
            sell_quantity=Decimal(row_dict["Shares"]) * Decimal(row_dict["Price"]),
            sell_asset=config.ccy,
            fee_quantity=Decimal(row_dict["Charges"]) + Decimal(row_dict["Tax"]),
            fee_asset=config.ccy,
            wallet=WALLET,
        )
    elif row_dict["B/S"] == "S":
        if data_row.timestamp >= datetime(2008, 4, 6, tzinfo=TZ_UTC):
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Shares"]) * Decimal(row_dict["Price"]),
                buy_asset=config.ccy,
                sell_quantity=Decimal(row_dict["Shares"]),
                sell_asset=row_dict["Company"],
                fee_quantity=Decimal(row_dict["Charges"]) + Decimal(row_dict["Tax"]),
                fee_asset=config.ccy,
                wallet=WALLET,
            )
        else:
            raise UnexpectedContentError(parser.in_header.index("Date"), "Date", row_dict["Date"])
    elif row_dict["B/S"] == "T":
        data_row.t_record = TransactionOutRecord(
            TrType.GIFT_SPOUSE,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Shares"]),
            sell_asset=row_dict["Company"],
            fee_quantity=Decimal(row_dict["Price"]),
            fee_asset=config.ccy,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("B/S"), "B/S", row_dict["B/S"])


DataParser(
    ParserType.SHARES,
    "CGTCalculator",
    ["B/S", "Date", "Company", "Shares", "Price", "Charges", "Tax"],
    worksheet_name="CGTCalculator",
    row_handler=parse_cgtcalculator,
)

DataParser(
    ParserType.SHARES,
    "CGTCalculator",
    ["B/S", "Date", "Company", "Shares", "Price", "Charges", "Tax", ""],
    worksheet_name="CGTCalculator",
    row_handler=parse_cgtcalculator,
)
