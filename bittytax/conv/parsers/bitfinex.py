# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys

from decimal import Decimal
from colorama import Fore, Back

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedContentError

WALLET = "Bitfinex"

PRECISION = Decimal('0.00000000')

def parse_bitfinex_trades2(data_row, parser, _filename):
    if not hasattr(parser, 'bitfinex_ledger'):
        parser.bitfinex_ledger = False
        for d in parser.data_files:
            if d.parser.worksheet_name == "Bitfinex L":
                parser.bitfinex_ledger = True
                sys.stderr.write(
                    "%sWARNING%s 'Bitfinex L' has been loaded first, so this sheet will be ignored.%s\n" % (
                        Back.YELLOW + Fore.BLACK, Back.RESET + Fore.YELLOW, Fore.RESET))
                break
    elif parser.bitfinex_ledger:
        return

    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[7], dayfirst=True)

    if Decimal(in_row[2]) > 0:
        sell_quantity = Decimal(in_row[3]) * Decimal(in_row[2])

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[2],
                                                 buy_asset=in_row[1].split('/')[0],
                                                 sell_quantity=sell_quantity.quantize(PRECISION),
                                                 sell_asset=in_row[1].split('/')[1],
                                                 fee_quantity=abs(Decimal(in_row[4])),
                                                 fee_asset=in_row[6],
                                                 wallet=WALLET)
    else:
        buy_quantity = Decimal(in_row[3]) * abs(Decimal(in_row[2]))

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=buy_quantity.quantize(PRECISION),
                                                 buy_asset=in_row[1].split('/')[1],
                                                 sell_quantity=abs(Decimal(in_row[2])),
                                                 sell_asset=in_row[1].split('/')[0],
                                                 fee_quantity=abs(Decimal(in_row[4])),
                                                 fee_asset=in_row[6],
                                                 wallet=WALLET)

def parse_bitfinex_trades(data_row, parser, _filename):
    if not hasattr(parser, 'bitfinex_ledger'):
        parser.bitfinex_ledger = False
        for d in parser.data_files:
            if d.parser.worksheet_name == "Bitfinex L":
                parser.bitfinex_ledger = True
                sys.stderr.write(
                    "%sWARNING%s 'Bitfinex L' has been loaded first, so this sheet will be ignored.%s\n" % (
                        Back.YELLOW + Fore.BLACK, Back.RESET + Fore.YELLOW, Fore.RESET))
                break
    elif parser.bitfinex_ledger:
        return

    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[6], dayfirst=True)

    if Decimal(in_row[2]) > 0:
        sell_quantity = Decimal(in_row[3]) * Decimal(in_row[2])

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[2],
                                                 buy_asset=in_row[1].split('/')[0],
                                                 sell_quantity=sell_quantity.quantize(PRECISION),
                                                 sell_asset=in_row[1].split('/')[1],
                                                 fee_quantity=abs(Decimal(in_row[4])),
                                                 fee_asset=in_row[5],
                                                 wallet=WALLET)
    else:
        buy_quantity = Decimal(in_row[3]) * abs(Decimal(in_row[2]))

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=buy_quantity.quantize(PRECISION),
                                                 buy_asset=in_row[1].split('/')[1],
                                                 sell_quantity=abs(Decimal(in_row[2])),
                                                 sell_asset=in_row[1].split('/')[0],
                                                 fee_quantity=abs(Decimal(in_row[4])),
                                                 fee_asset=in_row[5],
                                                 wallet=WALLET)

def parse_bitfinex_deposits_withdrawals(data_row, parser, _filename):
    if not hasattr(parser, 'bitfinex_ledger'):
        parser.bitfinex_ledger = False
        for d in parser.data_files:
            if d.parser.worksheet_name == "Bitfinex L":
                parser.bitfinex_ledger = True
                sys.stderr.write(
                    "%sWARNING%s 'Bitfinex L' has been loaded first, so this sheet will be ignored.%s\n" % (
                        Back.YELLOW + Fore.BLACK, Back.RESET + Fore.YELLOW, Fore.RESET))
                break
    elif parser.bitfinex_ledger:
        return

    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[1], dayfirst=True)

    if in_row[3] != "COMPLETED":
        return

    if Decimal(in_row[4]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=in_row[2],
                                                 fee_quantity=abs(Decimal(in_row[5])),
                                                 fee_asset=in_row[2],
                                                 wallet=WALLET)
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[4])),
                                                 sell_asset=in_row[2],
                                                 fee_quantity=abs(Decimal(in_row[5])),
                                                 fee_asset=in_row[2],
                                                 wallet=WALLET)


def parse_bitfinex_ledgers(data_rows, parser, _filename):
    for d in parser.data_files:
        if d.parser.worksheet_name == "Bitfinex T":
            got_trades = True
            sys.stderr.write(
                "%sNOTICE%s 'Bitfinex T' has been loaded, so buy/sell will be ignored in this sheet.%s\n" % (
                    Back.YELLOW + Fore.BLACK, Back.RESET + Fore.YELLOW, Fore.RESET))
        if d.parser.worksheet_name == "Bitfinex D,W":
            got_deposits_withdrawals = True
            sys.stderr.write(
                "%sNOTICE%s 'Bitfinex D,W' has been loaded, so deposit/withdrawal will be ignored in this sheet.%s\n" % (
                    Back.YELLOW + Fore.BLACK, Back.RESET + Fore.YELLOW, Fore.RESET))

    for data_row in data_rows:
        in_row = data_row.in_row
        header = parser.header
        timestamp = data_row.timestamp = DataParser.parse_timestamp('20'+in_row[header.index('DATE')], dayfirst=False)

        amount = in_row[header.index('AMOUNT')]
        asset = in_row[header.index('CURRENCY')]
        to_amount = None
        to_asset = ''
        t_type = TransactionOutRecord.TYPE_TRADE
        buy_quantity = sell_quantity = None
        buy_asset = sell_asset = ''
        fee_quantity = None
        fee_asset = ''
        comment = in_row[header.index('DESCRIPTION')]

        if "deposit" in comment.lower():
            if 'got_deposits_withdrawals' in locals():
                return
            t_type = TransactionOutRecord.TYPE_DEPOSIT
        elif "withdrawal" in comment.lower():
            if 'got_deposits_withdrawals' in locals():
                return
            t_type = TransactionOutRecord.TYPE_WITHDRAWAL
        elif "exchange" in comment.lower():
            if 'got_trades' in locals():
                return
            to_amount = '0.0'
            to_asset = asset
        elif "fees" in comment.lower():
            if 'got_trades' in locals():
                return
            to_amount = '0.0'
            to_asset = asset
        else:
            raise UnexpectedContentError(header.index('DESCRIPTION'), 'DESCRIPTION', comment)

        if Decimal(amount) > 0:
            buy_quantity = amount
            buy_asset = asset
            sell_quantity = to_amount
            sell_asset = to_asset
        else:
            sell_quantity = abs(Decimal(amount))
            sell_asset = asset
            buy_quantity = to_amount
            buy_asset = to_asset

        data_row.t_record = TransactionOutRecord(t_type, timestamp,
                                                 buy_quantity, buy_asset, None,
                                                 sell_quantity, sell_asset, None,
                                                 fee_quantity, fee_asset, None,
                                                 WALLET, comment)


DataParser(DataParser.TYPE_EXCHANGE,
           "Bitfinex Trades",
           ['#', 'PAIR', 'AMOUNT', 'PRICE', 'FEE', 'FEE PERC', 'FEE CURRENCY', 'DATE', 'ORDER ID'],
           worksheet_name="Bitfinex T",
           row_handler=parse_bitfinex_trades2)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bitfinex Trades",
           ['#', 'PAIR', 'AMOUNT', 'PRICE', 'FEE', 'FEE CURRENCY', 'DATE', 'ORDER ID'],
           worksheet_name="Bitfinex T",
           row_handler=parse_bitfinex_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bitfinex Deposits/Withdrawals",
           ['#', 'DATE', 'CURRENCY', 'STATUS', 'AMOUNT', 'FEES', 'DESCRIPTION', 'TRANSACTION ID'],
           worksheet_name="Bitfinex D,W",
           row_handler=parse_bitfinex_deposits_withdrawals)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bitfinex Ledgers",
           ['#', 'DESCRIPTION', 'CURRENCY', 'AMOUNT', 'BALANCE', 'DATE', 'WALLET'],
           worksheet_name="Bitfinex L",
           all_handler=parse_bitfinex_ledgers)
