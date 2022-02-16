# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

import sys
import copy

from colorama import Fore

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataRowError, UnexpectedTypeError

KOINLY_D_MAPPING = {'': TransactionOutRecord.TYPE_GIFT_RECEIVED,
                    'airdrop': TransactionOutRecord.TYPE_AIRDROP,
                    'fork': None,
                    'mining': TransactionOutRecord.TYPE_MINING,
                    'reward': TransactionOutRecord.TYPE_GIFT_RECEIVED,
                    'income': TransactionOutRecord.TYPE_INCOME,
                    'loan_interest': TransactionOutRecord.TYPE_INTEREST,
                    'realized_gain': None}

KOINLY_W_MAPPING = {'': TransactionOutRecord.TYPE_GIFT_SENT,
                    'gift': TransactionOutRecord.TYPE_GIFT_SENT,
                    'lost': TransactionOutRecord.TYPE_LOST,
                    'cost': TransactionOutRecord.TYPE_SPEND,
                    'margin_fee': None,
                    'interest_payment': None,
                    'realized_loss': None,
                    'swap': None}

def parse_koinly(data_rows, parser, **_kwargs):
    for row_index, data_row in enumerate(data_rows):
        if config.debug:
            sys.stderr.write("%sconv: row[%s] %s\n" % (
                Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))

        if data_row.parsed:
            continue

        try:
            parse_koinly_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e

def parse_koinly_row(data_rows, parser, data_row, row_index):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date'])
    data_row.parsed = True

    if row_dict['Fee Amount']:
        fee_quantity = row_dict['Fee Amount']
    else:
        fee_quantity = None

    if row_dict['Fee Value (GBP)']:
        fee_value = row_dict['Fee Value (GBP)']
    else:
        fee_value = None

    if row_dict['Type'] in ("buy", "sell", "exchange"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Received Amount'],
                                                 buy_asset=row_dict['Received Currency'],
                                                 buy_value=row_dict['Net Value (GBP)'],
                                                 sell_quantity=row_dict['Sent Amount'],
                                                 sell_asset=row_dict['Sent Currency'],
                                                 sell_value=row_dict['Net Value (GBP)'],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=row_dict['Fee Currency'],
                                                 fee_value=fee_value,
                                                 wallet=row_dict['Sending Wallet'],
                                                 note=row_dict['Description'])
    elif row_dict['Type'] == "transfer":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Sent Amount'],
                                                 sell_asset=row_dict['Sent Currency'],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=row_dict['Fee Currency'],
                                                 wallet=row_dict['Sending Wallet'],
                                                 note=row_dict['Description'])
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []
        dup_data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Received Amount'],
                                                     buy_asset=row_dict['Received Currency'],
                                                     wallet=row_dict['Receiving Wallet'],
                                                     note=row_dict['Description'])
        data_rows.insert(row_index + 1, dup_data_row)
    elif row_dict['Type'] in ("fiat_deposit", "crypto_deposit"):
        if row_dict['Label'] in KOINLY_D_MAPPING and KOINLY_D_MAPPING[row_dict['Label']]:
            data_row.t_record = TransactionOutRecord(KOINLY_D_MAPPING[row_dict['Label']],
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Received Amount'],
                                                     buy_asset=row_dict['Received Currency'],
                                                     buy_value=row_dict['Net Value (GBP)'],
                                                     wallet=row_dict['Receiving Wallet'],
                                                     note=row_dict['Description'])
        else:
            raise UnexpectedTypeError(parser.in_header.index('Label'), 'Label', row_dict['Label'])
    elif row_dict['Type'] in ("fiat_withdrawal", "crypto_withdrawal"):
        if row_dict['Label'] in KOINLY_W_MAPPING and KOINLY_W_MAPPING[row_dict['Label']]:
            data_row.t_record = TransactionOutRecord(KOINLY_W_MAPPING[row_dict['Label']],
                                                     data_row.timestamp,
                                                     sell_quantity=row_dict['Sent Amount'],
                                                     sell_asset=row_dict['Sent Currency'],
                                                     sell_value=row_dict['Net Value (GBP)'],
                                                     fee_quantity=fee_quantity,
                                                     fee_asset=row_dict['Fee Currency'],
                                                     fee_value=fee_value,
                                                     wallet=row_dict['Sending Wallet'],
                                                     note=row_dict['Description'])
        else:
            raise UnexpectedTypeError(parser.in_header.index('Label'), 'Label', row_dict['Label'])
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

DataParser(DataParser.TYPE_ACCOUNTING,
           "Koinly",
           ['Date', 'Type', 'Label', 'Sending Wallet', 'Sent Amount', 'Sent Currency',
            'Sent Cost Basis', 'Receiving Wallet', 'Received Amount', 'Received Currency',
            'Received Cost Basis', 'Fee Amount', 'Fee Currency', 'Gain (GBP)', 'Net Value (GBP)',
            'Fee Value (GBP)', 'TxSrc', 'TxDest', 'TxHash',
            'Description'],
           worksheet_name="Koinly",
           all_handler=parse_koinly)
