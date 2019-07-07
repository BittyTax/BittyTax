# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ..record import TransactionRecord
from ..parser import DataParser

WALLET = "Bitstamp"

def parse_bitstamp(in_row):
    if in_row[0] in ("Ripple deposit", "Deposit"):
        return TransactionRecord(TransactionRecord.TYPE_DEPOSIT,
                                 DataParser.parse_timestamp(in_row[1]),
                                 buy_quantity=in_row[3].split(' ')[0],
                                 buy_asset=in_row[3].split(' ')[1],
                                 wallet=WALLET)
    elif in_row[0] in ("Ripple payment", "Withdrawal"):
        return TransactionRecord(TransactionRecord.TYPE_WITHDRAWAL,
                                 DataParser.parse_timestamp(in_row[1]),
                                 sell_quantity=in_row[3].split(' ')[0],
                                 sell_asset=in_row[3].split(' ')[1],
                                 wallet=WALLET)
    elif in_row[0] == "Market":
        if in_row[7] == "Buy":
            return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                     DataParser.parse_timestamp(in_row[1]),
                                     buy_quantity=in_row[3].split(' ')[0],
                                     buy_asset=in_row[3].split(' ')[1],
                                     sell_quantity=in_row[4].split(' ')[0],
                                     sell_asset=in_row[4].split(' ')[1],
                                     fee_quantity=in_row[6].split(' ')[0],
                                     fee_asset=in_row[6].split(' ')[1],
                                     wallet=WALLET)
        elif in_row[7] == "Sell":
            return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                     DataParser.parse_timestamp(in_row[1]),
                                     buy_quantity=in_row[4].split(' ')[0],
                                     buy_asset=in_row[4].split(' ')[1],
                                     sell_quantity=in_row[3].split(' ')[0],
                                     sell_asset=in_row[3].split(' ')[1],
                                     fee_quantity=in_row[6].split(' ')[0],
                                     fee_asset=in_row[6].split(' ')[1],
                                     wallet=WALLET)
        else:
            raise ValueError("Unrecognised Sub Type: " + in_row[7])
    else:
        raise ValueError("Unrecognised Type: " + in_row[0])

DataParser(DataParser.TYPE_EXCHANGE,
           "Bitstamp",
           ['Type', 'Datetime', 'Account', 'Amount', 'Value', 'Rate', 'Fee', 'Sub Type'],
           row_handler=parse_bitstamp)
