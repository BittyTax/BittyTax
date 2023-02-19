# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Coinomi"

def parse_coinomi(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Time(ISO8601-UTC)'])

    if Decimal(row_dict['Value']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Value'],
                                                 buy_asset=row_dict['Symbol'],
                                                 wallet=WALLET,
                                                 note=row_dict['AddressName'])
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(row_dict['Value'])) -
                                                 Decimal(row_dict['Fees']),
                                                 sell_asset=row_dict['Symbol'],
                                                 fee_quantity=row_dict['Fees'],
                                                 fee_asset=row_dict['Symbol'],
                                                 wallet=WALLET,
                                                 note=row_dict['AddressName'])

DataParser(DataParser.TYPE_WALLET,
           "Coinomi",
           ['Asset', 'AccountName', 'Address', 'AddressName', 'Value', 'Symbol', 'Fees',
            'InternalTransfer', 'TransactionID', 'Time(UTC)', 'Time(ISO8601-UTC)', 'BlockExplorer'],
           worksheet_name="Coinomi",
           row_handler=parse_coinomi)
