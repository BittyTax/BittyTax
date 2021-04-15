# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal

from colorama import Fore

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataParserError, UnexpectedTypeError, \
                         MissingValueError, MissingComponentError

WALLET = "GateHub"

def parse_gatehub(data_rows, parser, _filename, _args):
    for data_row in data_rows:
        if config.debug:
            sys.stderr.write("%sconv: row[%s] %s\n" % (
                Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))

        if data_row.parsed:
            continue

        try:
            parse_gatehub_row(data_rows, parser, data_row)
        except DataParserError as e:
            data_row.failure = e

def parse_gatehub_row(data_rows, parser, data_row):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Time'])
    data_row.parsed = True

    t_type = ""
    buy_quantity = None
    buy_asset = ""
    sell_quantity = None
    sell_asset = ""
    fee_quantity = None
    fee_asset = ""

    if not row_dict['Amount']:
        raise MissingValueError(parser.in_header.index('Amount'), 'Amount', row_dict['Amount'])

    if row_dict['Type'] == "payment":
        if Decimal(row_dict['Amount']) < 0:
            t_type = TransactionOutRecord.TYPE_WITHDRAWAL
            sell_quantity = abs(Decimal(row_dict['Amount']))
            sell_asset = row_dict['Currency']
        else:
            t_type = TransactionOutRecord.TYPE_DEPOSIT
            buy_quantity = row_dict['Amount']
            buy_asset = row_dict['Currency']

        fee_quantity, fee_asset = find_same_tx(data_rows, row_dict['TX hash'], "network_fee")
    elif row_dict['Type'] == "exchange":
        t_type = TransactionOutRecord.TYPE_TRADE
        if Decimal(row_dict['Amount']) < 0:
            sell_quantity = abs(Decimal(row_dict['Amount']))
            sell_asset = row_dict['Currency']

            buy_quantity, buy_asset = find_same_tx(data_rows, row_dict['TX hash'], "exchange")
        else:
            buy_quantity = row_dict['Amount']
            buy_asset = row_dict['Currency']

            sell_quantity, sell_asset = find_same_tx(data_rows, row_dict['TX hash'], "exchange")

        if sell_quantity is None or buy_quantity is None:
            raise MissingComponentError(parser.in_header.index('TX hash'), 'TX hash',
                                        row_dict['TX hash'])

        fee_quantity, fee_asset = find_same_tx(data_rows, row_dict['TX hash'], "network_fee")
    elif "network_fee" in row_dict['Type']:
        # Fees which are not associated with a payment or exchange are added
        # as a Spend
        t_type = TransactionOutRecord.TYPE_SPEND
        sell_quantity = abs(Decimal(row_dict['Amount']))
        sell_asset = row_dict['Currency']
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

    data_row.t_record = TransactionOutRecord(t_type,
                                             data_row.timestamp,
                                             buy_quantity=buy_quantity,
                                             buy_asset=buy_asset,
                                             sell_quantity=sell_quantity,
                                             sell_asset=sell_asset,
                                             fee_quantity=fee_quantity,
                                             fee_asset=fee_asset,
                                             wallet=WALLET)

def find_same_tx(data_rows, tx_hash, tx_type):
    quantity = None
    asset = ""

    data_rows = [data_row for data_row in data_rows
                 if data_row.row_dict['TX hash'] == tx_hash and not data_row.parsed]
    for data_row in data_rows:
        if tx_type in data_row.row_dict['Type']:
            quantity = abs(Decimal(data_row.row_dict['Amount']))
            asset = data_row.row_dict['Currency']
            data_row.timestamp = DataParser.parse_timestamp(data_row.row_dict['Time'])
            data_row.parsed = True
            break

    return quantity, asset

DataParser(DataParser.TYPE_EXCHANGE,
           "GateHub (XRP)",
           ['Time', 'TX hash', 'Type', 'Amount', 'Currency', 'Currency Issuer Address',
            'Currency Issuer Name', 'Balance'],
           worksheet_name="Gatehub",
           all_handler=parse_gatehub)
