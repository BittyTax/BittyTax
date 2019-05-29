# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ..record import TransactionRecord
from ..parser import DataParser

WALLET = "Coinfloor"

def parse_coinfloor_trades(in_row):
    if in_row[7] == "Buy":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[0]),
                                 buy_quantity=in_row[3],
                                 buy_asset=in_row[1],
                                 sell_quantity=in_row[5],
                                 sell_asset=in_row[2],
                                 fee_quantity=in_row[6],
                                 fee_asset=in_row[2],
                                 wallet=WALLET)
    elif in_row[7] == "Sell":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[0]),
                                 buy_quantity=in_row[5],
                                 buy_asset=in_row[2],
                                 sell_quantity=in_row[3],
                                 sell_asset=in_row[1],
                                 fee_quantity=in_row[6],
                                 fee_asset=in_row[2],
                                 wallet=WALLET)
    else:
        raise ValueError("Unrecognised Order Type: " + in_row[7])

def parse_coinfloor_deposits_withdrawals(in_row):
    if in_row[3] == "Deposit":
        return TransactionRecord(TransactionRecord.TYPE_DEPOSIT,
                                 DataParser.parse_timestamp(in_row[0]),
                                 buy_quantity=in_row[1],
                                 buy_asset=in_row[2],
                                 wallet=WALLET)
    elif in_row[3] == "Withdrawal":
        return TransactionRecord(TransactionRecord.TYPE_WITHDRAWAL,
                                 DataParser.parse_timestamp(in_row[0]),
                                 sell_quantity=in_row[1],
                                 sell_asset=in_row[2],
                                 wallet=WALLET)
    else:
        raise ValueError("Unrecognised Type: " + in_row[3])

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinfloor Trades",
           ['Date & Time', 'Base Asset', 'Counter Asset', 'Amount', 'Price', 'Total', 'Fee',
            'Order Type'],
           row_handler=parse_coinfloor_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinfloor Deposits/Withdrawals",
           ['Date & Time', 'Amount', 'Asset', 'Type'],
           row_handler=parse_coinfloor_deposits_withdrawals)
