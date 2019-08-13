# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Trezor"

def parse_trezor(in_row):
    if not config.args.cryptoasset:
        raise Exception(config.ERROR_TXT[0])

    if in_row[5] == "IN":
        return TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                    DataParser.parse_timestamp(in_row[0] + 'T' + in_row[1]),
                                    buy_quantity=in_row[7],
                                    buy_asset=config.args.cryptoasset,
                                    wallet=WALLET)
    elif in_row[5] == "OUT" or in_row[5] == "SELF":
        return TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                    DataParser.parse_timestamp(in_row[0] + 'T' + in_row[1]),
                                    sell_quantity=abs(Decimal(in_row[7])),
                                    sell_asset=config.args.cryptoasset,
                                    wallet=WALLET)
    else:
        raise ValueError("Unrecognised TX type: " + in_row[5])

DataParser(DataParser.TYPE_WALLET,
           "Trezor",
           ['Date', 'Time', 'TX id', 'Address', 'Address Label', 'TX type', 'Value', 'TX total',
            'Balance'],
           row_handler=parse_trezor)
