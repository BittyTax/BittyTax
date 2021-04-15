# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "CoinTracking"

COINTRACKING_TYPE_MAPPING = {'Trade': TransactionOutRecord.TYPE_TRADE,
                             'Deposit': TransactionOutRecord.TYPE_DEPOSIT,
                             'Income': TransactionOutRecord.TYPE_INCOME,
                             'Mining': TransactionOutRecord.TYPE_MINING,
                             'Gift/Tip': TransactionOutRecord.TYPE_GIFT_RECEIVED,
                             'Withdrawal': TransactionOutRecord.TYPE_WITHDRAWAL,
                             'Spend': TransactionOutRecord.TYPE_SPEND,
                             'Donation': TransactionOutRecord.TYPE_CHARITY_SENT,
                             'Gift': TransactionOutRecord.TYPE_GIFT_SENT,
                             'Stolen': TransactionOutRecord.TYPE_TRADE,
                             'Lost': TransactionOutRecord.TYPE_TRADE}

def parse_cointracking(data_row, parser, _filename, _args):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date'], dayfirst=True)

    if row_dict['Type'] == "Trade":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Buy'],
                                                 buy_asset=data_row.row[2],
                                                 buy_value=data_row.row[4],
                                                 sell_quantity=row_dict['Sell'],
                                                 sell_asset=data_row.row[6],
                                                 sell_value=data_row.row[8],
                                                 wallet=wallet_name(row_dict['Exchange']))
    elif row_dict['Type'] in ("Gift/Tip", "Income", "Mining"):
        data_row.t_record = TransactionOutRecord(map_type(row_dict['Type']),
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Buy'],
                                                 buy_asset=data_row.row[2],
                                                 buy_value=data_row.row[4],
                                                 wallet=wallet_name(row_dict['Exchange']))
    elif row_dict['Type'] in ("Lost", "Stolen"):
        # No direct mapping, map as a trade for 0 GBP
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=0,
                                                 buy_asset=config.ccy,
                                                 sell_quantity=row_dict['Sell'],
                                                 sell_asset=data_row.row[6],
                                                 wallet=wallet_name(row_dict['Exchange']))
    elif row_dict['Type'] in ("Spend", "Gift", "Donation"):
        data_row.t_record = TransactionOutRecord(map_type(row_dict['Type']),
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Sell'],
                                                 sell_asset=data_row.row[6],
                                                 sell_value=data_row.row[8],
                                                 wallet=wallet_name(row_dict['Exchange']))
    elif row_dict['Type'] == "Deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Buy'],
                                                 buy_asset=data_row.row[2],
                                                 wallet=wallet_name(row_dict['Exchange']))
    elif row_dict['Type'] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Sell'],
                                                 sell_asset=data_row.row[6],
                                                 wallet=wallet_name(row_dict['Exchange']))
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

def wallet_name(wallet):
    if not wallet:
        return WALLET
    return wallet

def map_type(t_type):
    return COINTRACKING_TYPE_MAPPING[t_type]

DataParser(DataParser.TYPE_ACCOUNTING,
           "CoinTracking",
           ['Type', 'Buy', 'Cur.', 'Value in BTC', 'Value in GBP', 'Sell', 'Cur.', 'Value in BTC',
            'Value in GBP', 'Spread', 'Exchange', 'Group', 'Date'],
           worksheet_name="CoinTracking",
           row_handler=parse_cointracking)
