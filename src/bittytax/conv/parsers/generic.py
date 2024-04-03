# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import re
from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord
from ..output_csv import OutputBase

if TYPE_CHECKING:
    from ..datarow import DataRow


def parse_generic(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Timestamp"])
    currency = parser.args[0].group(1)

    try:
        t_type = TrType(row_dict["Type"])
    except ValueError as e:
        raise UnexpectedTypeError(0, "Type", row_dict["Type"]) from e

    if row_dict["Buy Quantity"]:
        buy_quantity = Decimal(row_dict["Buy Quantity"])
    else:
        buy_quantity = None

    if row_dict[f"Buy Value in {currency}"]:
        buy_value = DataParser.convert_currency(
            row_dict[f"Buy Value in {currency}"], currency, data_row.timestamp
        )
    else:
        buy_value = None

    if row_dict["Sell Quantity"]:
        sell_quantity = Decimal(row_dict["Sell Quantity"])
    else:
        sell_quantity = None

    if row_dict[f"Sell Value in {currency}"]:
        sell_value = DataParser.convert_currency(
            row_dict[f"Sell Value in {currency}"], currency, data_row.timestamp
        )
    else:
        sell_value = None

    if row_dict["Fee Quantity"]:
        fee_quantity = Decimal(row_dict["Fee Quantity"])
    else:
        fee_quantity = None

    if row_dict[f"Fee Value in {currency}"]:
        fee_value = DataParser.convert_currency(
            row_dict[f"Fee Value in {currency}"], currency, data_row.timestamp
        )
    else:
        fee_value = None

    data_row.t_record = TransactionOutRecord(
        t_type,
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
    ParserType.GENERIC,
    "Generic",
    [
        "Type",
        "Buy Quantity",
        "Buy Asset",
        lambda h: re.match(r"^Buy Value in (\w{3})", h),
        "Sell Quantity",
        "Sell Asset",
        lambda h: re.match(r"^Sell Value in (\w{3})", h),
        "Fee Quantity",
        "Fee Asset",
        lambda h: re.match(r"^Fee Value in (\w{3})", h),
        "Wallet",
        "Timestamp",
        "Note",
        "Raw Data",
    ],
    worksheet_name="Generic",
    row_handler=parse_generic,
)
