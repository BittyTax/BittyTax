# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

import re
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Tuple

from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedContentError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Volt"


def parse_volt(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(
        row_dict["time"], tz=config.local_timezone, dayfirst=config.date_is_day_first
    )

    amount, symbol = _get_amount(row_dict["amount"].replace(",", ""))
    if amount is None or symbol is None:
        raise UnexpectedContentError(parser.in_header.index("amount"), "amount", row_dict["amount"])

    if "fee" in row_dict:
        fee_quantity = Decimal(row_dict["fee"])
        fee_asset = symbol
    else:
        fee_quantity = None
        fee_asset = ""

    if row_dict["status"] == "Received":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=symbol,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["status"] == "OUT":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=amount,
            sell_asset=symbol,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("status"), "status", row_dict["status"])


def _get_amount(amount_str: str) -> Tuple[Optional[Decimal], str]:
    match = re.match(r"^[-+](\d+|\d+\.\d+) (\w{3,4}) |$", amount_str)

    if match:
        amount = match.group(1)
        symbol = match.group(2)
        return Decimal(amount), symbol
    return None, ""


DataParser(
    ParserType.WALLET,
    "Volt",
    ["time", "status", "address", "amount", "fee", "txid"],
    worksheet_name="Volt",
    row_handler=parse_volt,
)

DataParser(
    ParserType.WALLET,
    "Volt",
    ["time", "status", "address", "amount", "fee", "txid", ""],
    worksheet_name="Volt",
    row_handler=parse_volt,
)

DataParser(
    ParserType.WALLET,
    "Volt",
    ["time", "status", "address", "amount", "txid"],
    worksheet_name="Volt",
    row_handler=parse_volt,
)

DataParser(
    ParserType.WALLET,
    "Volt",
    ["time", "status", "address", "amount", "txid", ""],
    worksheet_name="Volt",
    row_handler=parse_volt,
)
