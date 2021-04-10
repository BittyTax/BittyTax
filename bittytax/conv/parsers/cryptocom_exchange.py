# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Crypto.com Exchange"


def parse_crypto_com_exchange(data_row, parser, _filename):
    in_row = data_row.in_row
    header = parser.header
    timestamp = data_row.timestamp = DataParser.parse_timestamp(in_row[header.index('create_time_utc')])
    account = in_row[header.index('account_type')] if header.index('create_time_utc') != 0 else "TRANSFER"
    quantity = in_row[header.index('amount')] if account == "TRANSFER" else in_row[header.index('traded_quantity')]
    asset = in_row[header.index('currency')] if account == "TRANSFER" else in_row[header.index('symbol')].split('_')[0]

    if account == "TRANSFER":
        if in_row[header.index('status')] == '1':
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT, timestamp,
                                                     buy_quantity=quantity,
                                                     buy_asset=asset,
                                                     wallet=WALLET)
        else: # status is '5' for withdrawals
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL, timestamp,
                                                     sell_quantity=quantity,
                                                     sell_asset=asset,
                                                     wallet=WALLET)
    elif account == "SPOT":
        fee_quantity = in_row[header.index('fee')]
        fee_asset = in_row[header.index('fee_currency')]
        traded_price = in_row[header.index('traded_price')]
        traded_quantity = Decimal(quantity) * Decimal(traded_price)
        traded_asset = in_row[header.index('symbol')].split('_')[1]
        if in_row[header.index('side')] == "BUY":
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=quantity,
                                                     buy_asset=asset,
                                                     sell_quantity=traded_quantity,
                                                     sell_asset=traded_asset,
                                                     # fee_quantity=fee_quantity,
                                                     # fee_asset=fee_asset,
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=traded_quantity,
                                                     buy_asset=traded_asset,
                                                     sell_quantity=quantity,
                                                     sell_asset=asset,
                                                     # fee_quantity=fee_quantity,
                                                     # fee_asset=fee_asset,
                                                     wallet=WALLET)

    else:
        raise UnexpectedTypeError(0, parser.in_header[0], in_row[0])


DataParser(DataParser.TYPE_EXCHANGE,
           "Crypto.com Exchange Deposits/Withdrawals",
           ['create_time_utc', 'currency', 'amount', 'fee', 'address', 'status'],
           worksheet_name="Crypto.com Exchange D,W",
           row_handler=parse_crypto_com_exchange)

DataParser(DataParser.TYPE_EXCHANGE,
           "Crypto.com Exchange Trades",
           ['account_type', 'order_id', 'trade_id', 'create_time_utc', 'symbol', 'side', 'liquditiy_indicator', 'traded_price', 'traded_quantity', 'fee', 'fee_currency'],
           worksheet_name="Crypto.com Exchange T",
           row_handler=parse_crypto_com_exchange)
