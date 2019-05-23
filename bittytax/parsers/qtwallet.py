# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019
# $id: $

import re
from decimal import Decimal

from ..config import config
from ..record import TransactionRecord
from ..parser import DataParser

WALLET = "Qt Wallet"

def parse_qt_wallet(in_row, *args):
    if args[0].group(2):
        symbol = args[0].group(2)
    elif config.args.cryptoasset:
        symbol = config.args.cryptoasset
    else:
        raise Exception(config.ERROR_TXT[0])

    if in_row[0] == "false" and not config.args.unconfirmed:
        # skip unconfirmed transactions
        return []

    if in_row[2] == "Received with":
        t_type = TransactionRecord.TYPE_DEPOSIT
    elif in_row[2] == "Sent to":
        t_type = TransactionRecord.TYPE_WITHDRAWAL
    elif in_row[2] == "Mined":
        t_type = TransactionRecord.TYPE_MINING
    elif in_row[2] == "Payment to yourself":
        t_type = TransactionRecord.TYPE_WITHDRAWAL
    else:
        raise ValueError("Unrecognised transaction type: " + in_row[2])

    if Decimal(in_row[5]) > 0:
        return TransactionRecord(t_type,
                                 DataParser.parse_timestamp(in_row[1], tz='Europe/London'),
                                 buy_quantity=in_row[5],
                                 buy_asset=symbol,
                                 wallet=WALLET)
    else:
        return TransactionRecord(t_type,
                                 DataParser.parse_timestamp(in_row[1], tz='Europe/London'),
                                 sell_quantity=abs(Decimal(in_row[5])),
                                 sell_asset=symbol,
                                 wallet=WALLET)

DataParser(DataParser.TYPE_WALLET,
           "Qt Wallet (i.e. Bitcoin Core, etc)",
           ['Confirmed', 'Date', 'Type', 'Label', 'Address',
            lambda c: re.match(r"Amount( \((\w+)\))?", c), 'ID'],
           row_handler=parse_qt_wallet)
