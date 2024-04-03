# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Uphold"


def parse_uphold_v2(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["Type"] == "in":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Origin Amount"]),
            buy_asset=row_dict["Origin Currency"],
            fee_quantity=Decimal(row_dict["Fee Amount"]) if row_dict["Fee Amount"] else None,
            fee_asset=row_dict["Fee Currency"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "out":
        if row_dict["Origin Currency"] == row_dict["Destination Currency"]:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["Destination Amount"]),
                sell_asset=row_dict["Origin Currency"],
                fee_quantity=Decimal(row_dict["Fee Amount"]) if row_dict["Fee Amount"] else None,
                fee_asset=row_dict["Fee Currency"],
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["Origin Amount"]),
                sell_asset=row_dict["Origin Currency"],
                wallet=WALLET,
            )
    elif row_dict["Type"] == "transfer":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Destination Amount"]),
            buy_asset=row_dict["Destination Currency"],
            sell_quantity=Decimal(row_dict["Origin Amount"]),
            sell_asset=row_dict["Origin Currency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def parse_uphold_v1(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["date"])

    if row_dict["type"] in ("deposit", "in"):
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["origin_amount"]),
            buy_asset=row_dict["origin_currency"],
            fee_quantity=Decimal(row_dict["origin_amount"])
            - Decimal(row_dict["destination_amount"]),
            fee_asset=row_dict["origin_currency"],
            wallet=WALLET,
        )
    elif row_dict["type"] in ("withdrawal", "out"):
        # Check if origin and destination currency are the same
        if row_dict["origin_currency"] == row_dict["destination_currency"]:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["destination_amount"]),
                sell_asset=row_dict["origin_currency"],
                fee_quantity=Decimal(row_dict["origin_amount"])
                - Decimal(row_dict["destination_amount"]),
                fee_asset=row_dict["origin_currency"],
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["origin_amount"]),
                sell_asset=row_dict["origin_currency"],
                wallet=WALLET,
            )
    elif row_dict["type"] == "transfer":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["destination_amount"]),
            buy_asset=row_dict["destination_currency"],
            sell_quantity=Decimal(row_dict["origin_amount"]),
            sell_asset=row_dict["origin_currency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


DataParser(
    ParserType.EXCHANGE,
    "Uphold",
    [
        "Date",
        "Destination",
        "Destination Amount",
        "Destination Currency",
        "Fee Amount",
        "Fee Currency",
        "Id",
        "Origin",
        "Origin Amount",
        "Origin Currency",
        "Status",
        "Type",
    ],
    worksheet_name="Uphold",
    row_handler=parse_uphold_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "Uphold",
    [
        "date",
        "id",
        "type",
        lambda h: re.match(r"^value_in_(\w{3})", h),
        lambda h: re.match(r"^commission_in_(\w{3})", h),
        "pair",
        "rate",
        "origin_currency",
        "origin_amount",
        "origin_commission",
        "destination_currency",
        "destination_amount",
        "destination_commission",
    ],
    worksheet_name="Uphold",
    row_handler=parse_uphold_v1,
)
