# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import sys
import copy

from decimal import Decimal, ROUND_DOWN

from colorama import Fore

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataRowError, UnexpectedTypeError, UnexpectedTradingPairError

WALLET = "Hotbit"

QUOTE_ASSETS = ['ALGO', 'ATOM', 'AUDIO', 'BCH', 'BTC', 'CHZ', 'DOGE', 'DYDX', 'ENS', 'ETC',
                'ETH', 'FSN', 'HOT', 'ICP', 'IMX', 'KDA', 'LEV', 'LRC', 'LTC', 'MFT',
                'MINA', 'NEAR', 'NEXO', 'NFT', 'QNT', 'QTUM', 'RVN', 'SHIB', 'SLP', 'SOL',
                'TFUEL', 'THETA', 'TRB', 'TRX', 'UNI', 'USD', 'USDC', 'USDT', 'VET', 'XEM',
                'XMR', 'XRP', 'nUSD']

PRECISION = Decimal('0.00000000')
MAKER_FEE = Decimal(0.0005)
TAKER_FEE = Decimal(0.002)

def parse_hotbit_orders_v3(data_rows, parser, **kwargs):
    parse_hotbit_orders_v1(data_rows, parser, type_str='Side', amount_str='Volume', **kwargs)

def parse_hotbit_orders_v2(data_rows, parser, **kwargs):
    parse_hotbit_orders_v1(data_rows, parser, type_str='Side', amount_str='Amount', **kwargs)

def parse_hotbit_orders_v1(data_rows, parser, **kwargs):
    if kwargs.get('type_str'):
        type_str = kwargs['type_str']
    else:
        type_str = 'Type'

    if kwargs.get('amount_str'):
        amount_str = kwargs['amount_str']
    else:
        amount_str = 'Amount'

    for row_index, data_row in enumerate(data_rows):
        if config.debug:
            sys.stderr.write("%sconv: row[%s] %s\n" % (
                Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))

        if data_row.parsed:
            continue

        try:
            parse_hotbit_orders_row(data_rows, parser, data_row, row_index, type_str, amount_str)
        except DataRowError as e:
            data_row.failure = e

def parse_hotbit_orders_row(data_rows, parser, data_row, row_index, type_str, amount_str):
    if data_row.row[0] == '':
        return

    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date'])
    data_row.parsed = True

    # Have to -re-caclulate the total as it's incorrect for USDT trades
    total = Decimal(row_dict['Price'].split(' ')[0]) * Decimal(row_dict[amount_str].split(' ')[0])

    # Maker fees are a credit (+), add as gift-received
    if row_dict['Fee'][0] == '+':
        # Have to re-calculate the fee as rounding in datafile is incorrect
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []
        dup_data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=(total * MAKER_FEE). \
                                                         quantize(PRECISION, rounding=ROUND_DOWN),
                                                     buy_asset=row_dict['Fee'].split(' ')[1],
                                                     wallet=WALLET)
        data_rows.insert(row_index + 1, dup_data_row)

        fee_quantity = None
        fee_asset = ''
    else:
        # Have to re-calculate the fee as rounding in datafile is incorrect
        fee_quantity = (total * TAKER_FEE).quantize(PRECISION, rounding=ROUND_DOWN)
        fee_asset = row_dict['Fee'].split(' ')[1]

    if row_dict[type_str] == "BUY":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict[amount_str].split(' ')[0],
                                                 buy_asset=row_dict['Pair'].split('/')[0],
                                                 sell_quantity=total.quantize(PRECISION),
                                                 sell_asset=row_dict['Pair'].split('/')[1],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    elif row_dict[type_str] == "SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=total.quantize(PRECISION),
                                                 buy_asset=row_dict['Pair'].split('/')[1],
                                                 sell_quantity=row_dict[amount_str].split(' ')[0],
                                                 sell_asset=row_dict['Pair'].split('/')[0],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index(type_str), type_str, row_dict[type_str])

def parse_hotbit_trades(data_rows, parser, **_kwargs):
    for row_index, data_row in enumerate(data_rows):
        if config.debug:
            sys.stderr.write("%sconv: row[%s] %s\n" % (
                Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))

        if data_row.parsed:
            continue

        try:
            parse_hotbit_trades_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e

def parse_hotbit_trades_row(data_rows, parser, data_row, row_index):
    row_dict = data_row.row_dict

    if '_' in row_dict['time']:
        data_row.timestamp = DataParser.parse_timestamp(row_dict['time'].replace('_', ' '))
    else:
        data_row.timestamp = DataParser.parse_timestamp(row_dict['time'], tz='Asia/Hong_Kong')
    data_row.parsed = True

    base_asset, quote_asset = split_trading_pair(row_dict['market'])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(parser.in_header.index('market'), 'market',
                                         row_dict['market'])

    # Maker fees are negative, add as gift-received
    if Decimal(row_dict['fee']) < 0:
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []

        dup_data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=abs(Decimal(row_dict['fee']). \
                                                             quantize(PRECISION)),
                                                     buy_asset=quote_asset,
                                                     wallet=WALLET)
        data_rows.insert(row_index + 1, dup_data_row)

        fee_quantity = None
        fee_asset = ''
    else:
        fee_quantity = Decimal(row_dict['fee']).quantize(PRECISION)
        fee_asset = quote_asset

    if row_dict['side'] == "buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['amount'],
                                                 buy_asset=base_asset,
                                                 sell_quantity=Decimal(row_dict['deal']). \
                                                         quantize(PRECISION),
                                                 sell_asset=quote_asset,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    elif row_dict['side'] == "sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(row_dict['deal']). \
                                                         quantize(PRECISION),
                                                 buy_asset=quote_asset,
                                                 sell_quantity=row_dict['amount'],
                                                 sell_asset=base_asset,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('side'), 'side', row_dict['side'])

def split_trading_pair(market):
    for quote_asset in QUOTE_ASSETS:
        if market.endswith(quote_asset):
            return market[:-len(quote_asset)], quote_asset

    return None, None

DataParser(DataParser.TYPE_EXCHANGE,
           "Hotbit Trades",
           ['Date', 'Pair', 'Side', 'Price', 'Volume', 'Fee', 'Total'],
           worksheet_name="Hotbit T",
           all_handler=parse_hotbit_orders_v3)

DataParser(DataParser.TYPE_EXCHANGE,
           "Hotbit Trades",
           ['Date', 'Pair', 'Side', 'Price', 'Amount', 'Fee', 'Total'],
           worksheet_name="Hotbit T",
           all_handler=parse_hotbit_orders_v2)

DataParser(DataParser.TYPE_EXCHANGE,
           "Hotbit Trades",
           ['Date', 'Pair', 'Type', 'Price', 'Amount', 'Fee', 'Total', 'Export'],
           worksheet_name="Hotbit T",
           all_handler=parse_hotbit_orders_v1)

DataParser(DataParser.TYPE_EXCHANGE,
           "Hotbit Trades",
           ['time', 'market', 'side', 'price', 'amount', 'deal', 'fee'],
           worksheet_name="Hotbit T",
           all_handler=parse_hotbit_trades)

# Format provided by request from support
DataParser(DataParser.TYPE_EXCHANGE,
           "Hotbit Trades",
           ['time', 'user_id', 'market', 'side', 'role', 'price', 'amount', 'deal', 'fee',
            'platform', 'stock', 'deal_stock'],
           worksheet_name="Hotbit T",
           all_handler=parse_hotbit_trades)
