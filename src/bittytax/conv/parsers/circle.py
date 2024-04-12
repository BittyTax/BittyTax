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

WALLET = "Circle"


def parse_circle(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["Transaction Type"] in (
        "deposit",
        "internal_switch_currency",
        "switch_currency",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["To Amount"].strip("£€$").split(" ")[0]),
            buy_asset=row_dict["To Currency"],
            sell_quantity=Decimal(row_dict["From Amount"].strip("£€$").split(" ")[0]),
            sell_asset=row_dict["From Currency"],
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "spend":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["From Amount"].strip("£€$").split(" ")[0]),
            sell_asset=row_dict["From Currency"],
            sell_value=(
                Decimal(row_dict["To Amount"].strip("£€$"))
                if row_dict["To Currency"] == config.ccy
                else None
            ),
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "receive":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["To Amount"].strip("£€$").split(" ")[0]),
            buy_asset=row_dict["To Currency"],
            buy_value=(
                Decimal(row_dict["From Amount"].strip("£€$"))
                if row_dict["From Currency"] == config.ccy
                else None
            ),
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "fork":
        data_row.t_record = TransactionOutRecord(
            TrType.FORK,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["To Amount"].strip("£€$").split(" ")[0]),
            buy_asset=row_dict["To Currency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Transaction Type"),
            "Transaction Type",
            row_dict["Transaction Type"],
        )


DataParser(
    ParserType.EXCHANGE,
    "Circle",
    [
        "Date",
        "Reference ID",
        "Transaction Type",
        "From Account",
        "To Account",
        "From Amount",
        "From Currency",
        "To Amount",
        "To Currency",
        "Status",
    ],
    worksheet_name="Circle",
    row_handler=parse_circle,
)
