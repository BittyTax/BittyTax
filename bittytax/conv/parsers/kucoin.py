# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "KuCoin"

def parse_kucoin_trades(data_row, parser, _filename):
    in_row = data_row.in_row
    header = parser.header
    data_row.timestamp = DataParser.parse_timestamp(in_row[header.index('tradeCreatedAt') if 'tradeCreatedAt' in header else header.index('createdDate')], tz='Asia/Hong_Kong')
    action = in_row[header.index('side') if 'side' in header else header.index('direction')].lower()
    quantity = in_row[header.index('size') if 'size' in header else header.index('amount')]
    asset = in_row[header.index('symbol')].split('-')[0]
    to_asset = in_row[header.index('symbol')].split('-')[1]
    to_quantity = in_row[header.index('funds') if 'funds' in header else header.index('dealValue')]
    fee_quantity = in_row[header.index('fee')]
    fee_asset = in_row[header.index('feeCurrency')] if 'feeCurrency' in header else asset if action == "buy" else to_asset

    if action == "buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=quantity,
                                                 buy_asset=asset,
                                                 sell_quantity=to_quantity,
                                                 sell_asset=to_asset,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    elif action == "sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=to_quantity,
                                                 buy_asset=to_asset,
                                                 sell_quantity=quantity,
                                                 sell_asset=asset,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    else:
        row_idx = header.index('side') if 'side' in header else header.index('direction')
        raise UnexpectedTypeError(row_idx, parser.in_header[row_idx], action)


def parse_kucoin_deposits_withdrawals(data_row, parser, _filename):
    in_row = data_row.in_row
    header = parser.header
    data_row.timestamp = DataParser.parse_timestamp(in_row[header.index('Time')], tz='Asia/Hong_Kong')
    quantity = in_row[header.index('Amount')]
    asset = in_row[header.index('Coin')]

    if 'Wallet Address' not in header:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=quantity,
                                                 buy_asset=asset,
                                                 wallet=WALLET)
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=quantity,
                                                 sell_asset=asset,
                                                 wallet=WALLET)


DataParser(DataParser.TYPE_EXCHANGE,
           "KuCoin Trades 2020",
           ['tradeCreatedAt', 'orderId', 'symbol', 'side', 'price', 'size', 'funds', 'fee',
            'liquidity', 'feeCurrency', 'orderType'],
           worksheet_name="KuCoin T",
           row_handler=parse_kucoin_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "KuCoin Trades 2021",
           ['oid', 'symbol', 'dealPrice', 'dealValue', 'amount', 'fee', 'direction', 'createdDate', ''],
           worksheet_name="KuCoin T",
           row_handler=parse_kucoin_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "KuCoin Deposits",
           ['Time', 'Coin', 'Amount', 'Type', 'Remark'],
           worksheet_name="KuCoin D",
           row_handler=parse_kucoin_deposits_withdrawals)

DataParser(DataParser.TYPE_EXCHANGE,
           "KuCoin Withdrawals",
           ['Time', 'Coin', 'Amount', 'Type', 'Wallet Address', 'Remark'],
           worksheet_name="KuCoin W",
           row_handler=parse_kucoin_deposits_withdrawals)
