# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Uphold"

def parse_uphold2(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[11] == "in":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[8],
                                                 buy_asset=in_row[9],
                                                 fee_quantity=in_row[4] if in_row[4] else None,
                                                 fee_asset=in_row[5],
                                                 wallet=WALLET)
    elif in_row[11] == "out":
        if in_row[9] == in_row[3]:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                     data_row.timestamp,
                                                     sell_quantity=in_row[2],
                                                     sell_asset=in_row[9],
                                                     fee_quantity=in_row[4] if in_row[4] else None,
                                                     fee_asset=in_row[5],
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                     data_row.timestamp,
                                                     sell_quantity=in_row[8],
                                                     sell_asset=in_row[9],
                                                     wallet=WALLET)
    elif in_row[11] == "transfer":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[2],
                                                 buy_asset=in_row[3],
                                                 sell_quantity=in_row[8],
                                                 sell_asset=in_row[9],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(11, parser.in_header[11], in_row[11])

def parse_uphold(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[2] == "deposit" or in_row[2] == "in":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[8],
                                                 buy_asset=in_row[7],
                                                 fee_quantity=Decimal(in_row[8]) - \
                                                              Decimal(in_row[11]),
                                                 fee_asset=in_row[7],
                                                 wallet=WALLET)
    elif in_row[2] == "withdrawal" or in_row[2] == "out":
        # Check if origin and destination currency are the same
        if in_row[7] == in_row[10]:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                     data_row.timestamp,
                                                     sell_quantity=in_row[11],
                                                     sell_asset=in_row[7],
                                                     fee_quantity=Decimal(in_row[8]) - \
                                                                  Decimal(in_row[11]),
                                                     fee_asset=in_row[7],
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                     data_row.timestamp,
                                                     sell_quantity=in_row[8],
                                                     sell_asset=in_row[7],
                                                     wallet=WALLET)
    elif in_row[2] == "transfer":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[11],
                                                 buy_asset=in_row[10],
                                                 sell_quantity=in_row[8],
                                                 sell_asset=in_row[7],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

DataParser(DataParser.TYPE_EXCHANGE,
           "Uphold",
           ['Date', 'Destination', 'Destination Amount', 'Destination Currency', 'Fee Amount',
            'Fee Currency', 'Id', 'Origin', 'Origin Amount', 'Origin Currency', 'Status', 'Type'],
           worksheet_name="Uphold",
           row_handler=parse_uphold2)

DataParser(DataParser.TYPE_EXCHANGE,
           "Uphold",
           ['date', 'id', 'type', 'value_in_GBP', 'commission_in_GBP', 'pair', 'rate',
            'origin_currency', 'origin_amount', 'origin_commission', 'destination_currency',
            'destination_amount', 'destination_commission'],
           worksheet_name="Uphold",
           row_handler=parse_uphold)
