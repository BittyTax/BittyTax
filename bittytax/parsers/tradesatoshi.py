# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..record import TransactionRecord
from ..parser import DataParser

WALLET = "TradeSatoshi"

def parse_tradesatoshi_deposits(in_row):
    return TransactionRecord(TransactionRecord.TYPE_DEPOSIT,
                             DataParser.parse_timestamp(in_row[7]),
                             buy_quantity=in_row[3],
                             buy_asset=in_row[2],
                             wallet=WALLET)

def parse_tradesatoshi_withdrawals(in_row):
    return TransactionRecord(TransactionRecord.TYPE_WITHDRAWAL,
                             DataParser.parse_timestamp(in_row[10]),
                             sell_quantity=Decimal(in_row[3]) - Decimal(in_row[4]),
                             sell_asset=in_row[2],
                             fee_quantity=in_row[4],
                             fee_asset=in_row[2],
                             wallet=WALLET)

def parse_tradesatoshi_trades(in_row, *_):
    if in_row[2] == "Buy":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[6]),
                                 buy_quantity=in_row[3],
                                 buy_asset=in_row[1].split('/')[0],
                                 sell_quantity=Decimal(in_row[3]) * Decimal(in_row[4]),
                                 sell_asset=in_row[1].split('/')[1],
                                 fee_quantity=in_row[5],
                                 fee_asset=in_row[1].split('/')[1],
                                 wallet=WALLET)
    elif in_row[2] == "Sell":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[6]),
                                 buy_quantity=Decimal(in_row[3]) * Decimal(in_row[4]),
                                 buy_asset=in_row[1].split('/')[1],
                                 sell_quantity=in_row[3],
                                 sell_asset=in_row[1].split('/')[0],
                                 fee_quantity=in_row[5],
                                 fee_asset=in_row[1].split('/')[1],
                                 wallet=WALLET)
    else:
        raise ValueError("Unrecognised TradeType: " + in_row[2])

DataParser(DataParser.TYPE_EXCHANGE,
           "TradeSatoshi Deposits",
           ['Id', 'Currency', 'Symbol', 'Amount', 'Status', 'Confirmations', 'TxId', 'TimeStamp'],
           parse_tradesatoshi_deposits,
           None)

DataParser(DataParser.TYPE_EXCHANGE,
           "TradeSatoshi Withdrawals",
           ['Id', 'User', 'Symbol', 'Amount', 'Fee', 'Net Amount', 'Status', 'Confirmations',
            'TxId', 'Address', 'TimeStamp'],
           parse_tradesatoshi_withdrawals,
           None)

DataParser(DataParser.TYPE_EXCHANGE,
           "TradeSatoshi Trades",
           ['Id', 'TradePair', lambda c: c in ('TradeType', 'TradeHistoryType'), 'Amount', 'Rate',
            'Fee', lambda c: c.lower() == 'timestamp', 'IsApi'],
           parse_tradesatoshi_trades,
           None)
