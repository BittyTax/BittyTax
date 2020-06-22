# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Circle"

def parse_circle(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[2] in ("deposit", "internal_switch_currency", "switch_currency"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[7].strip('£').split(' ')[0],
                                                 buy_asset=in_row[8],
                                                 sell_quantity=in_row[5].strip('£').split(' ')[0],
                                                 sell_asset=in_row[6],
                                                 wallet=WALLET)
    elif in_row[2] == "spend":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[5].strip('£').split(' ')[0],
                                                 sell_asset=in_row[6],
                                                 sell_value=in_row[7].strip('£') if in_row[8] == \
                                                                                     config.CCY \
                                                                                 else None,
                                                 wallet=WALLET)
    elif in_row[2] == "receive":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[7].strip('£').split(' ')[0],
                                                 buy_asset=in_row[8],
                                                 buy_value=in_row[5].strip('£') if in_row[6] == \
                                                                                    config.CCY \
                                                                                else None,
                                                 wallet=WALLET)
    elif in_row[2] == "fork":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[7].strip('£').split(' ')[0],
                                                 buy_asset=in_row[8],
                                                 buy_value=0,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

DataParser(DataParser.TYPE_EXCHANGE,
           "Circle",
           ['Date', ' Reference ID', ' Transaction Type', ' From Account', ' To Account',
            ' From Amount', ' From Currency', ' To Amount', ' To Currency', ' Status'],
           worksheet_name="Circle",
           row_handler=parse_circle)
