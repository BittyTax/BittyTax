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

def parse_cointracking(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[12])

    if in_row[0] == "Trade":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[1],
                                                 buy_asset=in_row[2],
                                                 buy_value=in_row[4],
                                                 sell_quantity=in_row[5],
                                                 sell_asset=in_row[6],
                                                 sell_value=in_row[8],
                                                 wallet=wallet_name(in_row[10]))
    elif in_row[0] in ("Gift/Tip", "Income", "Mining"):
        data_row.t_record = TransactionOutRecord(map_type(in_row[0]),
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[1],
                                                 buy_asset=in_row[2],
                                                 buy_value=in_row[4],
                                                 wallet=wallet_name(in_row[10]))
    elif in_row[0] in ("Lost", "Stolen"):
        # No direct mapping, map as a trade for 0 GBP
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=0,
                                                 buy_asset=config.CCY,
                                                 sell_quantity=in_row[5],
                                                 sell_asset=in_row[6],
                                                 wallet=wallet_name(in_row[10]))
    elif in_row[0] in ("Spend", "Gift", "Donation"):
        data_row.t_record = TransactionOutRecord(map_type(in_row[0]),
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[5],
                                                 sell_asset=in_row[6],
                                                 sell_value=in_row[8],
                                                 wallet=wallet_name(in_row[10]))
    elif in_row[0] == "Deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[1],
                                                 buy_asset=in_row[2],
                                                 wallet=wallet_name(in_row[10]))
    elif in_row[0] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[5],
                                                 sell_asset=in_row[6],
                                                 wallet=wallet_name(in_row[10]))
    else:
        raise UnexpectedTypeError(0, parser.in_header[0], in_row[0])

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
