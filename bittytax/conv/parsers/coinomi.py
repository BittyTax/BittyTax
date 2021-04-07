# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Coinomi"

def parse_coinomi_history(data_row, parser, _filename):
    in_row = data_row.in_row
    header = parser.header
    value = in_row[header.index('Value')]
    timestamp = data_row.timestamp = DataParser.parse_timestamp(in_row[header.index('Time(ISO8601-UTC)')])
    asset = in_row[header.index('Symbol')]
    address = in_row[header.index('Address')]
    label = in_row[header.index('AddressName')]

    if not address:
        return

    t_type = TransactionOutRecord.TYPE_TRADE
    buy_quantity = sell_quantity = None
    buy_asset = sell_asset = ''
    fee_quantity = in_row[header.index('Fees')]
    fee_asset = asset

    if float(value) > 0:
        t_type = TransactionOutRecord.TYPE_DEPOSIT
        buy_asset = asset
        buy_quantity = Decimal(value)
        fee_quantity = 0
    elif float(value) < 0:
        t_type = TransactionOutRecord.TYPE_WITHDRAWAL
        sell_asset = asset
        sell_quantity = abs(Decimal(value)) - Decimal(fee_quantity if fee_quantity else 0)
    else:
        t_type = TransactionOutRecord.TYPE_SPEND
        sell_asset = fee_asset = asset

    data_row.t_record = TransactionOutRecord(t_type, timestamp,
                                             buy_quantity, buy_asset, None,
                                             sell_quantity, sell_asset, None,
                                             fee_quantity, fee_asset, None,
                                             WALLET, label)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinomi",
           ['Asset', 'AccountName', 'Address', 'AddressName', 'Value', 'Symbol', 'Fees', 'InternalTransfer',
            'TransactionID', 'Time(UTC)', 'Time(ISO8601-UTC)', 'BlockExplorer'],
           worksheet_name="Coinomi",
           row_handler=parse_coinomi_history)

# Yes, seriously
DataParser(DataParser.TYPE_EXCHANGE,
           "Coinomi",
           ['Asset', ' AccountName', 'Address', 'AddressName', 'Value', 'Symbol', 'Fees', 'InternalTransfer',
            'TransactionID', 'Time(UTC)', 'Time(ISO8601-UTC)', 'BlockExplorer'],
           worksheet_name="Coinomi",
           row_handler=parse_coinomi_history)
