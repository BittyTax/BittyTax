# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

import dateutil.tz

from ...record import TransactionRecord
from ..dataparser import DataParser

WALLET = "OKEx"
TZ_INFOS = {'CST': dateutil.tz.gettz('Asia/Shanghai')}

def parse_okex_trades(all_in_row):
    t_records = []

    for in_row in all_in_row:
        if in_row[1] == "buy":
            buy_quantity = in_row[2]
            buy_asset = in_row[5]
            fee_quantity = abs(Decimal(in_row[4]))
            fee_asset = in_row[5]

            t_records.append(None)
        elif in_row[1] == "sell":
            sell_quantity = abs(Decimal(in_row[2]))
            sell_asset = in_row[5]

            t_record = TransactionRecord(TransactionRecord.TYPE_TRADE,
                                         DataParser.parse_timestamp(in_row[0],
                                                                    tzinfos=TZ_INFOS),
                                         buy_quantity=buy_quantity,
                                         buy_asset=buy_asset,
                                         sell_quantity=sell_quantity,
                                         sell_asset=sell_asset,
                                         fee_quantity=fee_quantity,
                                         fee_asset=fee_asset,
                                         wallet=WALLET)
            t_records.append(t_record)
        else:
            raise ValueError("Unrecognised type: " + in_row[1])

    return t_records

DataParser(DataParser.TYPE_EXCHANGE,
           "OKEx",
           ['time', 'type', 'size', 'balance', 'fee', 'currency'],
           all_handler=parse_okex_trades)
