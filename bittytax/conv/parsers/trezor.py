# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownCryptoassetError, UnexpectedTypeError

WALLET = "Trezor"

def parse_trezor2(data_row, parser, filename, args):
    parse_trezor(data_row, parser, filename, args)

def parse_trezor(data_row, parser, filename, args):
    in_row = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(in_row['Date'] + 'T' + in_row['Time'])

    if not args.cryptoasset:
        match = re.match(r".+_(\w{3,4})\.csv$", filename)

        if match:
            symbol = match.group(1).upper()
        else:
            raise UnknownCryptoassetError
    else:
        symbol = args.cryptoasset

    if in_row['TX type'] == "IN":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row['Value'],
                                                 buy_asset=symbol,
                                                 fee_quantity=Decimal(in_row['TX total']) - \
                                                              Decimal(in_row['Value']),
                                                 fee_asset=symbol,
                                                 wallet=WALLET,
                                                 note=in_row.get('Address Label', ''))
    elif in_row['TX type'] == "OUT":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row['Value'],
                                                 sell_asset=symbol,
                                                 fee_quantity=abs(Decimal(in_row['TX total']))
                                                 -Decimal(in_row['Value']),
                                                 fee_asset=symbol,
                                                 wallet=WALLET,
                                                 note=in_row.get('Address Label', ''))
    elif in_row['TX type'] == "SELF":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=0,
                                                 sell_asset=symbol,
                                                 fee_quantity=abs(Decimal(in_row['TX total'])),
                                                 fee_asset=symbol,
                                                 wallet=WALLET,
                                                 note=in_row.get('Address Label', ''))
    else:
        raise UnexpectedTypeError(parser.in_header.index('TX type'), 'TX type', in_row['TX type'])

DataParser(DataParser.TYPE_WALLET,
           "Trezor",
           ['Date', 'Time', 'TX id', 'Address', 'Address Label', 'TX type', 'Value', 'TX total',
            'Balance'],
           worksheet_name="Trezor",
           row_handler=parse_trezor2)

DataParser(DataParser.TYPE_WALLET,
           "Trezor",
           ['Date', 'Time', 'TX id', 'Address', 'TX type', 'Value', 'TX total',
            'Balance'],
           worksheet_name="Trezor",
           row_handler=parse_trezor)
