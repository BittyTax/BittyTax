# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownCryptoassetError, UnexpectedTypeError

WALLET = "Qt Wallet"

def parse_qt_wallet(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[1], tz='Europe/London')

    if parser.args[0].group(2):
        symbol = parser.args[0].group(2)
    elif config.args.cryptoasset:
        symbol = config.args.cryptoasset
    else:
        raise UnknownCryptoassetError

    if in_row[0] == "false" and not config.args.unconfirmed:
        # skip unconfirmed transactions
        return

    if in_row[2] == "Received with":
        t_type = TransactionOutRecord.TYPE_DEPOSIT
    elif in_row[2] == "Sent to":
        t_type = TransactionOutRecord.TYPE_WITHDRAWAL
    elif in_row[2] == "Mined":
        t_type = TransactionOutRecord.TYPE_MINING
    elif in_row[2] == "Payment to yourself":
        t_type = TransactionOutRecord.TYPE_WITHDRAWAL
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

    if Decimal(in_row[5]) > 0:
        data_row.t_record = TransactionOutRecord(t_type,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=symbol,
                                                 wallet=WALLET)
    else:
        data_row.t_record = TransactionOutRecord(t_type,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[5])),
                                                 sell_asset=symbol,
                                                 wallet=WALLET)

DataParser(DataParser.TYPE_WALLET,
           "Qt Wallet (i.e. Bitcoin Core, etc)",
           ['Confirmed', 'Date', 'Type', 'Label', 'Address',
            lambda c: re.match(r"Amount( \((\w+)\))?", c), 'ID'],
           worksheet_name="Qt Wallet",
           row_handler=parse_qt_wallet)
