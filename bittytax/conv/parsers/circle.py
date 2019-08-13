# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Circle"

def parse_circle(in_row):
    if in_row[2] in ("deposit", "internal_switch_currency", "switch_currency"):
        return TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                    DataParser.parse_timestamp(in_row[0]),
                                    buy_quantity=in_row[7].strip('£').split(' ')[0],
                                    buy_asset=in_row[8],
                                    sell_quantity=in_row[5].strip('£').split(' ')[0],
                                    sell_asset=in_row[6],
                                    wallet=WALLET)
    elif in_row[2] == "spend":
        return TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                    DataParser.parse_timestamp(in_row[0]),
                                    sell_quantity=in_row[5].strip('£').split(' ')[0],
                                    sell_asset=in_row[6],
                                    sell_value=in_row[7].strip('£') if in_row[8] == config.CCY \
                                                                    else None,
                                    wallet=WALLET)
    elif in_row[2] == "receive":
        return TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                    DataParser.parse_timestamp(in_row[0]),
                                    buy_quantity=in_row[7].strip('£').split(' ')[0],
                                    buy_asset=in_row[8],
                                    buy_value=in_row[5].strip('£') if in_row[6] == config.CCY \
                                                                   else None,
                                    wallet=WALLET)
    else:
        raise ValueError("Unrecognised Transaction Type: " + in_row[2])

DataParser(DataParser.TYPE_EXCHANGE,
           "Circle",
           ['Date', ' Reference ID', ' Transaction Type', ' From Account', ' To Account',
            ' From Amount', ' From Currency', ' To Amount', ' To Currency', ' Status'],
           row_handler=parse_circle)
