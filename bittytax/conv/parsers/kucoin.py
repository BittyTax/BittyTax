# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "KuCoin"

def parse_kucoin_trades(data_row, parser, _filename, _args):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['tradeCreatedAt'], tz='Asia/Hong_Kong')

    if row_dict['side'] == "buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['size'],
                                                 buy_asset=row_dict['symbol'].split('-')[0],
                                                 sell_quantity=row_dict['funds'],
                                                 sell_asset=row_dict['symbol'].split('-')[1],
                                                 fee_quantity=row_dict['fee'],
                                                 fee_asset=row_dict['feeCurrency'],
                                                 wallet=WALLET)
    elif row_dict['side'] == "sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['funds'],
                                                 buy_asset=row_dict['symbol'].split('-')[1],
                                                 sell_quantity=row_dict['size'],
                                                 sell_asset=row_dict['symbol'].split('-')[0],
                                                 fee_quantity=row_dict['fee'],
                                                 fee_asset=row_dict['feeCurrency'],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('side'), 'side', row_dict['side'])

DataParser(DataParser.TYPE_EXCHANGE,
           "KuCoin",
           ['tradeCreatedAt', 'orderId', 'symbol', 'side', 'price', 'size', 'funds', 'fee',
            'liquidity', 'feeCurrency', 'orderType'],
           worksheet_name="KuCoin T",
           row_handler=parse_kucoin_trades)
