# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import ConsolidateType, DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import UnexpectedTypeError, UnknownCryptoassetError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Trezor"


def parse_trezor(data_row: "DataRow", parser: DataParser, **kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(
        row_dict["Date"] + "T" + row_dict["Time"], tz="GMT+1"
    )
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TX id"), tx_dest_pos=parser.in_header.index("Address")
    )

    if not kwargs["cryptoasset"]:
        match = re.match(r".+_(\w{3,4})\.csv$", kwargs["filename"])

        if match:
            symbol = match.group(1).upper()
        else:
            raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet", ""))
    else:
        symbol = kwargs["cryptoasset"]

    if row_dict["TX type"] == "IN":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Value"]),
            buy_asset=symbol,
            fee_quantity=Decimal(row_dict["TX total"]) - Decimal(row_dict["Value"]),
            fee_asset=symbol,
            wallet=WALLET,
            note=row_dict.get("Address Label", ""),
        )
    elif row_dict["TX type"] == "OUT":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value"]),
            sell_asset=symbol,
            fee_quantity=abs(Decimal(row_dict["TX total"])) - Decimal(row_dict["Value"]),
            fee_asset=symbol,
            wallet=WALLET,
            note=row_dict.get("Address Label", ""),
        )
    elif row_dict["TX type"] == "SELF":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(0),
            sell_asset=symbol,
            fee_quantity=abs(Decimal(row_dict["TX total"])),
            fee_asset=symbol,
            wallet=WALLET,
            note=row_dict.get("Address Label", ""),
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("TX type"), "TX type", row_dict["TX type"])


DataParser(
    ParserType.WALLET,
    "Trezor",
    [
        "Date",
        "Time",
        "TX id",
        "Address",
        "Address Label",
        "TX type",
        "Value",
        "TX total",
        "Balance",
    ],
    worksheet_name="Trezor",
    row_handler=parse_trezor,
    consolidate_type=ConsolidateType.HEADER_MATCH,
)

DataParser(
    ParserType.WALLET,
    "Trezor",
    ["Date", "Time", "TX id", "Address", "TX type", "Value", "TX total", "Balance"],
    worksheet_name="Trezor",
    row_handler=parse_trezor,
)
