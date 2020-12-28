# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal

from colorama import Fore

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError, UnexpectedTradingPairError, \
                         UnexpectedContentError, MissingComponentError, DataFilenameError

WALLET = "Binance"
QUOTE_ASSETS = ['BNB', 'BTC', 'BUSD', 'ETH', 'EUR', 'GBP', 'NGN', 'PAX', 'RUB', 'TRX',
                'TUSD', 'USDC', 'USDS', 'USDT', 'XRP']

def parse_binance_trades(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    base_asset, quote_asset = split_trading_pair(in_row[1])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(1, parser.in_header[1], in_row[1])

    if in_row[2] == "BUY":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=base_asset,
                                                 sell_quantity=in_row[5],
                                                 sell_asset=quote_asset,
                                                 fee_quantity=in_row[6],
                                                 fee_asset=in_row[7],
                                                 wallet=WALLET)
    elif in_row[2] == "SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=quote_asset,
                                                 sell_quantity=in_row[4],
                                                 sell_asset=base_asset,
                                                 fee_quantity=in_row[6],
                                                 fee_asset=in_row[7],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

def split_trading_pair(trading_pair):
    for quote_asset in QUOTE_ASSETS:
        if trading_pair.endswith(quote_asset):
            return trading_pair[:-len(quote_asset)], quote_asset

    return None, None

def parse_binance_deposits_withdrawals_crypto(data_row, _parser, filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[8] != "Completed":
        return

    if "deposit" in filename.lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[2],
                                                 buy_asset=in_row[1],
                                                 fee_quantity=in_row[3],
                                                 fee_asset=in_row[1],
                                                 wallet=WALLET)
    elif "withdrawal" in filename.lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[2],
                                                 sell_asset=in_row[1],
                                                 fee_quantity=in_row[3],
                                                 fee_asset=in_row[1],
                                                 wallet=WALLET)
    else:
        raise DataFilenameError(filename, "Transaction Type (Deposit or Withdrawal)")

def parse_binance_deposits_withdrawals_cash(data_row, _parser, filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[3] != "Successful":
        return

    if "deposit" in filename.lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[2],
                                                 buy_asset=in_row[1],
                                                 fee_quantity=in_row[6],
                                                 fee_asset=in_row[1],
                                                 wallet=WALLET)
    elif "withdrawal" in filename.lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[2],
                                                 sell_asset=in_row[1],
                                                 fee_quantity=in_row[6],
                                                 fee_asset=in_row[1],
                                                 wallet=WALLET)
    else:
        raise DataFilenameError(filename, "Transaction Type (Deposit or Withdrawal)")

def parse_binance_statements(data_rows, parser, _filename):
    for data_row in data_rows:
        if config.args.debug:
            sys.stderr.write("%sconv: row[%s] %s\n" % (
                Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))

        in_row = data_row.in_row
        data_row.timestamp = DataParser.parse_timestamp(in_row[0])

        if in_row[2] in ("Distribution", "Commission History"):
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[4],
                                                     buy_asset=in_row[3],
                                                     wallet=WALLET)
        elif in_row[2] == "Small assets exchange BNB":
            bnb_convert(data_rows, parser, in_row[0], in_row[2])

def bnb_convert(data_rows, parser, utc_time, operation):
    matching_rows = [data_row for data_row in data_rows
                     if data_row.in_row[0] == utc_time and data_row.in_row[2] == operation]

    bnb_found, buy_quantity = get_bnb_quantity(matching_rows, parser)

    for data_row in matching_rows:
        if not data_row.parsed:
            data_row.timestamp = DataParser.parse_timestamp(data_row.in_row[0])
            data_row.parsed = True

            if bnb_found:
                data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                         data_row.timestamp,
                                                         buy_quantity=buy_quantity,
                                                         buy_asset="BNB",
                                                         sell_quantity= \
                                                                 abs(Decimal(data_row.in_row[4])),
                                                         sell_asset=data_row.in_row[3],
                                                         wallet=WALLET)
            else:
                data_row.failure = MissingComponentError(2, parser.in_header[2], data_row.in_row[2])

def get_bnb_quantity(matching_rows, parser):
    bnb_found = False
    buy_quantity = None
    assets = 0

    for data_row in matching_rows:
        if data_row.in_row[3] == "BNB":
            data_row.timestamp = DataParser.parse_timestamp(data_row.in_row[0])
            data_row.parsed = True

            if not bnb_found:
                buy_quantity = data_row.in_row[4]
                bnb_found = True
            else:
                # Multiple BNB values?
                data_row.failure = UnexpectedContentError(3, parser.in_header[3],
                                                          data_row.in_row[3])
                buy_quantity = None
        else:
            assets += 1

    if assets > 1:
        # Multiple assets converted, BNB quantities will need to be added manually
        buy_quantity = None

    return bnb_found, buy_quantity

DataParser(DataParser.TYPE_EXCHANGE,
           "Binance Trades",
           ['Date(UTC)', 'Market', 'Type', 'Price', 'Amount', 'Total', 'Fee', 'Fee Coin'],
           worksheet_name="Binance T",
           row_handler=parse_binance_trades)

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
           ['UTC_Time', 'Account', 'Operation', 'Coin', 'Change', 'Remark'],
           worksheet_name="Binance S",
           all_handler=parse_binance_statements)
