# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
import re
from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError, UnexpectedContentError

WALLET = "Coinbase"
DUPLICATE = "Duplicate"

def parse_coinbase(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Timestamp'])

    spot_price_ccy = DataParser.convert_currency(row_dict['Spot Price at Transaction'],
                                                 row_dict['Spot Price Currency'],
                                                 data_row.timestamp)
    total_ccy = DataParser.convert_currency(row_dict['Total (inclusive of fees)'],
                                            row_dict['Spot Price Currency'],
                                            data_row.timestamp)

    do_parse_coinbase(data_row, parser, (spot_price_ccy, row_dict['Subtotal'],
                                         total_ccy, row_dict['Fees']))

def parse_coinbase_gbp(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Timestamp'])
    fiat_values = get_fiat_values(row_dict, 'GBP', data_row.timestamp)
    do_parse_coinbase(data_row, parser, fiat_values)

def parse_coinbase_eur(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Timestamp'])
    fiat_values = get_fiat_values(row_dict, 'EUR', data_row.timestamp)
    do_parse_coinbase(data_row, parser, fiat_values)

def parse_coinbase_usd(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Timestamp'])
    fiat_values = get_fiat_values(row_dict, 'USD', data_row.timestamp)
    do_parse_coinbase(data_row, parser, fiat_values)

def get_fiat_values(row_dict, currency, timestamp):
    sp_header = '%s Spot Price at Transaction' % currency
    st_header = '%s Subtotal' % currency
    t_header = '%s Total (inclusive of fees)' % currency
    f_header = '%s Fees' % currency

    spot_price_ccy = DataParser.convert_currency(row_dict[sp_header], currency, timestamp)
    total_ccy = DataParser.convert_currency(row_dict[t_header], currency, timestamp)
    return (spot_price_ccy, row_dict[st_header], total_ccy, row_dict[f_header])

def do_parse_coinbase(data_row, parser, fiat_values):
    (spot_price_ccy, subtotal, total_ccy, fees) = fiat_values
    row_dict = data_row.row_dict

    if row_dict['Transaction Type'] == "Receive":
        if "Coinbase Referral" in row_dict['Notes']:
            # We can calculate the exact buy_value from the spot price
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                 data_row.timestamp,
                                 buy_quantity=row_dict['Quantity Transacted'],
                                 buy_asset=row_dict['Asset'],
                                 buy_value=spot_price_ccy * \
                                           Decimal(row_dict['Quantity Transacted']),
                                 wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Quantity Transacted'],
                                                     buy_asset=row_dict['Asset'],
                                                     wallet=WALLET)
    elif row_dict['Transaction Type'] in ("Coinbase Earn", "Rewards Income", "Learning Reward"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INCOME,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Quantity Transacted'],
                                                 buy_asset=row_dict['Asset'],
                                                 buy_value=total_ccy,
                                                 wallet=WALLET)
    elif row_dict['Transaction Type'] == "Send":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Quantity Transacted'],
                                                 sell_asset=row_dict['Asset'],
                                                 wallet=WALLET)
    elif row_dict['Transaction Type'] == "Buy":
        currency = get_currency(row_dict['Notes'])
        if currency is None:
            raise UnexpectedContentError(parser.in_header.index('Notes'), 'Notes',
                                         row_dict['Notes'])

        if config.coinbase_zero_fees_are_gifts and Decimal(fees) == 0:
            # Zero fees "may" indicate an early referral reward, or airdrop
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Quantity Transacted'],
                                                     buy_asset=row_dict['Asset'],
                                                     buy_value=total_ccy if total_ccy > 0 else None,
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Quantity Transacted'],
                                                     buy_asset=row_dict['Asset'],
                                                     sell_quantity=subtotal,
                                                     sell_asset=currency,
                                                     fee_quantity=fees,
                                                     fee_asset=currency,
                                                     wallet=WALLET)
    elif row_dict['Transaction Type'] == "Sell":
        currency = get_currency(row_dict['Notes'])
        if currency is None:
            raise UnexpectedContentError(parser.in_header.index('Notes'), 'Notes',
                                         row_dict['Notes'])

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=subtotal,
                                                 buy_asset=currency,
                                                 sell_quantity=row_dict['Quantity Transacted'],
                                                 sell_asset=row_dict['Asset'],
                                                 fee_quantity=fees,
                                                 fee_asset=currency,
                                                 wallet=WALLET)
    elif row_dict['Transaction Type'] == "Convert":
        convert_info = get_convert_info(row_dict['Notes'])
        if convert_info is None:
            raise UnexpectedContentError(parser.in_header.index('Notes'), 'Notes',
                                         row_dict['Notes'])

        buy_quantity = convert_info[2]
        buy_asset = convert_info[3]
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=buy_quantity,
                                                 buy_asset=buy_asset,
                                                 buy_value=total_ccy,
                                                 sell_quantity=row_dict['Quantity Transacted'],
                                                 sell_asset=row_dict['Asset'],
                                                 sell_value=total_ccy,
                                                 wallet=WALLET)

    else:
        raise UnexpectedTypeError(parser.in_header.index('Transaction Type'), 'Transaction Type',
                                  row_dict['Transaction Type'])

def get_convert_info(notes):
    if sys.version_info[0] < 3:
        notes = notes.decode('utf8')

    match = re.match(r'^Converted ([\d|,]*\.\d+) (\w+) to ([\d|,]*\.\d+) (\w+) *$', notes)

    if match:
        return match.groups()
    return None

def get_currency(notes):
    if sys.version_info[0] < 3:
        notes = notes.decode('utf8')

    match = re.match(r".+for .{1}[\d|,]+\.\d{2} (\w{3})$", notes)

    if match:
        return match.group(1)
    return None

def parse_coinbase_transfers(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Timestamp'])

    if row_dict['Type'] == "Deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Total'],
                                                 buy_asset=row_dict['Currency'],
                                                 fee_quantity=row_dict['Fees'],
                                                 fee_asset=row_dict['Currency'],
                                                 wallet=WALLET)
    elif row_dict['Type'] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Total'],
                                                 sell_asset=row_dict['Currency'],
                                                 fee_quantity=row_dict['Fees'],
                                                 fee_asset=row_dict['Currency'],
                                                 wallet=WALLET)
    elif row_dict['Type'] == "Buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict[parser.in_header[2]],
                                                 buy_asset=parser.in_header[2],
                                                 sell_quantity=row_dict['Subtotal'],
                                                 sell_asset=row_dict['Currency'],
                                                 fee_quantity=row_dict['Fees'],
                                                 fee_asset=row_dict['Currency'],
                                                 wallet=WALLET)
    elif row_dict['Type'] == "Sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Subtotal'],
                                                 buy_asset=row_dict['Currency'],
                                                 sell_quantity=row_dict[parser.in_header[2]],
                                                 sell_asset=parser.in_header[2],
                                                 fee_quantity=row_dict['Fees'],
                                                 fee_asset=row_dict['Currency'],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

def parse_coinbase_transactions(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Timestamp'])

    if data_row.row[21] != "":
        # Hash so must be external crypto deposit or withdrawal
        if Decimal(row_dict['Amount']) < 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                     data_row.timestamp,
                                                     sell_quantity=abs(Decimal(row_dict['Amount'])),
                                                     sell_asset=row_dict['Currency'],
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Amount'],
                                                     buy_asset=row_dict['Currency'],
                                                     wallet=WALLET)
    elif row_dict['Transfer ID'] != "":
        # Transfer ID so could be a trade or external fiat deposit/withdrawal
        if row_dict['Currency'] != row_dict['Transfer Total Currency']:
            # Currencies are different so must be a trade
            if Decimal(row_dict['Amount']) < 0:
                data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity= \
                                                     Decimal(row_dict['Transfer Total']) + \
                                                     Decimal(row_dict['Transfer Fee']),
                                                 buy_asset=row_dict['Transfer Total Currency'],
                                                 sell_quantity=abs(Decimal(row_dict['Amount'])),
                                                 sell_asset=row_dict['Currency'],
                                                 fee_quantity=row_dict['Transfer Fee'],
                                                 fee_asset=row_dict['Transfer Fee Currency'],
                                                 wallet=WALLET)
            else:
                data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Amount'],
                                                     buy_asset=row_dict['Currency'],
                                                     sell_quantity=
                                                         Decimal(row_dict['Transfer Total']) - \
                                                         Decimal(row_dict['Transfer Fee']),
                                                     sell_asset=row_dict['Transfer Total Currency'],
                                                     fee_quantity=row_dict['Transfer Fee'],
                                                     fee_asset=row_dict['Transfer Fee Currency'],
                                                     wallet=WALLET)
        else:
            if Decimal(row_dict['Amount']) < 0:
                data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                     data_row.timestamp,
                                                     sell_quantity=row_dict['Transfer Total'],
                                                     sell_asset=row_dict['Currency'],
                                                     fee_quantity=row_dict['Transfer Fee'],
                                                     fee_asset=row_dict['Transfer Fee Currency'],
                                                     wallet=WALLET)
            else:
                data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Transfer Total'],
                                                     buy_asset=row_dict['Currency'],
                                                     fee_quantity=row_dict['Transfer Fee'],
                                                     fee_asset=row_dict['Transfer Fee Currency'],
                                                     wallet=WALLET)
    else:
        # Could be a referral bonus or deposit/withdrawal to/from Coinbase Pro
        if row_dict['Notes'] != "" and row_dict['Currency'] == "BTC":
            # Bonus is always in BTC
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Amount'],
                                                     buy_asset=row_dict['Currency'],
                                                     wallet=WALLET)
        elif row_dict['Notes'] != "" and row_dict['Currency'] != "BTC":
            # Special case, flag as duplicate entry, trade will be in BTC Wallet Transactions Report
            if Decimal(row_dict['Amount']) < 0:
                data_row.t_record = TransactionOutRecord(DUPLICATE,
                                                     data_row.timestamp,
                                                     sell_quantity=abs(Decimal(row_dict['Amount'])),
                                                     sell_asset=row_dict['Currency'],
                                                     wallet=WALLET)
            else:
                data_row.t_record = TransactionOutRecord(DUPLICATE,
                                                         data_row.timestamp,
                                                         buy_quantity=row_dict['Amount'],
                                                         buy_asset=row_dict['Currency'],
                                                         wallet=WALLET)
        elif Decimal(row_dict['Amount']) < 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                     data_row.timestamp,
                                                     sell_quantity=abs(Decimal(row_dict['Amount'])),
                                                     sell_asset=row_dict['Currency'],
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Amount'],
                                                     buy_asset=row_dict['Currency'],
                                                     wallet=WALLET)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase",
           ['Timestamp', 'Transaction Type', 'Asset', 'Quantity Transacted',
            'Spot Price Currency', 'Spot Price at Transaction', 'Subtotal',
            'Total (inclusive of fees)', 'Fees', 'Notes'],
           worksheet_name="Coinbase",
           row_handler=parse_coinbase)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase",
           ['Timestamp', 'Transaction Type', 'Asset', 'Quantity Transacted',
            'GBP Spot Price at Transaction', 'GBP Subtotal', 'GBP Total (inclusive of fees)',
            'GBP Fees', 'Notes'],
           worksheet_name="Coinbase",
           row_handler=parse_coinbase_gbp)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase",
           ['Timestamp', 'Transaction Type', 'Asset', 'Quantity Transacted',
            'EUR Spot Price at Transaction', 'EUR Subtotal', 'EUR Total (inclusive of fees)',
            'EUR Fees', 'Notes'],
           worksheet_name="Coinbase",
           row_handler=parse_coinbase_eur)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase",
           ['Timestamp', 'Transaction Type', 'Asset', 'Quantity Transacted',
            'USD Spot Price at Transaction', 'USD Subtotal', 'USD Total (inclusive of fees)',
            'USD Fees', 'Notes'],
           worksheet_name="Coinbase",
           row_handler=parse_coinbase_usd)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase Transfers",
           ['Timestamp', 'Type', None, 'Subtotal', 'Fees', 'Total', 'Currency', 'Price Per Coin',
            'Payment Method', 'ID', 'Share'],
           worksheet_name="Coinbase",
           row_handler=parse_coinbase_transfers)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase Transactions",
           ['Timestamp', 'Balance', 'Amount', 'Currency', 'To', 'Notes', 'Instantly Exchanged',
            'Transfer Total', 'Transfer Total Currency', 'Transfer Fee', 'Transfer Fee Currency',
            'Transfer Payment Method', 'Transfer ID', 'Order Price', 'Order Currency', None,
            'Order Tracking Code', 'Order Custom Parameter', 'Order Paid Out',
            'Recurring Payment ID', None, None],
           worksheet_name="Coinbase",
           row_handler=parse_coinbase_transactions)
