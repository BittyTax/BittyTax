# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Liquid"

PRECISION = Decimal('0.00000000')

def parse_liquid_trades(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date'])

    if row_dict['Type'] == "Bought":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Open Qty'],
                                                 buy_asset=row_dict['Base Currency'],
                                                 sell_quantity=Decimal(row_dict['Amount']).
                                                 quantize(PRECISION),
                                                 sell_asset=row_dict['Quote Currency'],
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=row_dict['Fee Currency'],
                                                 wallet=WALLET)
    elif row_dict['Type'] == "Sold":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(row_dict['Amount']).
                                                 quantize(PRECISION),
                                                 buy_asset=row_dict['Quote Currency'],
                                                 sell_quantity=row_dict['Open Qty'],
                                                 sell_asset=row_dict['Base Currency'],
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=row_dict['Fee Currency'],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

DataParser(DataParser.TYPE_EXCHANGE,
           "Liquid Trades",
           ['Quote Currency', 'Base Currency', 'Execution Id', 'Type', 'Date', 'Open Qty',
            'Price', 'Fee', 'Fee Currency', 'Amount'],
           worksheet_name="Liquid T",
           row_handler=parse_liquid_trades)
