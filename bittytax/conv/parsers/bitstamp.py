# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Bitstamp"

def parse_bitstamp(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[1])

    if in_row[0] in ("Ripple deposit", "Deposit"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3].split(' ')[0],
                                                 buy_asset=in_row[3].split(' ')[1],
                                                 wallet=WALLET)
    elif in_row[0] in ("Ripple payment", "Withdrawal"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[3].split(' ')[0],
                                                 sell_asset=in_row[3].split(' ')[1],
                                                 wallet=WALLET)
    elif in_row[0] == "Market":
        if in_row[7] == "Buy":
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[3].split(' ')[0],
                                                     buy_asset=in_row[3].split(' ')[1],
                                                     sell_quantity=in_row[4].split(' ')[0],
                                                     sell_asset=in_row[4].split(' ')[1],
                                                     fee_quantity=in_row[6].split(' ')[0],
                                                     fee_asset=in_row[6].split(' ')[1],
                                                     wallet=WALLET)
        elif in_row[7] == "Sell":
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[4].split(' ')[0],
                                                     buy_asset=in_row[4].split(' ')[1],
                                                     sell_quantity=in_row[3].split(' ')[0],
                                                     sell_asset=in_row[3].split(' ')[1],
                                                     fee_quantity=in_row[6].split(' ')[0],
                                                     fee_asset=in_row[6].split(' ')[1],
                                                     wallet=WALLET)
        else:
            raise UnexpectedTypeError(7, parser.in_header[7], in_row[7])
    else:
        raise UnexpectedTypeError(0, parser.in_header[0], in_row[0])

DataParser(DataParser.TYPE_EXCHANGE,
           "Bitstamp",
           ['Type', 'Datetime', 'Account', 'Amount', 'Value', 'Rate', 'Fee', 'Sub Type'],
           worksheet_name="Bitstamp",
           row_handler=parse_bitstamp)
