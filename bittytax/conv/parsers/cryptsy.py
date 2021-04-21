# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Cryptsy"

def parse_cryptsy(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Timestamp'], tz='US/Eastern')

    if row_dict['OrderType'] == "Buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Quantity'],
                                                 buy_asset=row_dict['Market'].split('/')[0],
                                                 sell_quantity=row_dict['Total'],
                                                 sell_asset=row_dict['Market'].split('/')[1],
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=row_dict['Market'].split('/')[1],
                                                 wallet=WALLET)
    elif row_dict['OrderType'] == "Sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Total'],
                                                 buy_asset=row_dict['Market'].split('/')[1],
                                                 sell_quantity=row_dict['Quantity'],
                                                 sell_asset=row_dict['Market'].split('/')[0],
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=row_dict['Market'].split('/')[1],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('OrderType'), 'OrderType',
                                  row_dict['OrderType'])

DataParser(DataParser.TYPE_EXCHANGE,
           "Cryptsy",
           ['TradeID', 'OrderType', 'Market', 'Price', 'Quantity', 'Total', 'Fee', 'Net',
            'Timestamp'],
           worksheet_name="Cryptsy",
           row_handler=parse_cryptsy)
