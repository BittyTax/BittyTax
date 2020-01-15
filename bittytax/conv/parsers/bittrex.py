# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Bittrex"

def parse_bittrex_trades2(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[14])

    if in_row[3] == "LIMIT_BUY":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[5]) - \
                                                              Decimal(in_row[6]),
                                                 buy_asset=in_row[1].split('-')[1],
                                                 sell_quantity=in_row[8],
                                                 sell_asset=in_row[1].split('-')[0],
                                                 fee_quantity=in_row[7],
                                                 fee_asset=in_row[1].split('-')[0],
                                                 wallet=WALLET)
    elif in_row[3] == "LIMIT_SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[8],
                                                 buy_asset=in_row[1].split('-')[0],
                                                 sell_quantity=Decimal(in_row[5]) - \
                                                               Decimal(in_row[6]),
                                                 sell_asset=in_row[1].split('-')[1],
                                                 fee_quantity=in_row[7],
                                                 fee_asset=in_row[1].split('-')[0],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(3, parser.in_header[3], in_row[3])

def parse_bittrex_trades(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[8])

    if in_row[2] == "LIMIT_BUY":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[1].split('-')[1],
                                                 sell_quantity=in_row[6],
                                                 sell_asset=in_row[1].split('-')[0],
                                                 fee_quantity=in_row[5],
                                                 fee_asset=in_row[1].split('-')[0],
                                                 wallet=WALLET)
    elif in_row[2] == "LIMIT_SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[6],
                                                 buy_asset=in_row[1].split('-')[0],
                                                 sell_quantity=in_row[3],
                                                 sell_asset=in_row[1].split('-')[1],
                                                 fee_quantity=in_row[5],
                                                 fee_asset=in_row[1].split('-')[0],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

def parse_bittrex_deposits2(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[4])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                             data_row.timestamp,
                                             buy_quantity=in_row[2],
                                             buy_asset=in_row[1],
                                             wallet=WALLET)

def parse_bittrex_deposits(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[4])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                             data_row.timestamp,
                                             buy_quantity=in_row[1],
                                             buy_asset=in_row[2],
                                             wallet=WALLET)

def parse_bittrex_withdrawals(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[4])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                             data_row.timestamp,
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
           worksheet_name="Bittrex T",
           row_handler=parse_bittrex_trades2)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bittrex Trades",
           ['OrderUuid', 'Exchange', 'Type', 'Quantity', 'Limit', 'CommissionPaid', 'Price',
            'Opened', 'Closed'],
           worksheet_name="Bittrex T",
           row_handler=parse_bittrex_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bittrex Deposits",
           ['Id', 'Currency', 'Amount', 'Confirmations', 'LastUpdatedDate', 'TxId',
            'CryptoAddress'],
           worksheet_name="Bittrex D",
           row_handler=parse_bittrex_deposits2)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bittrex Deposits",
           ['Id', 'Amount', 'Currency', 'Confirmations', 'LastUpdated', 'TxId', 'CryptoAddress'],
           worksheet_name="Bittrex D",
           row_handler=parse_bittrex_deposits)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bittrex Withdrawals",
           ['PaymentUuid', 'Currency', 'Amount', 'Address', 'OpenedDate', 'Authorized', 'Pending',
            'TxFee', 'Canceled', 'TxId'],
           worksheet_name="Bittrex W",
           row_handler=parse_bittrex_withdrawals)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bittrex Withdrawals",
           ['PaymentUuid', 'Currency', 'Amount', 'Address', 'Opened', 'Authorized',
            'PendingPayment', 'TxCost', 'TxId', 'Canceled', 'InvalidAddress'],
           worksheet_name="Bittrex W",
           row_handler=parse_bittrex_withdrawals)
