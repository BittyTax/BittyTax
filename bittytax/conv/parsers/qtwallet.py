# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownCryptoassetError, UnexpectedTypeError

WALLET = "Qt Wallet"

def parse_qt_wallet(data_row, parser, _filename):
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
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=symbol,
                                                 wallet=WALLET)
    elif in_row[2] == "Sent to":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[5])),
                                                 sell_asset=symbol,
                                                 wallet=WALLET)
    elif in_row[2] == "Mined":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_MINING,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=symbol,
                                                 wallet=WALLET)
    elif in_row[2] == "Payment to yourself":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=Decimal(0),
                                                 sell_asset=symbol,
                                                 fee_quantity=abs(Decimal(in_row[5])),
                                                 fee_asset=symbol,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

DataParser(DataParser.TYPE_WALLET,
           "Qt Wallet (i.e. Bitcoin Core, etc)",
           ['Confirmed', 'Date', 'Type', 'Label', 'Address',
            lambda c: re.match(r"Amount( \((\w+)\))?", c), 'ID'],
           worksheet_name="Qt Wallet",
           row_handler=parse_qt_wallet)
