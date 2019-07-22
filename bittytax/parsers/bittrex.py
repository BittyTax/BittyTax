# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ..record import TransactionRecord
from ..parser import DataParser

WALLET = "Bittrex"

def parse_bittrex_trades2(in_row):
    if in_row[3] == "LIMIT_BUY":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[14]),
                                 buy_quantity=in_row[5],
                                 buy_asset=in_row[1].split('-')[1],
                                 sell_quantity=in_row[8],
                                 sell_asset=in_row[1].split('-')[0],
                                 fee_quantity=in_row[7],
                                 fee_asset=in_row[1].split('-')[0],
                                 wallet=WALLET)
    elif in_row[3] == "LIMIT_SELL":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[14]),
                                 buy_quantity=in_row[8],
                                 buy_asset=in_row[1].split('-')[0],
                                 sell_quantity=in_row[5],
                                 sell_asset=in_row[1].split('-')[1],
                                 fee_quantity=in_row[7],
                                 fee_asset=in_row[1].split('-')[0],
                                 wallet=WALLET)
    else:
        raise ValueError("Unrecognised Order Type: " + in_row[2])

def parse_bittrex_trades(in_row):
    if in_row[2] == "LIMIT_BUY":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[8]),
                                 buy_quantity=in_row[3],
                                 buy_asset=in_row[1].split('-')[1],
                                 sell_quantity=in_row[6],
                                 sell_asset=in_row[1].split('-')[0],
                                 fee_quantity=in_row[5],
                                 fee_asset=in_row[1].split('-')[0],
                                 wallet=WALLET)
    elif in_row[2] == "LIMIT_SELL":
        return TransactionRecord(TransactionRecord.TYPE_TRADE,
                                 DataParser.parse_timestamp(in_row[8]),
                                 buy_quantity=in_row[6],
                                 buy_asset=in_row[1].split('-')[0],
                                 sell_quantity=in_row[3],
                                 sell_asset=in_row[1].split('-')[1],
                                 fee_quantity=in_row[5],
                                 fee_asset=in_row[1].split('-')[0],
                                 wallet=WALLET)
    else:
        raise ValueError("Unrecognised Order Type: " + in_row[2])

def parse_bittrex_deposits(in_row):
    return TransactionRecord(TransactionRecord.TYPE_DEPOSIT,
                             DataParser.parse_timestamp(in_row[4]),
                             buy_quantity=in_row[1],
                             buy_asset=in_row[2],
                             wallet=WALLET)

def parse_bittrex_withdrawals(in_row):
    return TransactionRecord(TransactionRecord.TYPE_WITHDRAWAL,
                             DataParser.parse_timestamp(in_row[4]),
                             sell_quantity=in_row[2],
                             sell_asset=in_row[1],
                             fee_quantity=in_row[7],
                             fee_asset=in_row[1],
                             wallet=WALLET)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bittrex Trades",
           ['Uuid', 'Exchange', 'TimeStamp', 'OrderType', 'Limit', 'Quantity', 'QuantityRemaining',
            'Commission', 'Price', 'PricePerUnit', 'IsConditional', 'Condition', 'ConditionTarget',
            'ImmediateOrCancel', 'Closed'],
           row_handler=parse_bittrex_trades2)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bittrex Trades",
           ['OrderUuid', 'Exchange', 'Type', 'Quantity', 'Limit', 'CommissionPaid', 'Price',
            'Opened', 'Closed'],
           row_handler=parse_bittrex_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bittrex Deposits",
           ['Id', 'Amount', 'Currency', 'Confirmations', 'LastUpdated', 'TxId', 'CryptoAddress'],
           row_handler=parse_bittrex_deposits)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bittrex Withdrawals",
           ['PaymentUuid', 'Currency', 'Amount', 'Address', 'Opened', 'Authorized',
            'PendingPayment', 'TxCost', 'TxId', 'Canceled', 'InvalidAddress'],
           row_handler=parse_bittrex_withdrawals)
