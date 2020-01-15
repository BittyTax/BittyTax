# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "HitBTC"

def parse_hitbtc_trades(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[4] == "buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=in_row[1].split('/')[0],
                                                 sell_quantity=Decimal(in_row[7]) - \
                                                               Decimal(in_row[9]),
                                                 sell_asset=in_row[1].split('/')[1],
                                                 fee_quantity=in_row[8],
                                                 fee_asset=in_row[1].split('/')[1],
                                                 wallet=WALLET)
    elif in_row[4] == "sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[7]) + \
                                                              Decimal(in_row[9]),
                                                 buy_asset=in_row[1].split('/')[1],
                                                 sell_quantity=in_row[5],
                                                 sell_asset=in_row[1].split('/')[0],
                                                 fee_quantity=in_row[8],
                                                 fee_asset=in_row[1].split('/')[1],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(4, parser.in_header[4], in_row[4])

def parse_hitbtc_deposits_withdrawals(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[2] == "Withdraw":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[6],
                                                 wallet=WALLET)
    elif in_row[2] == "Deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[6],
                                                 wallet=WALLET)

DataParser(DataParser.TYPE_EXCHANGE,
           "HitBTC",
           ['Date (UTC)', 'Instrument', 'Trade ID', 'Order ID', 'Side', 'Quantity', 'Price',
            'Volume', 'Fee', 'Rebate', 'Total'],
           worksheet_name="HitBTC T",
           row_handler=parse_hitbtc_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "HitBTC",
           ['Date (UTC)', 'Operation id', 'Type', 'Amount', 'Transaction Hash',
            'Main account balance'],
           worksheet_name="HitBTC D,W",
           row_handler=parse_hitbtc_deposits_withdrawals)
