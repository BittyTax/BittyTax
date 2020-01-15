# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Crypsty"

def parse_cryptsy(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[8], tz='US/Eastern')

    if in_row[1] == "Buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=in_row[2].split('/')[0],
                                                 sell_quantity=in_row[7],
                                                 sell_asset=in_row[2].split('/')[1],
                                                 fee_quantity=in_row[6],
                                                 fee_asset=in_row[2].split('/')[1],
                                                 wallet=WALLET)
    elif in_row[1] == "Sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[7],
                                                 buy_asset=in_row[2].split('/')[1],
                                                 sell_quantity=in_row[4],
                                                 sell_asset=in_row[2].split('/')[0],
                                                 fee_quantity=in_row[6],
                                                 fee_asset=in_row[2].split('/')[1],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(1, parser.in_header[1], in_row[1])

DataParser(DataParser.TYPE_EXCHANGE,
           "Cryptsy",
           ['TradeID', 'OrderType', 'Market', 'Price', 'Quantity', 'Total', 'Fee', 'Net',
            'Timestamp'],
           worksheet_name="Cryptsy",
           row_handler=parse_cryptsy)
