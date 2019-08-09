# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ...record import TransactionRecord
from ..dataparser import DataParser

WALLET = "Bifinex"

def parse_bitfinex_trades(in_row):
    if Decimal(in_row[2]) > 0:
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[6], dayfirst=True),
                                 buy_quantity=in_row[2],
                                 buy_asset=in_row[1].split('/')[0],
                                 sell_quantity=Decimal(in_row[3]) * Decimal(in_row[2]),
                                 sell_asset=in_row[1].split('/')[1],
                                 fee_quantity=abs(Decimal(in_row[4])),
                                 fee_asset=in_row[5],
                                 wallet=WALLET)
    else:
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[6], dayfirst=True),
                                 buy_quantity=Decimal(in_row[3]) * abs(Decimal(in_row[2])),
                                 buy_asset=in_row[1].split('/')[1],
                                 sell_quantity=abs(Decimal(in_row[2])),
                                 sell_asset=in_row[1].split('/')[0],
                                 fee_quantity=abs(Decimal(in_row[4])),
                                 fee_asset=in_row[5],
                                 wallet=WALLET)

def parse_bitfinex_deposits_withdrawals(in_row):
    if in_row[3] != "COMPLETED":
        return None

    if Decimal(in_row[4]) > 0:
        return TransactionRecord(TransactionRecord.TYPE_DEPOSIT,
                                 DataParser.parse_timestamp(in_row[1], dayfirst=True),
                                 buy_quantity=in_row[4],
                                 buy_asset=in_row[2],
                                 fee_quantity=abs(Decimal(in_row[5])),
                                 fee_asset=in_row[2],
                                 wallet=WALLET)

    else:
        return TransactionRecord(TransactionRecord.TYPE_WITHDRAWAL,
                                 DataParser.parse_timestamp(in_row[1], dayfirst=True),
                                 sell_quantity=abs(Decimal(in_row[4])),
                                 sell_asset=in_row[2],
                                 fee_quantity=abs(Decimal(in_row[5])),
                                 fee_asset=in_row[2],
                                 wallet=WALLET)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bitfinex Trades",
           ['#', 'PAIR', 'AMOUNT', 'PRICE', 'FEE', 'FEE CURRENCY', 'DATE', 'ORDER ID'],
           row_handler=parse_bitfinex_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bitfinex Deposits/Withdrawals",
           ['#', 'DATE', 'CURRENCY', 'STATUS', 'AMOUNT', 'FEES', 'DESCRIPTION', 'TRANSACTION ID'],
           row_handler=parse_bitfinex_deposits_withdrawals)
