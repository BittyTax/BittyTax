# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import json
from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "HandCash"

def parse_handcash(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    if row_dict.get('updatedAt'):
        data_row.timestamp = DataParser.parse_timestamp(row_dict['updatedAt'])
    else:
        data_row.timestamp = DataParser.parse_timestamp(row_dict['createdAt'])

    participants = json.loads(row_dict['participants'])
    if row_dict['type'] == "receive":
        if participants[0]["type"] == "user":
            t_type = TransactionOutRecord.TYPE_GIFT_RECEIVED
        else:
            t_type = TransactionOutRecord.TYPE_DEPOSIT

        data_row.t_record = TransactionOutRecord(t_type,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(row_dict['satoshiAmount']) \
                                                     / 10 ** 8,
                                                 buy_asset="BSV",
                                                 wallet=WALLET,
                                                 note=row_dict['note'])
    elif row_dict['type'] == "send":
        if participants[0]["type"] == "user":
            t_type = TransactionOutRecord.TYPE_GIFT_SENT
        else:
            t_type = TransactionOutRecord.TYPE_WITHDRAWAL

        data_row.t_record = TransactionOutRecord(t_type,
                                                 data_row.timestamp,
                                                 sell_quantity=Decimal(row_dict['satoshiAmount']) \
                                                     / 10 ** 8,
                                                 sell_asset="BSV",
                                                 fee_quantity=Decimal(row_dict['satoshiFees']) \
                                                     / 10 ** 8,
                                                 fee_asset="BSV",
                                                 wallet=WALLET,
                                                 note=row_dict['note'])
    else:
        raise UnexpectedTypeError(parser.in_header.index('type'), 'type', row_dict['type'])

DataParser(DataParser.TYPE_WALLET,
           "HandCash",
           ['type', 'addresses', 'transactionId', 'note', 'satoshiFees', 'satoshiAmount',
            'fiatExchangeRate', 'fiatCurrencyCode', 'participants', 'createdAt'],
           worksheet_name="HandCash",
           row_handler=parse_handcash)

DataParser(DataParser.TYPE_WALLET,
           "HandCash",
           ['type', 'addresses', 'transactionId', 'note', 'satoshiFees', 'satoshiAmount',
            'fiatExchangeRate', 'fiatCurrencyCode', 'participants', 'updatedAt', 'createdAt'],
           worksheet_name="HandCash",
           row_handler=parse_handcash)
