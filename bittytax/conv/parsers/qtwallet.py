# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
import re
from decimal import Decimal

from colorama import Fore, Back

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownCryptoassetError, UnexpectedTypeError, DataFilenameError

WALLET = "Qt Wallet"

def parse_qt_wallet(data_row, parser, filename):
    in_row = data_row.in_row
    header = parser.header
    data_row.timestamp = DataParser.parse_timestamp(in_row[header.index('Label') if 'Label' in header else header.index('Date/Time')], tz='Europe/London')
    # amount = None
    # symbol = None
    # 'Date/Time'
    action = in_row[header.index('Type')]

    if 'Amount' in header:
        note = ''
        amount = in_row[header.index('Amount')]
        if 'vericoin' in filename.lower() or 'vrc' in filename.lower():
            symbol = 'vrc'
        else:
            raise DataFilenameError(filename, "Asset Name")
    else:
        amount, symbol = get_amount(in_row[5])
        note = in_row[header.index('Label')]

    if not config.args.cryptoasset:
        try:
            if parser.args[0].group(2):
                symbol = parser.args[0].group(2)
            elif not symbol:
                raise UnknownCryptoassetError
        except IndexError:
            pass
    else:
        symbol = config.args.cryptoasset

    if 'Confirmed' in header and in_row[header.index('Confirmed')] == "false" and not config.args.unconfirmed:
        sys.stderr.write("%srow[%s] %s\n" % (
            Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
        sys.stderr.write("%sWARNING%s Skipping unconfirmed transaction, "
                         "use the [-uc] option to include it\n" % (
                             Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW))
        return

    if action in ("Received with", "Receive"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=amount,
                                                 buy_asset=symbol,
                                                 wallet=WALLET,
                                                 note=note)
    elif action in ("Sent to", "Send"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(amount)),
                                                 sell_asset=symbol,
                                                 wallet=WALLET,
                                                 note=note)
    elif action in ("Mined", "Masternode Reward", "Stake"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_MINING,
                                                 data_row.timestamp,
                                                 buy_quantity=amount,
                                                 buy_asset=symbol,
                                                 wallet=WALLET,
                                                 note=note)
    elif action == "Payment to yourself":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=Decimal(0),
                                                 sell_asset=symbol,
                                                 fee_quantity=amount,
                                                 fee_asset=symbol,
                                                 wallet=WALLET,
                                                 note=note)
    elif action == "Name operation":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=amount,
                                                 sell_asset=symbol,
                                                 wallet=WALLET,
                                                 note=note)
    else:
        raise UnexpectedTypeError(header.index('Type'), 'Type', action)

def get_amount(amount):
    match = re.match(r"^(-?\d+\.\d+) (\w{3,4})$", amount)

    if match:
        amount = match.group(1)
        symbol = match.group(2)
        return abs(Decimal(amount)), symbol
    return abs(Decimal(amount)), None

DataParser(DataParser.TYPE_WALLET,
           "Qt Wallet (i.e. Bitcoin Core, etc)",
           ['Confirmed', 'Date', 'Type', 'Label', 'Address',
            lambda c: re.match(r"Amount( \((\w+)\))?", c), 'ID'],
           worksheet_name="Qt Wallet",
           row_handler=parse_qt_wallet)

DataParser(DataParser.TYPE_WALLET,
           "Qt Wallet (i.e. Vericoin Qt, etc)",
           ['Transaction', 'Block', 'Date/Time', 'Type', 'Amount', 'Total'],
           worksheet_name="Qt Wallet",
           row_handler=parse_qt_wallet)
