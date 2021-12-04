# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
import re
from decimal import Decimal

from colorama import Fore

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError, UnexpectedTradingPairError, \
                         DataFilenameError

WALLET = "Binance"

QUOTE_ASSETS = ['AUD', 'BIDR', 'BKRW', 'BNB', 'BRL', 'BTC', 'BUSD', 'BVND', 'DAI', 'ETH',
                'EUR', 'GBP', 'GYEN', 'IDRT', 'NGN', 'PAX', 'RUB', 'TRX', 'TRY', 'TUSD',
                'UAH', 'USDC', 'USDP', 'USDS', 'USDT', 'VAI', 'XRP', 'ZAR']

def parse_binance_trades(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date(UTC)'])

    base_asset, quote_asset = split_trading_pair(row_dict['Market'])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(parser.in_header.index('Market'), 'Market',
                                         row_dict['Market'])

    if row_dict['Type'] == "BUY":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=base_asset,
                                                 sell_quantity=row_dict['Total'],
                                                 sell_asset=quote_asset,
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=row_dict['Fee Coin'],
                                                 wallet=WALLET)
    elif row_dict['Type'] == "SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Total'],
                                                 buy_asset=quote_asset,
                                                 sell_quantity=row_dict['Amount'],
                                                 sell_asset=base_asset,
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=row_dict['Fee Coin'],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

def parse_binance_trades_statement(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date(UTC)'])
    fee_quantity, fee_asset = split_asset(row_dict['Fee'].replace(',', ''))

    if row_dict['Side'] == "BUY":
        buy_quantity, buy_asset = split_asset(row_dict['Executed'].replace(',', ''))
        sell_quantity, sell_asset = split_asset(row_dict['Amount'].replace(',', ''))

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=buy_quantity,
                                                 buy_asset=buy_asset,
                                                 sell_quantity=sell_quantity,
                                                 sell_asset=sell_asset,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    elif row_dict['Side'] == "SELL":
        buy_quantity, buy_asset = split_asset(row_dict['Amount'].replace(',', ''))
        sell_quantity, sell_asset = split_asset(row_dict['Executed'].replace(',', ''))

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=buy_quantity,
                                                 buy_asset=buy_asset,
                                                 sell_quantity=sell_quantity,
                                                 sell_asset=sell_asset,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Side'), 'Side', row_dict['Side'])

def split_trading_pair(trading_pair):
    for quote_asset in QUOTE_ASSETS:
        if trading_pair.endswith(quote_asset):
            return trading_pair[:-len(quote_asset)], quote_asset

    return None, None

def split_asset(amount):
    match = re.match(r'([\d|,]*\.\d+)(\w+)$', amount)

    if match:
        return match.group(1), match.group(2)
    return None, ''

def parse_binance_deposits_withdrawals_crypto(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(data_row.row[0])

    if row_dict['Status'] != "Completed":
        return

    if "deposit" in kwargs['filename'].lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=row_dict['Coin'],
                                                 fee_quantity=row_dict['TransactionFee'],
                                                 fee_asset=row_dict['Coin'],
                                                 wallet=WALLET)
    elif "withdraw" in kwargs['filename'].lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Amount'],
                                                 sell_asset=row_dict['Coin'],
                                                 fee_quantity=row_dict['TransactionFee'],
                                                 fee_asset=row_dict['Coin'],
                                                 wallet=WALLET)
    else:
        raise DataFilenameError(kwargs['filename'], "Transaction Type (Deposit or Withdrawal)")

def parse_binance_deposits_withdrawals_cash(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date(UTC)'])

    if row_dict['Status'] != "Successful":
        return

    if "deposit" in kwargs['filename'].lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=row_dict['Coin'],
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=row_dict['Coin'],
                                                 wallet=WALLET)
    elif "withdraw" in kwargs['filename'].lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Amount'],
                                                 sell_asset=row_dict['Coin'],
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=row_dict['Coin'],
                                                 wallet=WALLET)
    else:
        raise DataFilenameError(kwargs['filename'], "Transaction Type (Deposit or Withdrawal)")

def parse_binance_statements(data_rows, parser, **_kwargs):
    tx_times = {}
    for dr in data_rows:
        if dr.row_dict['UTC_Time'] in tx_times:
            tx_times[dr.row_dict['UTC_Time']].append(dr)
        else:
            tx_times[dr.row_dict['UTC_Time']] = [dr]

    for data_row in data_rows:
        if config.debug:
            sys.stderr.write("%sconv: row[%s] %s\n" % (
                Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))

        row_dict = data_row.row_dict
        data_row.timestamp = DataParser.parse_timestamp(row_dict['UTC_Time'])

        if row_dict['Operation'] in ("Commission History", "Referrer rebates"):
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Change'],
                                                     buy_asset=row_dict['Coin'],
                                                     wallet=WALLET)
        elif row_dict['Operation'] == "Distribution":
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_AIRDROP,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Change'],
                                                     buy_asset=row_dict['Coin'],
                                                     wallet=WALLET)
        elif row_dict['Operation'] == "Super BNB Mining":
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_MINING,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Change'],
                                                     buy_asset=row_dict['Coin'],
                                                     wallet=WALLET)
        elif row_dict['Operation'] == "Savings Interest":
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Change'],
                                                     buy_asset=row_dict['Coin'],
                                                     wallet=WALLET)
        elif row_dict['Operation'] == "POS savings interest":
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_STAKING,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Change'],
                                                     buy_asset=row_dict['Coin'],
                                                     wallet=WALLET)
        elif row_dict['Operation'] == "Small assets exchange BNB":
            bnb_rows = [dr for dr in tx_times[row_dict['UTC_Time']]
                        if dr.row_dict['Operation'] == row_dict['Operation']]
            bnb_convert(bnb_rows)
        elif row_dict['Operation'] in ("Savings purchase", "Savings Principal redemption",
                                       "POS savings purchase", "POS savings redemption"):
            # Skip not taxable events
            continue

def bnb_convert(bnb_rows):
    buy_quantity = get_bnb_quantity(bnb_rows)

    for data_row in bnb_rows:
        if not data_row.parsed:
            data_row.timestamp = DataParser.parse_timestamp(data_row.row_dict['UTC_Time'])
            data_row.parsed = True

            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=buy_quantity,
                                                     buy_asset="BNB",
                                                     sell_quantity=abs(Decimal(data_row. \
                                                         row_dict['Change'])),
                                                     sell_asset=data_row.row_dict['Coin'],
                                                     wallet=WALLET)

def get_bnb_quantity(bnb_rows):
    bnb_found = False
    buy_quantity = None
    assets = 0

    for data_row in bnb_rows:
        if data_row.row_dict['Coin'] == "BNB":
            data_row.timestamp = DataParser.parse_timestamp(data_row.row_dict['UTC_Time'])
            data_row.parsed = True

            if not bnb_found:
                buy_quantity = data_row.row_dict['Change']
                bnb_found = True
            else:
                # Multiple BNB quantities, will need to be added manually
                buy_quantity = None
        else:
            assets += 1

    if assets > 1:
        # Multiple assets converted, BNB quantities will need to be added manually
        buy_quantity = None

    return buy_quantity

DataParser(DataParser.TYPE_EXCHANGE,
           "Binance Trades",
           ['Date(UTC)', 'Market', 'Type', 'Price', 'Amount', 'Total', 'Fee', 'Fee Coin'],
           worksheet_name="Binance T",
           row_handler=parse_binance_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "Binance Trades",
           ['Date(UTC)', 'Pair', 'Side', 'Price', 'Executed', 'Amount', 'Fee'],
           worksheet_name="Binance T",
           row_handler=parse_binance_trades_statement)

DataParser(DataParser.TYPE_EXCHANGE,
           "Binance Deposits/Withdrawals",
           ['Date(UTC)', 'Coin', 'Amount', 'TransactionFee', 'Address', 'TXID', 'SourceAddress',
            'PaymentID', 'Status'],
           worksheet_name="Binance D,W",
           row_handler=parse_binance_deposits_withdrawals_crypto)

DataParser(DataParser.TYPE_EXCHANGE,
           "Binance Deposits/Withdrawals",
           ['Date', 'Coin', 'Amount', 'TransactionFee', 'Address', 'TXID', 'SourceAddress',
            'PaymentID', 'Status'],
           worksheet_name="Binance D,W",
           row_handler=parse_binance_deposits_withdrawals_crypto)

DataParser(DataParser.TYPE_EXCHANGE,
           "Binance Deposits/Withdrawals",
           ['Date(UTC)', 'Coin', 'Amount', 'Status', 'Payment Method', 'Indicated Amount', 'Fee',
            'Order ID'],
           worksheet_name="Binance D,W",
           row_handler=parse_binance_deposits_withdrawals_cash)

DataParser(DataParser.TYPE_EXCHANGE,
           "Binance Statements",
           ['User_ID', 'UTC_Time', 'Account', 'Operation', 'Coin', 'Change', 'Remark'],
           worksheet_name="Binance S",
           all_handler=parse_binance_statements)

DataParser(DataParser.TYPE_EXCHANGE,
           "Binance Statements",
           ['UTC_Time', 'Account', 'Operation', 'Coin', 'Change', 'Remark'],
           worksheet_name="Binance S",
           all_handler=parse_binance_statements)
