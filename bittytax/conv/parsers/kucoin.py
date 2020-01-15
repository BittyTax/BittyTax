# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "KuCoin"

def parse_kucoin_trades(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0], tz='Asia/Hong_Kong')

    if in_row[3] == "buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=in_row[2].split('-')[0],
                                                 sell_quantity=in_row[6],
                                                 sell_asset=in_row[2].split('-')[1],
                                                 fee_quantity=in_row[7],
                                                 fee_asset=in_row[9],
                                                 wallet=WALLET)
    elif in_row[3] == "sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[6],
                                                 buy_asset=in_row[2].split('-')[1],
                                                 sell_quantity=in_row[5],
                                                 sell_asset=in_row[2].split('-')[0],
                                                 fee_quantity=in_row[7],
                                                 fee_asset=in_row[9],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(3, parser.in_header[3], in_row[3])

DataParser(DataParser.TYPE_EXCHANGE,
           "KuCoin",
           ['tradeCreatedAt', 'orderId', 'symbol', 'side', 'price', 'size', 'funds', 'fee',
            'liquidity', 'feeCurrency', 'orderType'],
           worksheet_name="KuCoin T",
           row_handler=parse_kucoin_trades)
