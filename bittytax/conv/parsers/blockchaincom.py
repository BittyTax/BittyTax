# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Blockchain.com"


def parse_blockchaincom_history(data_row, parser, _filename):
    in_row = data_row.in_row
    header = parser.header
    value = in_row[header.index('amount')]
    timestamp = data_row.timestamp = DataParser.parse_timestamp('%s %s' % (in_row[header.index('date')],
                                                                           in_row[header.index('time')]))
    asset = in_row[header.index('token')]
    note = in_row[header.index('note')]

    t_type = TransactionOutRecord.TYPE_TRADE
    buy_quantity = sell_quantity = None
    buy_asset = sell_asset = ''

    if float(value) > 0:
        t_type = TransactionOutRecord.TYPE_DEPOSIT
        buy_asset = asset
        buy_quantity = Decimal(value)
        fee_quantity = 0
    else:
        t_type = TransactionOutRecord.TYPE_WITHDRAWAL
        sell_asset = asset
        sell_quantity = abs(Decimal(value))

    data_row.t_record = TransactionOutRecord(t_type, timestamp,
                                             buy_quantity, buy_asset, None,
                                             sell_quantity, sell_asset, None,
                                             None, '', None,
                                             WALLET, note)


DataParser(DataParser.TYPE_WALLET,
           "Blockchain.com",
           ['date', 'time', 'token', 'type', 'amount', 'value_then', 'value_now', 'exchange_rate_then', 'tx', 'note'],
           worksheet_name="Blockchain.com",
           row_handler=parse_blockchaincom_history)
