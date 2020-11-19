# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import sys
import copy

from decimal import Decimal, ROUND_DOWN

from colorama import Fore

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataParserError, UnexpectedTypeError

WALLET = "Hotbit"

PRECISION = Decimal('0.00000000')
MAKER_FEE = Decimal(0.0005)
TAKER_FEE = Decimal(0.002)

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

    # Have to -re-caclulate the total as it's incorrect for USDT trades
    total = Decimal(in_row[3].split(' ')[0]) * Decimal(in_row[4].split(' ')[0])

    # Maker fees are a credit (+), add as gift-received
    if in_row[5][0] == '+':
        # Have to re-calculate the fee as rounding in datafile is incorrect
        dup_data_row = copy.copy(data_row)
        dup_data_row.in_row = []
        dup_data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=(total * MAKER_FEE). \
                                                         quantize(PRECISION, rounding=ROUND_DOWN),
                                                     buy_asset=in_row[5].split(' ')[1],
                                                     wallet=WALLET)
        data_rows.insert(row_index + 1, dup_data_row)

        fee_quantity = Decimal(0)
    else:
        # Have to re-calculate the fee as rounding in datafile is incorrect
        fee_quantity = (total * TAKER_FEE).quantize(PRECISION, rounding=ROUND_DOWN)

    fee_asset = in_row[5].split(' ')[1]

    if in_row[2] == "BUY":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4].split(' ')[0],
                                                 buy_asset=in_row[1].split('/')[0],
                                                 sell_quantity=total.quantize(PRECISION),
                                                 sell_asset=in_row[1].split('/')[1],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    elif in_row[2] == "SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=total.quantize(PRECISION),
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
