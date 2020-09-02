# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal

from colorama import Fore
import dateutil.tz

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataParserError, UnexpectedTypeError

WALLET = "OKEx"
TZ_INFOS = {'CST': dateutil.tz.gettz('Asia/Shanghai')}

def parse_okex_trades(data_rows, parser, _filename):
    for buy_row, sell_row in zip(data_rows[0::2], data_rows[1::2]):
        try:
            if config.args.debug:
                sys.stderr.write("%sconv: row[%s] %s\n" % (
                    Fore.YELLOW, parser.in_header_row_num + buy_row.line_num, buy_row))
                sys.stderr.write("%sconv: row[%s] %s\n" % (
                    Fore.YELLOW, parser.in_header_row_num + sell_row.line_num, sell_row))

            parse_okex_trades_row(buy_row, sell_row, parser)
        except DataParserError as e:
            buy_row.failure = e

def parse_okex_trades_row(buy_row, sell_row, parser):
    buy_row.timestamp = DataParser.parse_timestamp(buy_row.in_row[0], tzinfos=TZ_INFOS)
    sell_row.timestamp = DataParser.parse_timestamp(sell_row.in_row[0], tzinfos=TZ_INFOS)

    if buy_row.in_row[1] == "buy" and sell_row.in_row[1] == "sell":
        buy_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                buy_row.timestamp,
                                                buy_quantity=buy_row.in_row[2],
                                                buy_asset=buy_row.in_row[5],
                                                sell_quantity=abs(Decimal(sell_row.in_row[2])),
                                                sell_asset=sell_row.in_row[5],
                                                fee_quantity=abs(Decimal(buy_row.in_row[4])),
                                                fee_asset=buy_row.in_row[5],
                                                wallet=WALLET)
    else:
        raise UnexpectedTypeError(1, parser.in_header[1], buy_row.in_row[1])

DataParser(DataParser.TYPE_EXCHANGE,
           "OKEx",
           ['time', 'type', 'size', 'balance', 'fee', 'currency'],
           worksheet_name="OKEx",
           all_handler=parse_okex_trades)
