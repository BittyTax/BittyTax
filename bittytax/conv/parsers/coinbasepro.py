# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Coinbase Pro"

def parse_coinbase_pro_deposits_withdrawals(in_row):
    if in_row[0] == "withdrawal":
        return TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                    DataParser.parse_timestamp(in_row[1]),
                                    sell_quantity=abs(Decimal(in_row[2])),
                                    sell_asset=in_row[4],
                                    wallet=WALLET)
    elif in_row[0] == "deposit":
        return TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                    DataParser.parse_timestamp(in_row[1]),
                                    buy_quantity=in_row[2],
                                    buy_asset=in_row[4],
                                    wallet=WALLET)
    elif in_row[0] in ("match", "fee"):
        # Skip trades
        return None
    else:
        raise ValueError("Unrecognised type: " + in_row[0])

def parse_coinbase_pro_trades(in_row):
    if in_row[2] == "BUY":
        return TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                    DataParser.parse_timestamp(in_row[3]),
                                    buy_quantity=in_row[4],
                                    buy_asset=in_row[5],
                                    sell_quantity=abs(Decimal(in_row[8])) - Decimal(in_row[7]),
                                    sell_asset=in_row[9],
                                    fee_quantity=in_row[7],
                                    fee_asset=in_row[9],
                                    wallet=WALLET)
    elif in_row[2] == "SELL":
        return TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                    DataParser.parse_timestamp(in_row[3]),
                                    buy_quantity=in_row[8],
                                    buy_asset=in_row[9],
                                    sell_quantity=in_row[4],
                                    sell_asset=in_row[5],
                                    fee_quantity=in_row[7],
                                    fee_asset=in_row[9],
                                    wallet=WALLET)
    else:
        raise ValueError("Unrecognised Type: " + in_row[2])

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase Pro Deposites/Withdrawals",
           ['type', 'time', 'amount', 'balance', 'amount/balance unit', 'transfer id', 'trade id',
            'order id'],
           row_handler=parse_coinbase_pro_deposits_withdrawals)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase Pro Trades",
           ['trade id', 'product', 'side', 'created at', 'size', 'size unit', 'price', 'fee',
            'total', 'price/fee/total unit'],
           row_handler=parse_coinbase_pro_trades)
