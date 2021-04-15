# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownCryptoassetError

WALLET = "Electrum"

def parse_electrum2(data_row, _parser, _filename, args):
    parse_electrum(data_row, _parser, _filename, args)

def parse_electrum(data_row, _parser, _filename, args):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['timestamp'], tz='Europe/London')

    if not args.cryptoasset:
        raise UnknownCryptoassetError

    if Decimal(row_dict['value']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(row_dict['value']),
                                                 buy_asset=args.cryptoasset,
                                                 wallet=WALLET,
                                                 note=row_dict['label'])
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(row_dict['value'])),
                                                 sell_asset=args.cryptoasset,
                                                 wallet=WALLET,
                                                 note=row_dict['label'])

DataParser(DataParser.TYPE_WALLET,
           "Electrum",
           ['transaction_hash', 'label', 'value', 'timestamp'],
           worksheet_name="Electrum",
           # Different handler name used to prevent data file consolidation
           row_handler=parse_electrum2)

DataParser(DataParser.TYPE_WALLET,
           "Electrum",
           ['transaction_hash', 'label', 'confirmations', 'value', 'timestamp'],
           worksheet_name="Electrum",
           row_handler=parse_electrum)
