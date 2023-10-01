# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Coinomi"


def parse_coinomi(data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time(ISO8601-UTC)"])

    if Decimal(row_dict["Value"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Value"]),
            buy_asset=row_dict["Symbol"],
            wallet=WALLET,
            note=row_dict["AddressName"],
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Value"])) - Decimal(row_dict["Fees"]),
            sell_asset=row_dict["Symbol"],
            fee_quantity=Decimal(row_dict["Fees"]),
            fee_asset=row_dict["Symbol"],
            wallet=WALLET,
            note=row_dict["AddressName"],
        )


DataParser(
    ParserType.WALLET,
    "Coinomi",
    [
        "Asset",
        "AccountName",
        "Address",
        "AddressName",
        "Value",
        "Symbol",
        "Fees",
        "InternalTransfer",
        "TransactionID",
        "Time(UTC)",
        "Time(ISO8601-UTC)",
        "BlockExplorer",
    ],
    worksheet_name="Coinomi",
    row_handler=parse_coinomi,
)
