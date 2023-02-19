# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal

from colorama import Fore

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataRowError, UnexpectedTypeError

WALLET = "Gravity"
SYSTEM_ACCOUNT = "00000000-0000-0000-0000-000000000000"

def parse_gravity_v2(data_row, _parser, **_kwargs):
    parse_gravity_v1(data_row, _parser, v2=True, **_kwargs)

def parse_gravity_v1(data_rows, parser, **kwargs):
    if kwargs.get('v2'):
        referral_type = "referral fees payout"
    else:
        referral_type = "referral fees grouping"

    tx_ids = {}
    for dr in data_rows:
        if dr.row_dict['transaction id'] in tx_ids:
            tx_ids[dr.row_dict['transaction id']].append(dr)
        else:
            tx_ids[dr.row_dict['transaction id']] = [dr]

    for data_row in data_rows:
        if config.debug:
            sys.stderr.write("%sconv: row[%s] %s\n" % (
                Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))

        if data_row.parsed:
            continue

        try:
            parse_gravity_row(tx_ids, parser, data_row, referral_type)
        except DataRowError as e:
            data_row.failure = e

def parse_gravity_row(tx_ids, parser, data_row, referral_type):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['date utc'])
    data_row.parsed = True

    t_type = ""
    buy_quantity = None
    buy_asset = ""
    sell_quantity = None
    sell_asset = ""
    fee_quantity = None
    fee_asset = ""

    if row_dict['transaction type'] == "deposit":
        if row_dict['from account'] == SYSTEM_ACCOUNT:
            t_type = TransactionOutRecord.TYPE_DEPOSIT
            buy_quantity = row_dict['amount']
            buy_asset = row_dict['currency']
        else:
            return

    elif row_dict['transaction type'] == "withdrawal":
        if row_dict['to account'] == SYSTEM_ACCOUNT:
            t_type = TransactionOutRecord.TYPE_WITHDRAWAL
            sell_quantity = row_dict['amount']
            sell_asset = row_dict['currency']
            quantity, asset = get_tx(tx_ids[row_dict['transaction id']],
                                     "withdrawal", 'to account')
            if Decimal(sell_quantity) < Decimal(quantity):
                # Swap sell/fee around
                fee_quantity = sell_quantity
                fee_asset = sell_asset
                sell_quantity = quantity
                sell_asset = asset
            else:
                fee_quantity = quantity
                fee_asset = asset

        else:
            return
    elif row_dict['transaction type'] == "trade" and row_dict['from account'] == SYSTEM_ACCOUNT:
        t_type = TransactionOutRecord.TYPE_TRADE
        buy_quantity = row_dict['amount']
        buy_asset = row_dict['currency']

        sell_quantity, sell_asset = get_tx(tx_ids[row_dict['transaction id']],
                                           "trade", 'to account')
        if sell_quantity is None:
            return
    elif row_dict['transaction type'] == "trade" and row_dict['to account'] == SYSTEM_ACCOUNT:
        t_type = TransactionOutRecord.TYPE_TRADE
        sell_quantity = row_dict['amount']
        sell_asset = row_dict['currency']

        buy_quantity, buy_asset = get_tx(tx_ids[row_dict['transaction id']],
                                         "trade", 'from account')
        if buy_quantity is None:
            return
    elif row_dict['transaction type'] == referral_type:
        t_type = TransactionOutRecord.TYPE_GIFT_RECEIVED
        buy_quantity = row_dict['amount']
        buy_asset = row_dict['currency']
    elif row_dict['transaction type'] in ("referral fees collection", "referral fees grouping",
                                          "referral fees transfer", "internal transfer",
                                          "correction"):
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index('transaction type'), 'transaction type',
                                  row_dict['transaction type'])

    data_row.t_record = TransactionOutRecord(t_type,
                                             data_row.timestamp,
                                             buy_quantity=buy_quantity,
                                             buy_asset=buy_asset,
                                             sell_quantity=sell_quantity,
                                             sell_asset=sell_asset,
                                             fee_quantity=fee_quantity,
                                             fee_asset=fee_asset,
                                             wallet=WALLET)

def get_tx(tx_id_rows, tx_type, system_acc):
    quantity = None
    asset = ""

    for data_row in tx_id_rows:
        if not data_row.parsed and \
                data_row.row_dict['transaction type'] == tx_type and \
                data_row.row_dict[system_acc] == SYSTEM_ACCOUNT:
            quantity = data_row.row_dict['amount']
            asset = data_row.row_dict['currency']
            data_row.timestamp = DataParser.parse_timestamp(data_row.row_dict['date utc'])
            data_row.parsed = True
            break

    return quantity, asset

DataParser(DataParser.TYPE_EXCHANGE,
           "Gravity (Bitstocks)",
           ['transaction id', 'from account', 'to account', 'from account type', 'to account type',
            'date utc', 'transaction type', 'status', 'amount', 'currency', 'withdrawal_address'],
           worksheet_name="Gravity",
           all_handler=parse_gravity_v2)

DataParser(DataParser.TYPE_EXCHANGE,
           "Gravity (Bitstocks)",
           ['transaction id', 'from account', 'to account', 'date utc', 'transaction type',
            'status', 'amount', 'currency'],
           worksheet_name="Gravity",
           all_handler=parse_gravity_v1)
