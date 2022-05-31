# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownCryptoassetError

WALLET = "Electrum"

def parse_electrum_v3(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['timestamp'], tz='Europe/London')

    if not kwargs['cryptoasset']:
        raise UnknownCryptoassetError(kwargs['filename'], kwargs.get('worksheet'))

    if Decimal(row_dict['value']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['value'],
                                                 buy_asset=kwargs['cryptoasset'],
                                                 wallet=WALLET,
                                                 note=row_dict['label'])
    else:
        if row_dict['fee']:
            sell_quantity = abs(Decimal(row_dict['value'])) - Decimal(row_dict['fee'])
            fee_quantity = row_dict['fee']
            fee_asset = kwargs['cryptoasset']
        else:
            sell_quantity = abs(Decimal(row_dict['value']))
            fee_quantity = None
            fee_asset = ''

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=sell_quantity,
                                                 sell_asset=kwargs['cryptoasset'],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET,
                                                 note=row_dict['label'])

def parse_electrum_v2(data_row, _parser, **kwargs):
    parse_electrum_v1(data_row, _parser, **kwargs)

def parse_electrum_v1(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['timestamp'], tz='Europe/London')

    if not kwargs['cryptoasset']:
        raise UnknownCryptoassetError(kwargs['filename'], kwargs.get('worksheet'))

    if Decimal(row_dict['value']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['value'],
                                                 buy_asset=kwargs['cryptoasset'],
                                                 wallet=WALLET,
                                                 note=row_dict['label'])
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(row_dict['value'])),
                                                 sell_asset=kwargs['cryptoasset'],
                                                 wallet=WALLET,
                                                 note=row_dict['label'])

DataParser(DataParser.TYPE_WALLET,
           "Electrum",
           ['transaction_hash', 'label', 'confirmations', 'value', 'fiat_value', 'fee', 'fiat_fee',
            'timestamp'],
           worksheet_name="Electrum",
           row_handler=parse_electrum_v3)

DataParser(DataParser.TYPE_WALLET,
           "Electrum",
           ['transaction_hash', 'label', 'value', 'timestamp'],
           worksheet_name="Electrum",
           # Different handler name used to prevent data file consolidation
           row_handler=parse_electrum_v2)

DataParser(DataParser.TYPE_WALLET,
           "Electrum",
           ['transaction_hash', 'label', 'confirmations', 'value', 'timestamp'],
           worksheet_name="Electrum",
           row_handler=parse_electrum_v1)
