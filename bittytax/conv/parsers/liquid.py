# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Liquid"

PRECISION = Decimal('0.00000000')

def parse_liquid_trades(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[4])

    if in_row[3] == "Bought":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=in_row[1],
                                                 sell_quantity=Decimal(in_row[9]). \
                                                               quantize(PRECISION),
                                                 sell_asset=in_row[0],
                                                 fee_quantity=in_row[7],
                                                 fee_asset=in_row[8],
                                                 wallet=WALLET)
    elif in_row[3] == "Sold":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[9]). \
                                                              quantize(PRECISION),
                                                 buy_asset=in_row[0],
                                                 sell_quantity=in_row[5],
                                                 sell_asset=in_row[1],
                                                 fee_quantity=in_row[7],
                                                 fee_asset=in_row[8],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(3, parser.in_header[3], in_row[3])

DataParser(DataParser.TYPE_EXCHANGE,
           "Liquid Trades",
           ['Quote Currency', 'Base Currency', 'Execution Id', 'Type', 'Date', 'Open Qty',
            'Price', 'Fee', 'Fee Currency', 'Amount'],
           worksheet_name="Liquid T",
           row_handler=parse_liquid_trades)
