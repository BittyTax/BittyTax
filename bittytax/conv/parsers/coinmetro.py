# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

import sys
from decimal import Decimal

from colorama import Fore

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataRowError, UnexpectedTypeError, MissingComponentError

WALLET = "Coinmetro"

def parse_coinmetro(data_rows, parser, **_kwargs):
    for row_index, data_row in enumerate(data_rows):
        if config.debug:
            sys.stderr.write("%sconv: row[%s] %s\n" % (
                Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))

        if data_row.parsed:
            continue

        try:
            parse_coinmetro_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e

def parse_coinmetro_row(data_rows, parser, data_row, row_index):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date'])
    data_row.parsed = True

    if "Deposit" in row_dict['Description']:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(row_dict['Amount']) +
                                                 Decimal(row_dict['Fee']),
                                                 buy_asset=row_dict['Asset'],
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=row_dict['Asset'],
                                                 wallet=WALLET)
    elif "Withdrawal" in row_dict['Description']:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(row_dict['Amount'])),
                                                 sell_asset=row_dict['Asset'],
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=row_dict['Asset'],
                                                 wallet=WALLET)
    elif "Order" in row_dict['Description']:
        if Decimal(row_dict['Amount']) > 0:
            sell_quantity, sell_asset = get_sell(data_rows, row_index, row_dict['Description'])

            if sell_quantity is None or sell_asset is None:
                raise MissingComponentError(parser.in_header.index('Description'), 'Description',
                                            row_dict['Description'])

            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Amount'],
                                                     buy_asset=row_dict['Asset'],
                                                     sell_quantity=sell_quantity,
                                                     sell_asset=sell_asset,
                                                     fee_quantity=row_dict['Fee'],
                                                     fee_asset=row_dict['Asset'],
                                                     wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Description'), 'Description',
                                  row_dict['Description'])

def get_sell(data_rows, row_index, order_id):
    data_row = data_rows[row_index+1]
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date'])
    data_row.parsed = True

    if row_dict['Description'] == order_id:
        return abs(Decimal(row_dict['Amount'])), row_dict['Asset']
    return None, None

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinmetro",
           ['Asset', 'Date', 'Description', 'Amount', 'Fee', 'Price', 'Pair', 'Other Currency',
            'Other Amount', 'IBAN', 'Transaction Hash', 'Address', 'Tram', 'Additional Info',
            'Reference Note', 'Comment'],
           worksheet_name="Coinmetro",
           all_handler=parse_coinmetro)
