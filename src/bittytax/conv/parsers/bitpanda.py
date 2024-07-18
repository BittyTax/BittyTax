# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

HEADER_V2 = [
    "Transaction ID",
    "Timestamp",
    "Transaction Type",
    "In/Out",
    "Amount Fiat",
    "Fiat",
    "Amount Asset",
    "Asset",
    "Asset market price",
    "Asset market price currency",
    "Asset class",
    "Product ID",
    "Fee",
    "Fee asset",
    "Spread",
    "Spread Currency",
    "Tax Fiat",
]

HEADER = [
    "ID",
    "Type",
    "In/Out",
    "Amount Fiat",
    "Fee",
    "Fiat",
    "Amount Asset",
    "Asset",
    "Status",
    "Created at",
]

WALLET = "Bitpanda"


def parse_bitpanda(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    # Skip break between tables
    if len(data_row.row) == 1 or data_row.row in (HEADER, HEADER_V2):
        return

    row_dict = data_row.row_dict
    if "Timestamp" in row_dict:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["Timestamp"])
    else:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["Created at"])

    if "Type" in row_dict:
        if row_dict["Status"] != "finished":
            return

        row_dict["Transaction Type"] = row_dict["Type"]

    if row_dict["Transaction Type"] == "deposit":
        if row_dict["Amount Asset"] == "-" or Decimal(row_dict["Amount Asset"]) == Decimal(0):
            buy_quantity = Decimal(row_dict["Amount Fiat"])
            buy_asset = row_dict["Fiat"]
        else:
            buy_quantity = Decimal(row_dict["Amount Asset"])
            buy_asset = row_dict["Asset"]

        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=buy_quantity + Decimal(row_dict["Fee"]),
            buy_asset=buy_asset,
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=buy_asset,
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "withdrawal":
        if row_dict["Amount Asset"] == "-" or Decimal(row_dict["Amount Asset"]) == Decimal(0):
            sell_quantity = Decimal(row_dict["Amount Fiat"])
            sell_asset = row_dict["Fiat"]
        else:
            sell_quantity = Decimal(row_dict["Amount Asset"])
            sell_asset = row_dict["Asset"]

        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=sell_asset,
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount Asset"]),
            buy_asset=row_dict["Asset"],
            sell_quantity=Decimal(row_dict["Amount Fiat"]),
            sell_asset=row_dict["Fiat"],
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount Fiat"]),
            buy_asset=row_dict["Fiat"],
            sell_quantity=Decimal(row_dict["Amount Asset"]),
            sell_asset=row_dict["Asset"],
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
    "Bitpanda",
    list(HEADER_V2),
    worksheet_name="bitpanda",
    row_handler=parse_bitpanda,
)

DataParser(
    ParserType.EXCHANGE,
    "Bitpanda",
    list(HEADER),
    worksheet_name="bitpanda",
    row_handler=parse_bitpanda,
)
