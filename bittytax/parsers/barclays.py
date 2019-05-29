# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ..config import config
from ..record import TransactionRecord
from ..parser import DataParser

def parse_barclays(in_row):
    if in_row[2] != "Completed":
        return None

    if in_row[4] == "Buy":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[1]),
                                 buy_quantity=in_row[5],
                                 buy_asset=in_row[0],
                                 sell_quantity=in_row[6],
                                 sell_asset=config.CCY,
                                 wallet=in_row[3])
    elif in_row[4] == "Sell":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[1]),
                                 buy_quantity=in_row[6],
                                 buy_asset=config.CCY,
                                 sell_quantity=in_row[5],
                                 sell_asset=in_row[0],
                                 wallet=in_row[3])
    else:
        raise ValueError("Unrecognised type: " + in_row[4])

DataParser(DataParser.TYPE_SHARES,
           "Barclays Smart Investor",
           ['Investment', 'Date', 'Order Status', 'Account', 'Buy/Sell', 'Quantity',
            'Cost/Proceeds'],
           row_handler=parse_barclays)
