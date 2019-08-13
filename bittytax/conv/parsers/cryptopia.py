# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Cryptopia"

def parse_cryptopia_deposits(in_row):
    return TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                DataParser.parse_timestamp(in_row[7]),
                                buy_quantity=in_row[2],
                                buy_asset=in_row[1],
                                wallet=WALLET)

def parse_cryptopia_withdrawals(in_row):
    return TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                DataParser.parse_timestamp(in_row[7]),
                                sell_quantity=Decimal(in_row[2]) - Decimal(in_row[3]),
                                sell_asset=in_row[1],
                                fee_quantity=in_row[3],
                                fee_asset=in_row[1],
                                wallet=WALLET)

def parse_cryptopia_trades(in_row):
    if in_row[2] == "Buy":
        return TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                    DataParser.parse_timestamp(in_row[7]),
                                    buy_quantity=in_row[4],
                                    buy_asset=in_row[1].split('/')[0],
                                    sell_quantity=Decimal(in_row[3]) * Decimal(in_row[4]),
                                    sell_asset=in_row[1].split('/')[1],
                                    fee_quantity=in_row[6],
                                    fee_asset=in_row[1].split('/')[0],
                                    wallet=WALLET)
    elif in_row[2] == "Sell":
        return TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                    DataParser.parse_timestamp(in_row[7]),
                                    buy_quantity=Decimal(in_row[3]) * Decimal(in_row[4]),
                                    buy_asset=in_row[1].split('/')[1],
                                    sell_quantity=in_row[4],
                                    sell_asset=in_row[1].split('/')[0],
                                    fee_quantity=in_row[6],
                                    fee_asset=in_row[1].split('/')[1],
                                    wallet=WALLET)
    else:
        raise ValueError("Unrecognised Type: " + in_row[2])

DataParser(DataParser.TYPE_EXCHANGE,
           "Cryptopia Deposits",
           ['#', 'Currency', 'Amount', 'Status', 'Type', 'Transaction', 'Conf.', 'Timestamp'],
           row_handler=parse_cryptopia_deposits)

DataParser(DataParser.TYPE_EXCHANGE,
           "Cryptopia Withdrawals",
           ['#', 'Currency', 'Amount', 'Fee', 'Status', 'TransactionId', 'Address', 'Timestamp'],
           row_handler=parse_cryptopia_withdrawals)

DataParser(DataParser.TYPE_EXCHANGE,
           "Cryptopia Trades",
           ['#', 'Market', 'Type', 'Rate', 'Amount', 'Total', 'Fee', 'Timestamp'],
           row_handler=parse_cryptopia_trades)
