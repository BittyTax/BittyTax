# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import MissingValueError

WALLET = "ii"

def parse_ii(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[1])

    if not in_row[2]:
        return

    if not in_row[5]:
        raise MissingValueError(5, parser.in_header[5])

    if in_row[9]:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=in_row[2],
                                                 sell_quantity=in_row[9].
                                                 strip('£').replace(',', ''),
                                                 sell_asset=config.CCY,
                                                 wallet=WALLET)
    elif in_row[10]:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[10].
                                                 strip('£').replace(',', ''),
                                                 buy_asset=config.CCY,
                                                 sell_quantity=in_row[5],
                                                 sell_asset=in_row[2],
                                                 wallet=WALLET)

DataParser(DataParser.TYPE_SHARES,
           "Interactive Investor",
           ['Settlement Date', 'Date', 'Symbol', 'Sedol', 'ISIN', 'Quantity', 'Price',
            'Description', 'Reference', 'Debit', 'Credit', 'Running Balance'],
           worksheet_name="ii",
           row_handler=parse_ii)
