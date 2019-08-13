# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "ChangeTip"

def parse_changetip(in_row):
    if in_row[6] == "Delivered":
        if in_row[2] in config.usernames:
            return TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                        DataParser.parse_timestamp(in_row[3]),
                                        buy_quantity=Decimal(in_row[4]) / 100000000,
                                        buy_asset="BTC",
                                        wallet=WALLET)
        elif in_row[1] in config.usernames:
            return TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_SENT,
                                        DataParser.parse_timestamp(in_row[3]),
                                        sell_quantity=Decimal(in_row[4]) / 100000000,
                                        sell_asset="BTC",
                                        wallet=WALLET)
        else:
            raise ValueError("Unrecognised username: " + in_row[2])
    else:
        return None

DataParser(DataParser.TYPE_EXCHANGE,
           "ChangeTip",
           ['On', 'From', 'To', 'When', 'Amount in Satoshi', 'mBTC', 'Status', 'Message'],
           row_handler=parse_changetip)
