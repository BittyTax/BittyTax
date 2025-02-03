# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2025

import re
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Revolut"


def parse_revolut(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"], tz=config.local_timezone)

    value = _get_fiat_value(row_dict["Value"], data_row.timestamp)
    fee_value = _get_fiat_value(row_dict["Fees"], data_row.timestamp)

    if row_dict["Type"] == "Receive":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"].replace(",", "")),
            buy_asset=row_dict["Symbol"],
            buy_value=value,
            fee_quantity=fee_value,
            fee_asset=config.ccy,
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=value,
            buy_asset=config.ccy,
            sell_quantity=Decimal(row_dict["Quantity"].replace(",", "")),
            sell_asset=row_dict["Symbol"],
            fee_quantity=fee_value,
            fee_asset=config.ccy,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _get_fiat_value(value_str: str, timestamp: datetime) -> Optional[Decimal]:
    match = re.match(r"^([£€$]?)([\d|,]+\.\d{2})$", value_str)
    if match:
        symbol = match.group(1)
        value = match.group(2).replace(",", "")

        if symbol == "£":
            return DataParser.convert_currency(value, "GBP", timestamp)
        if symbol == "€":
            return DataParser.convert_currency(value, "EUR", timestamp)
        if symbol == "$":
            return DataParser.convert_currency(value, "USD", timestamp)

    raise RuntimeError(f"Unexpected fiat value: {value_str}")


DataParser(
    ParserType.EXCHANGE,
    "Revolut",
    ["Symbol", "Type", "Quantity", "Price", "Value", "Fees", "Date"],
    worksheet_name="Revolut",
    row_handler=parse_revolut,
)
