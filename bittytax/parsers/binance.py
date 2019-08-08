# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..record import TransactionRecord
from ..parser import DataParser

WALLET = "Binance"

def parse_binance_trades(in_row):
    if in_row[2] == "BUY":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[0]),
                                 buy_quantity=in_row[4],
                                 buy_asset=in_row[7],
                                 sell_quantity=in_row[5],
                                 sell_asset=in_row[1].replace(in_row[7], ''),
                                 fee_quantity=in_row[6],
                                 fee_asset=in_row[7],
                                 wallet=WALLET)
    elif in_row[2] == "SELL":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[0]),
                                 buy_quantity=in_row[5],
                                 buy_asset=in_row[7],
                                 sell_quantity=in_row[4],
                                 sell_asset=in_row[1].replace(in_row[7], ''),
                                 fee_quantity=in_row[6],
                                 fee_asset=in_row[7],
                                 wallet=WALLET)
    else:
        raise ValueError("Unrecognised Type: " + in_row[2])

def parse_binance_deposits_withdrawals(in_row):
    if in_row[8] != "Completed":
        return None

    # Assume that a transaction fee of 0 must be a Deposit
    if Decimal(in_row[3]) == 0:
        return TransactionRecord(TransactionRecord.TYPE_DEPOSIT,
                                 DataParser.parse_timestamp(in_row[0]),
                                 buy_quantity=in_row[2],
                                 buy_asset=in_row[1],
                                 wallet=WALLET)
    else:
        return TransactionRecord(TransactionRecord.TYPE_WITHDRAWAL,
                                 DataParser.parse_timestamp(in_row[0]),
                                 sell_quantity=in_row[2],
                                 sell_asset=in_row[1],
                                 fee_quantity=in_row[3],
                                 fee_asset=in_row[1],
                                 wallet=WALLET)

DataParser(DataParser.TYPE_EXCHANGE,
           "Binance Trades",
           ['Date(UTC)', 'Market', 'Type', 'Price', 'Amount', 'Total', 'Fee', 'Fee Coin'],
           row_handler=parse_binance_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "Binance Deposits/Withdrawals",
           ['Date', 'Coin', 'Amount', 'TransactionFee', 'Address', 'TXID', 'SourceAddress',
            'PaymentID', 'Status'],
           row_handler=parse_binance_deposits_withdrawals)
