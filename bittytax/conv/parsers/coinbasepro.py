# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal

from colorama import Fore

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataParserError, UnexpectedTypeError, MissingComponentError

WALLET = "Coinbase Pro"

def parse_coinbase_pro(data_rows, parser, _filename, _args):
    for data_row in data_rows:
        if config.debug:
            sys.stderr.write("%sconv: row[%s] %s\n" % (
                Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))

        if data_row.parsed:
            continue

        try:
            parse_coinbase_pro_row(data_rows, parser, data_row)
        except DataParserError as e:
            data_row.failure = e

def parse_coinbase_pro_row(data_rows, parser, data_row):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['time'])
    data_row.parsed = True

    if row_dict['type'] == "withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(row_dict['amount'])),
                                                 sell_asset=row_dict['amount/balance unit'],
                                                 wallet=WALLET)
    elif row_dict['type'] == "deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['amount'],
                                                 buy_asset=row_dict['amount/balance unit'],
                                                 wallet=WALLET)
    elif row_dict['type'] == "match":
        if Decimal(row_dict['amount']) < 0:
            sell_quantity = abs(Decimal(row_dict['amount']))
            sell_asset = row_dict['amount/balance unit']

            buy_quantity, buy_asset = find_same_trade(data_rows, row_dict['trade id'], "match")
        else:
            buy_quantity = row_dict['amount']
            buy_asset = row_dict['amount/balance unit']

            sell_quantity, sell_asset = find_same_trade(data_rows, row_dict['trade id'], "match")

        if sell_quantity is None or buy_quantity is None:
            raise MissingComponentError(parser.in_header.index('trade id'), 'trade id',
                                        row_dict['trade id'])

        fee_quantity, fee_asset = find_same_trade(data_rows, row_dict['trade id'], "fee")

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=buy_quantity,
                                                 buy_asset=buy_asset,
                                                 sell_quantity=sell_quantity,
                                                 sell_asset=sell_asset,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('type'), 'type', row_dict['type'])

def find_same_trade(data_rows, trade_id, t_type):
    quantity = None
    asset = ""

    data_rows = [data_row for data_row in data_rows
                 if data_row.row_dict['trade id'] == trade_id and not data_row.parsed]
    for data_row in data_rows:
        if t_type == data_row.row_dict['type']:
            quantity = abs(Decimal(data_row.row_dict['amount']))
            asset = data_row.row_dict['amount/balance unit']
            data_row.timestamp = DataParser.parse_timestamp(data_row.row_dict['time'])
            data_row.parsed = True
            break

    return quantity, asset

def parse_coinbase_pro_deposits_withdrawals(data_row, parser, _filename, _args):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['time'])

    if row_dict['type'] == "withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(row_dict['amount'])),
                                                 sell_asset=row_dict['amount/balance unit'],
                                                 wallet=WALLET)
    elif row_dict['type'] == "deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['amount'],
                                                 buy_asset=row_dict['amount/balance unit'],
                                                 wallet=WALLET)
    elif row_dict['type'] in ("match", "fee"):
        # Skip trades
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index('type'), 'type', row_dict['type'])

def parse_coinbase_pro_trades2(data_row, parser, _filename, _args):
    parse_coinbase_pro_trades(data_row, parser, _filename, _args)

def parse_coinbase_pro_trades(data_row, parser, _filename, _args):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['created at'])

    if row_dict['side'] == "BUY":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['size'],
                                                 buy_asset=row_dict['size unit'],
                                                 sell_quantity=abs(Decimal(row_dict['total'])) - \
                                                               Decimal(row_dict['fee']),
                                                 sell_asset=row_dict['price/fee/total unit'],
                                                 fee_quantity=row_dict['fee'],
                                                 fee_asset=row_dict['price/fee/total unit'],
                                                 wallet=WALLET)
    elif row_dict['side'] == "SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(row_dict['total']) + \
                                                              Decimal(row_dict['fee']),
                                                 buy_asset=row_dict['price/fee/total unit'],
                                                 sell_quantity=row_dict['size'],
                                                 sell_asset=row_dict['size unit'],
                                                 fee_quantity=row_dict['fee'],
                                                 fee_asset=row_dict['price/fee/total unit'],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('side'), 'side', row_dict['side'])

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase Pro",
           ['portfolio', 'type', 'time', 'amount', 'balance', 'amount/balance unit', 'transfer id',
            'trade id', 'order id'],
           worksheet_name="Coinbase Pro",
           all_handler=parse_coinbase_pro)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase Pro Trades",
           ['portfolio', 'trade id', 'product', 'side', 'created at', 'size', 'size unit', 'price',
            'fee', 'total', 'price/fee/total unit'],
           worksheet_name="Coinbase Pro T",
           # Different handler name used to prevent data file consolidation
           row_handler=parse_coinbase_pro_trades2)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase Pro Trades",
           ['trade id', 'product', 'side', 'created at', 'size', 'size unit', 'price', 'fee',
            'total', 'price/fee/total unit'],
           worksheet_name="Coinbase Pro T",
           row_handler=parse_coinbase_pro_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase Pro Deposits/Withdrawals",
           ['type', 'time', 'amount', 'balance', 'amount/balance unit', 'transfer id', 'trade id',
            'order id'],
           worksheet_name="Coinbase Pro D,W",
           row_handler=parse_coinbase_pro_deposits_withdrawals)
