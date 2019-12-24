# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Wirex"

def parse_wirex(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[2])

    if in_row[1] == "Create":
        return
    elif in_row[1] == "In":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3].split(' ')[0],
                                                 buy_asset=in_row[3].split(' ')[1],
                                                 wallet=WALLET)
    elif in_row[1] == "Out":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[3].split(' ')[0],
                                                 sell_asset=in_row[3].split(' ')[1],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(1, parser.in_header[1], in_row[1])

DataParser(DataParser.TYPE_EXCHANGE,
           "Wirex",
           ['# ', None, 'Time ', 'Amount', 'Available'],
           worksheet_name="Wirex",
           row_handler=parse_wirex)
