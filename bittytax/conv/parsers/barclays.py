# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ...config import config
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord


def parse_barclays(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["Order Status"] != "Completed":
        return

    if row_dict["Buy/Sell"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=row_dict["Quantity"],
            buy_asset=row_dict["Investment"],
            sell_quantity=row_dict["Cost/Proceeds"],
            sell_asset=config.ccy,
            wallet=row_dict["Account"],
        )
    elif row_dict["Buy/Sell"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=row_dict["Cost/Proceeds"],
            buy_asset=config.ccy,
            sell_quantity=row_dict["Quantity"],
            sell_asset=row_dict["Investment"],
            wallet=row_dict["Account"],
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Buy/Sell"), "Buy/Sell", row_dict["Buy/Sell"]
        )


DataParser(
    DataParser.TYPE_SHARES,
    "Barclays Smart Investor",
    [
        "Investment",
        "Date",
        "Order Status",
        "Account",
        "Buy/Sell",
        "Quantity",
        "Cost/Proceeds",
    ],
    worksheet_name="Barclays",
    row_handler=parse_barclays,
)
