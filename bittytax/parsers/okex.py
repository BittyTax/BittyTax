# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019
# $Id: okex.py,v 1.7 2019/05/16 20:26:52 scottgreen Exp $

import copy
from decimal import Decimal

import dateutil.tz

from ..config import config
from ..record import TransactionRecord
from ..parser import DataParser

TZ_INFOS = {'CST': dateutil.tz.gettz('Asia/Shanghai')}

def parse_okex_trades(all_in_row):
    all_out_row = copy.deepcopy(all_in_row)
    i = 0

    while i < len(all_in_row):
        in_row = all_in_row[i]

        if in_row[1] == "buy":
            buy_quantity = in_row[2]
            buy_asset = in_row[5]
            fee_quantity = abs(Decimal(in_row[4]))
            fee_asset = in_row[5]
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
                                         wallet="OKEx")

            all_out_row[i].extend(t_record.to_csv())
        else:
            raise ValueError("Unrecognised type: " + in_row[1])

        i += 1

    if not config.args.append:
        for i, _ in enumerate(all_in_row):
            del all_out_row[i][0:len(all_in_row[i])]

        all_out_row = filter(None, all_out_row)

    return all_out_row

DataParser(DataParser.TYPE_EXCHANGE,
           "OKEx",
           ['time', 'type', 'size', 'balance', 'fee', 'currency'],
           all_handler=parse_okex_trades)
