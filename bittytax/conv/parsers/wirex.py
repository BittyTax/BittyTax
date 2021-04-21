# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Wirex"

def parse_wirex(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Time'])

    if row_dict[''] == "Create":
        return

    if row_dict[''] == "In":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'].split(' ')[0],
                                                 buy_asset=row_dict['Amount'].split(' ')[1],
                                                 wallet=WALLET)
    elif row_dict[''] == "Out":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Amount'].split(' ')[0],
                                                 sell_asset=row_dict['Amount'].split(' ')[1],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index(''), '', row_dict[''])

DataParser(DataParser.TYPE_EXCHANGE,
           "Wirex",
           ['#', '', 'Time', 'Amount', 'Available'],
           worksheet_name="Wirex",
           row_handler=parse_wirex)
