# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ...config import config
from ...record import TransactionRecordBase as TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownCryptoassetError, UnexpectedTypeError

WALLET = "Trezor"

def parse_trezor(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0] + 'T' + in_row[1])

    if not config.args.cryptoasset:
        raise UnknownCryptoassetError

    if in_row[5] == "IN":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[7],
                                                 buy_asset=config.args.cryptoasset,
                                                 wallet=WALLET)
    elif in_row[5] == "OUT" or in_row[5] == "SELF":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[7])),
                                                 sell_asset=config.args.cryptoasset,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(5, parser.in_header[5], in_row[5])

DataParser(DataParser.TYPE_WALLET,
           "Trezor",
           ['Date', 'Time', 'TX id', 'Address', 'Address Label', 'TX type', 'Value', 'TX total',
            'Balance'],
           worksheet_name="Trezor",
           row_handler=parse_trezor)
