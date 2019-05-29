# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..config import config
from ..record import TransactionRecord
from ..parser import DataParser

WALLET = "Electrum"

def parse_electrum(in_row):
    if not config.args.cryptoasset:
        raise Exception(config.ERROR_TXT[0])

    if Decimal(in_row[3]) > 0:
        return TransactionRecord(TransactionRecord.TYPE_DEPOSIT,
                                 DataParser.parse_timestamp(in_row[4]),
                                 buy_quantity=Decimal(in_row[3]),
                                 buy_asset=config.args.cryptoasset,
                                 wallet=WALLET)

    else:
        return TransactionRecord(TransactionRecord.TYPE_WITHDRAWAL,
                                 DataParser.parse_timestamp(in_row[4]),
                                 sell_quantity=abs(Decimal(in_row[3])),
                                 sell_asset=config.args.cryptoasset,
                                 wallet=WALLET)

DataParser(DataParser.TYPE_WALLET,
           "Electrum",
           ['transaction_hash', 'label', 'confirmations', 'value', 'timestamp'],
           row_handler=parse_electrum)
