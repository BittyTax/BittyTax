# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

import dateutil.tz

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataParserError, UnexpectedTypeError

WALLET = "OKEx"
TZ_INFOS = {'CST': dateutil.tz.gettz('Asia/Shanghai')}

def parse_okex_trades(data_rows, parser):
    for buy_row, sell_row in zip(data_rows[0::2], data_rows[1::2]):
        try:
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
