# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import sys
import copy

from decimal import Decimal

from colorama import Fore

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataParserError, UnexpectedTypeError

WALLET = "HitBTC"

def parse_hitbtc_trades2(data_rows, parser, _filename):
    for row_index, data_row in enumerate(data_rows):
        if config.args.debug:
            sys.stderr.write("%sconv: row[%s] %s\n" % (
                Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))

        if data_row.parsed:
            continue

        try:
            parse_hitbtc_trades_row(data_rows, parser, data_row, row_index)
        except DataParserError as e:
            data_row.failure = e

def parse_hitbtc_trades_row(data_rows, parser, data_row, row_index):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[1])
    data_row.parsed = True


    # Negative fees are rebates, add as gift-received
    if Decimal(in_row[9]) < 0:
        dup_data_row = copy.copy(data_row)
        dup_data_row.in_row = []
        dup_data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=abs(Decimal(in_row[9])),
                                                     buy_asset=in_row[2].split('/')[1],
                                                     wallet=WALLET)
        data_rows.insert(row_index + 1, dup_data_row)

        fee_quantity = Decimal(0)
    else:
        fee_quantity = in_row[9]

    fee_asset = in_row[2].split('/')[1]

    if in_row[5] == "buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[6],
                                                 buy_asset=in_row[2].split('/')[0],
                                                 sell_quantity=Decimal(in_row[6]) * \
                                                               Decimal(in_row[7]),
                                                 sell_asset=in_row[2].split('/')[1],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    elif in_row[5] == "sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[6]) * \
                                                              Decimal(in_row[7]),
                                                 buy_asset=in_row[2].split('/')[1],
                                                 sell_quantity=in_row[6],
                                                 sell_asset=in_row[2].split('/')[0],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(5, parser.in_header[5], in_row[5])

def parse_hitbtc_trades(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[4] == "buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=in_row[1].split('/')[0],
                                                 sell_quantity=Decimal(in_row[7]) - \
                                                               Decimal(in_row[9]),
                                                 sell_asset=in_row[1].split('/')[1],
                                                 fee_quantity=in_row[8],
                                                 fee_asset=in_row[1].split('/')[1],
                                                 wallet=WALLET)
    elif in_row[4] == "sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[7]) + \
                                                              Decimal(in_row[9]),
                                                 buy_asset=in_row[1].split('/')[1],
                                                 sell_quantity=in_row[5],
                                                 sell_asset=in_row[1].split('/')[0],
                                                 fee_quantity=in_row[8],
                                                 fee_asset=in_row[1].split('/')[1],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(4, parser.in_header[4], in_row[4])


def parse_hitbtc_deposits_withdrawals2(data_row, _parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[1])

    if in_row[3] == "Withdraw":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[4])),
                                                 sell_asset=in_row[7].upper(),
                                                 wallet=WALLET)
    elif in_row[3] == "Deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=in_row[7].upper(),
                                                 wallet=WALLET)

def parse_hitbtc_deposits_withdrawals(data_row, _parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[2] == "Withdraw":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[6],
                                                 wallet=WALLET)
    elif in_row[2] == "Deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[6],
                                                 wallet=WALLET)

DataParser(DataParser.TYPE_EXCHANGE,
           "HitBTC",
           ['Email', 'Date (UTC)', 'Instrument', 'Trade ID', 'Order ID', 'Side', 'Quantity',
            'Price', 'Volume', 'Fee', 'Rebate', 'Total'],
           worksheet_name="HitBTC T",
           all_handler=parse_hitbtc_trades2)

DataParser(DataParser.TYPE_EXCHANGE,
           "HitBTC",
           ['Date (UTC)', 'Instrument', 'Trade ID', 'Order ID', 'Side', 'Quantity', 'Price',
            'Volume', 'Fee', 'Rebate', 'Total'],
           worksheet_name="HitBTC T",
           row_handler=parse_hitbtc_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "HitBTC",
           ['Email', 'Date (UTC)', 'Operation id', 'Type', 'Amount', 'Transaction hash',
            'Main account balance', 'Currency'],
           worksheet_name="HitBTC D,W",
           row_handler=parse_hitbtc_deposits_withdrawals2)

DataParser(DataParser.TYPE_EXCHANGE,
           "HitBTC",
           ['Date (UTC)', 'Operation id', 'Type', 'Amount', 'Transaction Hash',
            'Main account balance'],
           worksheet_name="HitBTC D,W",
           row_handler=parse_hitbtc_deposits_withdrawals)
