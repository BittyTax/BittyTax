# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

def parse_barclays(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[1])

    if in_row[2] != "Completed":
        return

    if in_row[4] == "Buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=in_row[0],
                                                 sell_quantity=in_row[6],
                                                 sell_asset=config.CCY,
                                                 wallet=in_row[3])
    elif in_row[4] == "Sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[6],
                                                 buy_asset=config.CCY,
                                                 sell_quantity=in_row[5],
                                                 sell_asset=in_row[0],
                                                 wallet=in_row[3])
    else:
        raise UnexpectedTypeError(4, parser.in_header[4], in_row[4])

DataParser(DataParser.TYPE_SHARES,
           "Barclays Smart Investor",
           ['Investment', 'Date', 'Order Status', 'Account', 'Buy/Sell', 'Quantity',
            'Cost/Proceeds'],
           worksheet_name="Barclays",
           row_handler=parse_barclays)
