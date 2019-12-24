# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownUsernameError

WALLET = "ChangeTip"

def parse_changetip(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[3])

    if in_row[6] == "Delivered":
        if in_row[2] in config.usernames:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=Decimal(in_row[4]) / 100000000,
                                                     buy_asset="BTC",
                                                     wallet=WALLET)
        elif in_row[1] in config.usernames:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_SENT,
                                                     data_row.timestamp,
                                                     sell_quantity=Decimal(in_row[4]) / 100000000,
                                                     sell_asset="BTC",
                                                     wallet=WALLET)
        else:
            raise UnknownUsernameError
    else:
        return

DataParser(DataParser.TYPE_EXCHANGE,
           "ChangeTip",
           ['On', 'From', 'To', 'When', 'Amount in Satoshi', 'mBTC', 'Status', 'Message'],
           worksheet_name="ChangeTip",
           row_handler=parse_changetip)
