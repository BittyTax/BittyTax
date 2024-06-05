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

WALLET = "CoinCorner"


def parse_coincorner(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    t_type = row_dict["Transaction Type"].strip()

    if t_type in ("Bank Deposit", "Coinfloor Balance Transfer"):
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"],
            wallet=WALLET,
        )
    elif t_type == "Bank Withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Currency"],
            wallet=WALLET,
        )
    elif t_type == "Bought Bitcoin":
        if row_dict["Currency"] == "BTC":
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount"]),
                buy_asset=row_dict["Currency"],
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["Amount"]),
                sell_asset=row_dict["Currency"],
                wallet=WALLET,
            )
    elif t_type == "Sold Bitcoin":
        if row_dict["Currency"] == "BTC":
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["Amount"]),
                sell_asset=row_dict["Currency"],
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount"]),
                buy_asset=row_dict["Currency"],
                wallet=WALLET,
            )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Transaction Type"),
            "Transaction Type",
            t_type,
        )


coincorner = DataParser(
    ParserType.EXCHANGE,
    "CoinCorner",
    ["Date", "Currency", "Transaction Type", "Amount", "Balance"],
    worksheet_name="CoinCorner",
    row_handler=parse_coincorner,
)
