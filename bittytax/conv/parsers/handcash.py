# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "HandCash"

def parse_handcash(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[9])

    if in_row[0] == "receive":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[5]) / 100000000,
                                                 buy_asset="BSV",
                                                 wallet=WALLET)
    elif in_row[0] == "send":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=Decimal(in_row[5]) / 100000000,
                                                 sell_asset="BSV",
                                                 fee_quantity=Decimal(in_row[4]) / 100000000,
                                                 fee_asset="BSV",
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(0, parser.in_header[0], in_row[0])

DataParser(DataParser.TYPE_WALLET,
           "HandCash",
           ['type', 'addresses', 'transactionId', 'note', 'satoshiFees', 'satoshiAmount',
            'fiatExchangeRate', 'fiatCurrencyCode', 'participants', 'createdAt'],
           worksheet_name="HandCash",
           row_handler=parse_handcash)
