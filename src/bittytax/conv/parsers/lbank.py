# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import re
from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Optional, Tuple, Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "LBank"


def parse_lbank_trades(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"].replace("UTC0", ""))

    if row_dict["Type"] != "SPOT":
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])

    fee, fee_asset = _get_amount(row_dict["Transaction Fee"])
    volume, volume_asset = _get_amount(row_dict["Volume"])
    turnover, turnover_asset = _get_amount(row_dict["Turnover"])

    if row_dict["Direction"] == "buy_market":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=volume,
            buy_asset=volume_asset,
            sell_quantity=turnover,
            sell_asset=turnover_asset,
            fee_quantity=fee,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["Direction"] == "sell_market":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=turnover,
            buy_asset=turnover_asset,
            sell_quantity=volume,
            sell_asset=volume_asset,
            fee_quantity=fee,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Direction"), "Direction", row_dict["Direction"]
        )


def _get_amount(data_field: str) -> Tuple[Optional[Decimal], str]:
    match = re.match(r"^(\d+\.\d+)([a-z]+)$", data_field)

    if match:
        amount = match.group(1)
        symbol = match.group(2)
        return Decimal(amount), symbol.upper()
    return None, ""


DataParser(
    ParserType.EXCHANGE,
    "LBank Trades",
    [
        "ID",
        "Method",
        "Type",
        "Pair",
        "Time",
        "Direction",
        "Average Price",
        "Volume",
        "Turnover",
        "Transaction Fee Rate",
        "Transaction Fee",
        "Remarks",
    ],
    worksheet_name="LBank T",
    row_handler=parse_lbank_trades,
)
