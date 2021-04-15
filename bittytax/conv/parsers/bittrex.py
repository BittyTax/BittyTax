# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Bittrex"

def parse_bittrex_trades2(data_row, parser, _filename, _args):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['TimeStamp'])

    if row_dict['OrderType'] in ("LIMIT_BUY", 'MARKET_BUY'):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity= \
                                                     Decimal(row_dict['Quantity']) - \
                                                     Decimal(row_dict['QuantityRemaining']),
                                                 buy_asset=row_dict['Exchange'].split('-')[1],
                                                 sell_quantity=row_dict['Price'],
                                                 sell_asset=row_dict['Exchange'].split('-')[0],
                                                 fee_quantity=row_dict['Commission'],
                                                 fee_asset=row_dict['Exchange'].split('-')[0],
                                                 wallet=WALLET)
    elif row_dict['OrderType'] in ("LIMIT_SELL", 'MARKET_SELL'):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Price'],
                                                 buy_asset=row_dict['Exchange'].split('-')[0],
                                                 sell_quantity= \
                                                     Decimal(row_dict['Quantity']) - \
                                                     Decimal(row_dict['QuantityRemaining']),
                                                 sell_asset=row_dict['Exchange'].split('-')[1],
                                                 fee_quantity=row_dict['Commission'],
                                                 fee_asset=row_dict['Exchange'].split('-')[0],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('OrderType'), 'OrderType',
                                  row_dict['OrderType'])

def parse_bittrex_trades(data_row, parser, _filename, _args):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Opened'])

    if row_dict['Type'] in ("LIMIT_BUY", 'MARKET_BUY'):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Quantity'],
                                                 buy_asset=row_dict['Exchange'].split('-')[1],
                                                 sell_quantity=row_dict['Price'],
                                                 sell_asset=row_dict['Exchange'].split('-')[0],
                                                 fee_quantity=row_dict['CommissionPaid'],
                                                 fee_asset=row_dict['Exchange'].split('-')[0],
                                                 wallet=WALLET)
    elif row_dict['Type'] in ("LIMIT_SELL", 'MARKET_SELL'):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Price'],
                                                 buy_asset=row_dict['Exchange'].split('-')[0],
                                                 sell_quantity=row_dict['Quantity'],
                                                 sell_asset=row_dict['Exchange'].split('-')[1],
                                                 fee_quantity=row_dict['CommissionPaid'],
                                                 fee_asset=row_dict['Exchange'].split('-')[0],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

def parse_bittrex_deposits2(data_row, _parser, _filename, _args):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['LastUpdatedDate'])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                             data_row.timestamp,
                                             buy_quantity=row_dict['Amount'],
                                             buy_asset=row_dict['Currency'],
                                             wallet=WALLET)

def parse_bittrex_deposits(data_row, _parser, _filename, _args):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['LastUpdated'])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                             data_row.timestamp,
                                             buy_quantity=row_dict['Amount'],
                                             buy_asset=row_dict['Currency'],
                                             wallet=WALLET)

def parse_bittrex_withdrawals2(data_row, _parser, _filename, _args):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['OpenedDate'])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                             data_row.timestamp,
                                             sell_quantity=row_dict['Amount'],
                                             sell_asset=row_dict['Currency'],
                                             fee_quantity=row_dict['TxFee'],
                                             fee_asset=row_dict['Currency'],
                                             wallet=WALLET)

def parse_bittrex_withdrawals(data_row, _parser, _filename, _args):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(data_row.row[4]) # Opened/OpenDate

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                             data_row.timestamp,
                                             sell_quantity=row_dict['Amount'],
                                             sell_asset=row_dict['Currency'],
                                             fee_quantity=data_row.row[7], # TxCost/TxFee
                                             fee_asset=row_dict['Currency'],
                                             wallet=WALLET)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bittrex Trades",
           ['Uuid', 'Exchange', 'TimeStamp', 'OrderType', 'Limit', 'Quantity', 'QuantityRemaining',
            'Commission', 'Price', 'PricePerUnit', 'IsConditional', 'Condition', 'ConditionTarget',
            'ImmediateOrCancel', 'Closed', 'TimeInForceTypeId', 'TimeInForce'],
           worksheet_name="Bittrex T",
           row_handler=parse_bittrex_trades2)

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
            'CryptoAddress', 'Source'],
           worksheet_name="Bittrex D",
           row_handler=parse_bittrex_deposits2)

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
