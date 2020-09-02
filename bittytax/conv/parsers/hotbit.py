# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import sys
import copy

from colorama import Fore

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataParserError, UnexpectedTypeError

WALLET = "Hotbit"

def parse_hotbit_trades(data_rows, parser, _filename):
    for row_index, data_row in enumerate(data_rows):
        if config.args.debug:
            sys.stderr.write("%sconv: row[%s] %s\n" % (
                Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))

        if data_row.parsed:
            continue

        try:
            parse_hotbit_trades_row(data_rows, parser, data_row, row_index)
        except DataParserError as e:
            data_row.failure = e

def parse_hotbit_trades_row(data_rows, parser, data_row, row_index):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])
    data_row.parsed = True

    # Maker fees are a credit (+), add as gift-received
    if in_row[5][0] == '+':
        dup_data_row = copy.copy(data_row)
        dup_data_row.in_row = []
        dup_data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[5].split(' ')[0],
                                                     buy_asset=in_row[5].split(' ')[1],
                                                     wallet=WALLET)
        data_rows.insert(row_index + 1, dup_data_row)

        fee_quantity = None
        fee_asset = ""
    else:
        fee_quantity = in_row[5].split(' ')[0]
        fee_asset = in_row[5].split(' ')[1]

    if in_row[2] == "BUY":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4].split(' ')[0],
                                                 buy_asset=in_row[1].split('/')[0],
                                                 sell_quantity=in_row[6].split(' ')[0],
                                                 sell_asset=in_row[1].split('/')[1],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    elif in_row[2] == "SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[6].split(' ')[0],
                                                 buy_asset=in_row[1].split('/')[1],
                                                 sell_quantity=in_row[4].split(' ')[0],
                                                 sell_asset=in_row[1].split('/')[0],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

DataParser(DataParser.TYPE_EXCHANGE,
           "Hotbit Trades",
           ['Date', 'Pair', 'Type', 'Price', 'Amount', 'Fee', 'Total', 'Export'],
           worksheet_name="Hotbit T",
           all_handler=parse_hotbit_trades)
