# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownCryptoassetError

WALLET = "Electrum"

def parse_electrum2(data_row, _parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[3], tz='Europe/London')

    if not config.args.cryptoasset:
        raise UnknownCryptoassetError

    if Decimal(in_row[2]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[2]),
                                                 buy_asset=config.args.cryptoasset,
                                                 wallet=WALLET,
                                                 note=in_row[1])
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[2])),
                                                 sell_asset=config.args.cryptoasset,
                                                 wallet=WALLET,
                                                 note=in_row[1])

def parse_electrum(data_row, _parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[4], tz='Europe/London')

    if not config.args.cryptoasset:
        raise UnknownCryptoassetError

    if Decimal(in_row[3]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[3]),
                                                 buy_asset=config.args.cryptoasset,
                                                 wallet=WALLET,
                                                 note=in_row[1])
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=config.args.cryptoasset,
                                                 wallet=WALLET,
                                                 note=in_row[1])

DataParser(DataParser.TYPE_WALLET,
           "Electrum",
           ['transaction_hash', 'label', 'value', 'timestamp'],
           worksheet_name="Electrum",
           row_handler=parse_electrum2)

DataParser(DataParser.TYPE_WALLET,
           "Electrum",
           ['transaction_hash', 'label', 'confirmations', 'value', 'timestamp'],
           worksheet_name="Electrum",
           row_handler=parse_electrum)
