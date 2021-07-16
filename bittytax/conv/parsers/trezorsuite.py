# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import re

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownCryptoassetError, UnexpectedTypeError

WALLET = "Trezor"

def parse_trezor_suite(data_row, parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date & Time'], dayfirst=True,
                                                    tz='Europe/London')

    if not kwargs['cryptoasset']:
        match = re.match(r".+-(\w{3,4})-.*", kwargs['filename'])

        if match:
            symbol = match.group(1).upper()
        else:
            raise UnknownCryptoassetError(kwargs['filename'], kwargs.get('worksheet'))
    else:
        symbol = kwargs['cryptoasset']

    if row_dict['Type'] == "RECV":
        # Workaround: we have to ignore the fee as fee is for the sender
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Total'],
                                                 buy_asset=symbol,
                                                 wallet=WALLET)
    elif row_dict['Type'] == "SENT":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Total'],
                                                 sell_asset=symbol,
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=symbol,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

DataParser(DataParser.TYPE_WALLET,
           "Trezor Suite",
           ['Date & Time', 'Type', 'Transaction ID', 'Addresses', 'Fee', 'Total'],
           worksheet_name="Trezor",
           row_handler=parse_trezor_suite)
