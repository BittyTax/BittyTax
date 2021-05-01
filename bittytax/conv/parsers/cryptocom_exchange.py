# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Crypto.com Exchange"


def parse_crypto_com_exchange(data_row, parser, filename):
    in_row = data_row.in_row
    header = parser.header
    timestamp = data_row.timestamp = DataParser.parse_timestamp(in_row[header.index('create_time_utc')]) if \
        'create_time_utc' in header else DataParser.parse_timestamp(in_row[header.index('operateTime')])
    t_type = TransactionOutRecord.TYPE_TRADE

    if 'status' in header:
        status = in_row[header.index('status')]
        if 'stake_amount' in header:
            t_type = TransactionOutRecord.TYPE_INTEREST
            quantity = in_row[header.index('interest_amount')]
            asset = in_row[header.index('interest_currency')]
            if status == '1':
                account = "STAKE_INTEREST"
            elif status == '2':
                account = "SOFT_STAKE_INTEREST"
            else:
                raise UnexpectedTypeError(header.index('status'), parser.in_header[header.index('status')],
                                          in_row[header.index('status')])
        elif 'rebate_amount' in header:
            account = "FEE_REBATE"
            t_type = TransactionOutRecord.TYPE_GIFT_RECEIVED
            quantity = in_row[header.index('rebate_amount')]
            asset = in_row[header.index('rebate_currency')]
        else:
            account = "TRANSFER"
            quantity = in_row[header.index('amount')]
            asset = in_row[header.index('currency')]
    elif 'historyInfo' in header:
        account = "SYNDICATE"
        asset = in_row[header.index('symbol')]
        quantity = Decimal(in_row[header.index('amount')])
        if "subscribe" in filename.lower():
            quantity = quantity
        elif "deliver" in filename.lower():
            quantity = -quantity
        elif "refund" in filename.lower():
            quantity = -quantity
        else:
            raise UnexpectedTypeError(header.index('historyInfo'), 'historyInfo', in_row[header.index('historyInfo')])

    else:
        account = in_row[header.index('account_type')]
        quantity = in_row[header.index('traded_quantity')]
        asset = in_row[header.index('symbol')].split('_')[0]

    if account == "TRANSFER":
        if status == '1':
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT, timestamp,
                                                     buy_quantity=quantity,
                                                     buy_asset=asset,
                                                     wallet=WALLET)
        elif status == '5':
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL, timestamp,
                                                     sell_quantity=quantity,
                                                     sell_asset=asset,
                                                     wallet=WALLET)
        else:
            raise UnexpectedTypeError(5, parser.in_header[5], in_row[5])
    elif account in ("FEE_REBATE", "STAKE_INTEREST", "SOFT_STAKE_INTEREST"):
        data_row.t_record = TransactionOutRecord(t_type, timestamp,
                                                 buy_quantity=quantity,
                                                 buy_asset=asset,
                                                 wallet=WALLET)
    elif account == "SPOT":
        fee_quantity = in_row[header.index('fee')]
        fee_asset = in_row[header.index('fee_currency')]
        traded_price = in_row[header.index('traded_price')]
        traded_quantity = Decimal(quantity) * Decimal(traded_price)
        traded_asset = in_row[header.index('symbol')].split('_')[1]
        if in_row[header.index('side')] == "BUY":
            data_row.t_record = TransactionOutRecord(t_type, timestamp,
                                                     buy_quantity=quantity,
                                                     buy_asset=asset,
                                                     sell_quantity=traded_quantity,
                                                     sell_asset=traded_asset,
                                                     # fee_quantity=fee_quantity,
                                                     # fee_asset=fee_asset,
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(t_type, timestamp,
                                                     buy_quantity=traded_quantity,
                                                     buy_asset=traded_asset,
                                                     sell_quantity=quantity,
                                                     sell_asset=asset,
                                                     # fee_quantity=fee_quantity,
                                                     # fee_asset=fee_asset,
                                                     wallet=WALLET)
    elif account == "SYNDICATE":
        if quantity < 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT, timestamp,
                                                     buy_quantity=abs(quantity),
                                                     buy_asset=asset,
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL, timestamp,
                                                     sell_quantity=quantity,
                                                     sell_asset=asset,
                                                     wallet=WALLET)
    else:
        raise UnexpectedTypeError(0, parser.in_header[0], in_row[0])


DataParser(DataParser.TYPE_EXCHANGE,
           "Crypto.com Exchange Trades",
           ['account_type', 'order_id', 'trade_id', 'create_time_utc', 'symbol', 'side', 'liquditiy_indicator',
            'traded_price', 'traded_quantity', 'fee', 'fee_currency'],
           worksheet_name="Crypto.com Exchange T",
           row_handler=parse_crypto_com_exchange)

DataParser(DataParser.TYPE_EXCHANGE,
           "Crypto.com Exchange Deposits/Withdrawals",
           ['create_time_utc', 'currency', 'amount', 'fee', 'address', 'status'],
           worksheet_name="Crypto.com Exchange D,W",
           row_handler=parse_crypto_com_exchange)

DataParser(DataParser.TYPE_EXCHANGE,
           "Crypto.com Exchange Stake Interest",
           ['create_time_utc', 'stake_currency', 'stake_amount', 'apr', 'interest_currency', 'interest_amount',
            'status'],
           worksheet_name="Crypto.com Exchange I",
           row_handler=parse_crypto_com_exchange)

DataParser(DataParser.TYPE_EXCHANGE,
           "Crypto.com Exchange Fee Rebate",
           ['create_time_utc', 'trade_fee_currency', 'trade_fee_amount', 'rebate_percentage', 'rebate_currency',
            'rebate_amount', 'rebate_destination', 'status'],
           worksheet_name="Crypto.com Exchange R",
           row_handler=parse_crypto_com_exchange)

# This one is required for a proper audit, but after one year of asking, CDC still didn't extend the export function to
# the Syndicate Details page. So I will just use the exact data harvested from the XmlHttpRequests on the exchange
# converted to csv. For example, like this:
# # pip3 install pandas
# # python3
# import pandas as pd
# for name in ('syndicate_delivered.json', 'syndicate_refunded.json', 'syndicate_subscribed.json'):
#     pd.read_json(name).to_csv(name + '.csv', index=None, header=True)
DataParser(DataParser.TYPE_EXCHANGE,
           "Crypto.com Exchange Syndicate",
           ['activityId', 'symbol', 'amount', 'historyInfo', 'operateTime', 'ctime', 'id', 'type', 'mtime', 'userId'],
           worksheet_name="Crypto.com Exchange S",
           row_handler=parse_crypto_com_exchange)
