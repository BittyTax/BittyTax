# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ...record import TransactionRecord
from ..dataparser import DataParser

WALLET = "Wirex"

def parse_wirex(in_row):
    if in_row[1] == "Create":
        return None
    elif in_row[1] == "In":
        return TransactionRecord(TransactionRecord.TYPE_DEPOSIT,
                                 DataParser.parse_timestamp(in_row[2]),
                                 buy_quantity=in_row[3].split(' ')[0],
                                 buy_asset=in_row[3].split(' ')[1],
                                 wallet=WALLET)
    elif in_row[1] == "Out":
        return TransactionRecord(TransactionRecord.TYPE_WITHDRAWAL,
                                 DataParser.parse_timestamp(in_row[2]),
                                 sell_quantity=in_row[3].split(' ')[0],
                                 sell_asset=in_row[3].split(' ')[1],
                                 wallet=WALLET)
    else:
        raise ValueError("Unrecognised Type: " + in_row[1])

DataParser(DataParser.TYPE_EXCHANGE,
           "Wirex",
           ['# ', None, 'Time ', 'Amount', 'Available'],
           row_handler=parse_wirex)
