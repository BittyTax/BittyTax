# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import json
from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "HandCash"

def parse_handcash(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[9])

    participants = json.loads(in_row[8])
    if in_row[0] == "receive":
        if participants[0]["type"] == "user":
            t_type = TransactionOutRecord.TYPE_GIFT_RECEIVED
        else:
            t_type = TransactionOutRecord.TYPE_DEPOSIT

        data_row.t_record = TransactionOutRecord(t_type,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[5]) / 10 ** 8,
                                                 buy_asset="BSV",
                                                 wallet=WALLET,
                                                 note=in_row[3])
    elif in_row[0] == "send":
        if participants[0]["type"] == "user":
            t_type = TransactionOutRecord.TYPE_GIFT_SENT
        else:
            t_type = TransactionOutRecord.TYPE_WITHDRAWAL

        data_row.t_record = TransactionOutRecord(t_type,
                                                 data_row.timestamp,
                                                 sell_quantity=Decimal(in_row[5]) / 10 ** 8,
                                                 sell_asset="BSV",
                                                 fee_quantity=Decimal(in_row[4]) / 10 ** 8,
                                                 fee_asset="BSV",
                                                 wallet=WALLET,
                                                 note=in_row[3])
    else:
        raise UnexpectedTypeError(0, parser.in_header[0], in_row[0])

DataParser(DataParser.TYPE_WALLET,
           "HandCash",
           ['type', 'addresses', 'transactionId', 'note', 'satoshiFees', 'satoshiAmount',
            'fiatExchangeRate', 'fiatCurrencyCode', 'participants', 'createdAt'],
           worksheet_name="HandCash",
           row_handler=parse_handcash)
