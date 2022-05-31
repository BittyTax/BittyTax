# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "qTrade"

def parse_qtrade_trades(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Creation Date'])

    if row_dict['Type'] == "buy_limit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Market Amount'],
                                                 buy_asset=row_dict['Market Currency'],
                                                 sell_quantity=row_dict['Base Amount'],
                                                 sell_asset=row_dict['Base Currency'],
                                                 fee_quantity=row_dict['Base Fee'],
                                                 fee_asset=row_dict['Base Currency'],
                                                 wallet=WALLET)
    elif row_dict['Type'] == "sell_limit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Base Amount'],
                                                 buy_asset=row_dict['Base Currency'],
                                                 sell_quantity=row_dict['Market Amount'],
                                                 sell_asset=row_dict['Market Currency'],
                                                 fee_quantity=row_dict['Base Fee'],
                                                 fee_asset=row_dict['Base Currency'],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

DataParser(DataParser.TYPE_EXCHANGE,
           "qTrade Trades",
           ['Order ID', 'Type', 'Market Currency', 'Base Currency', 'Trade ID', 'Market Amount',
            'Base Amount', 'Price', 'Taker', 'Base Fee', 'Creation Date'],
           worksheet_name="qTrade T",
           row_handler=parse_qtrade_trades)
