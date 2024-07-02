# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

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

WALLET = "PayPal"


def parse_paypal(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["DateTime"])
    currency = parser.args[0].group(1)

    market_value = DataParser.convert_currency(
        row_dict[f"Market Value ({currency})"],
        currency,
        data_row.timestamp,
    )

    if row_dict["Transaction Type"] in ("BUY", "SELL"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Asset In (Quantity)"]),
            buy_asset=row_dict["Asset In (Currency)"],
            buy_value=market_value,
            sell_quantity=Decimal(row_dict["Asset Out (Quantity)"]),
            sell_asset=row_dict["Asset Out (Currency)"],
            sell_value=market_value,
            fee_quantity=Decimal(row_dict["Transaction Fee (Quantity)"]),
            fee_asset=row_dict["Transaction Fee (Currency)"],
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
    "PayPal",
    [
        "DateTime",
        "Transaction Type",
        "Asset In (Quantity)",
        "Asset In (Currency)",
        "Asset Out (Quantity)",
        "Asset Out (Currency)",
        "Transaction Fee (Quantity)",
        "Transaction Fee (Currency)",
        lambda h: re.match(r"^Market Value \((\w{3})\)", h),
    ],
    worksheet_name="PayPal",
    row_handler=parse_paypal,
)
