# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ...config import config
from ..dataparser import DataParser
from ..exceptions import MissingValueError
from ..out_record import TransactionOutRecord

WALLET = "ii"


def parse_ii(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if not row_dict["Symbol"]:
        return

    if not row_dict["Quantity"]:
        raise MissingValueError(
            parser.in_header.index("Quantity"), "Quantity", row_dict["Quantity"]
        )

    if row_dict["Debit"]:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=row_dict["Quantity"],
            buy_asset=row_dict["Symbol"],
            sell_quantity=row_dict["Debit"].strip("£").replace(",", ""),
            sell_asset=config.ccy,
            wallet=WALLET,
        )
    elif row_dict["Credit"]:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=row_dict["Credit"].strip("£").replace(",", ""),
            buy_asset=config.ccy,
            sell_quantity=row_dict["Quantity"],
            sell_asset=row_dict["Symbol"],
            wallet=WALLET,
        )


DataParser(
    DataParser.TYPE_SHARES,
    "Interactive Investor",
    [
        "Settlement Date",
        "Date",
        "Symbol",
        "Sedol",
        "ISIN",
        "Quantity",
        "Price",
        "Description",
        "Reference",
        "Debit",
        "Credit",
        "Running Balance",
    ],
    worksheet_name="ii",
    row_handler=parse_ii,
)
