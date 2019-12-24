# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Coinfloor"

def parse_coinfloor_trades(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[7] == "Buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[1],
                                                 sell_quantity=in_row[5],
                                                 sell_asset=in_row[2],
                                                 fee_quantity=in_row[6],
                                                 fee_asset=in_row[2],
                                                 wallet=WALLET)
    elif in_row[7] == "Sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=in_row[2],
                                                 sell_quantity=in_row[3],
                                                 sell_asset=in_row[1],
                                                 fee_quantity=in_row[6],
                                                 fee_asset=in_row[2],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(7, parser.in_header[7], in_row[7])

def parse_coinfloor_deposits_withdrawals(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[3] == "Deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[1],
                                                 buy_asset=in_row[2],
                                                 wallet=WALLET)
    elif in_row[3] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[1],
                                                 sell_asset=in_row[2],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(3, parser.in_header[3], in_row[3])

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinfloor Trades",
           ['Date & Time', 'Base Asset', 'Counter Asset', 'Amount', 'Price', 'Total', 'Fee',
            'Order Type'],
           worksheet_name="Coinfloor T",
           row_handler=parse_coinfloor_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinfloor Deposits/Withdrawals",
           ['Date & Time', 'Amount', 'Asset', 'Type'],
           worksheet_name="Coinfloor D,W",
           row_handler=parse_coinfloor_deposits_withdrawals)
