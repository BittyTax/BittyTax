# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ...record import TransactionRecord
from ..dataparser import DataParser

WALLET = "Crypsty"

def parse_cryptsy(in_row):
    if in_row[1] == "Buy":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[8], tz='US/Eastern'),
                                 buy_quantity=in_row[4],
                                 buy_asset=in_row[2].split('/')[0],
                                 sell_quantity=in_row[7],
                                 sell_asset=in_row[2].split('/')[1],
                                 fee_quantity=in_row[6],
                                 fee_asset=in_row[2].split('/')[1],
                                 wallet=WALLET)
    elif in_row[1] == "Sell":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[8], tz='US/Eastern'),
                                 buy_quantity=in_row[7],
                                 buy_asset=in_row[2].split('/')[1],
                                 sell_quantity=in_row[4],
                                 sell_asset=in_row[2].split('/')[0],
                                 fee_quantity=in_row[6],
                                 fee_asset=in_row[2].split('/')[1],
                                 wallet=WALLET)
    else:
        raise ValueError("Unrecognised OrderType: " + in_row[1])

DataParser(DataParser.TYPE_EXCHANGE,
           "Cryptsy",
           ['TradeID', 'OrderType', 'Market', 'Price', 'Quantity', 'Total', 'Fee', 'Net',
            'Timestamp'],
           row_handler=parse_cryptsy)
