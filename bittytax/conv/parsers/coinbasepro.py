# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Coinbase Pro"

def parse_coinbase_pro_deposits_withdrawals(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[1])

    if in_row[0] == "withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[2])),
                                                 sell_asset=in_row[4],
                                                 wallet=WALLET)
    elif in_row[0] == "deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[2],
                                                 buy_asset=in_row[4],
                                                 wallet=WALLET)
    elif in_row[0] in ("match", "fee"):
        # Skip trades
        return
    else:
        raise UnexpectedTypeError(0, parser.in_header[0], in_row[0])

def parse_coinbase_pro_trades(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[3])

    if in_row[2] == "BUY":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=in_row[5],
                                                 sell_quantity=abs(Decimal(in_row[8])) - \
                                                               Decimal(in_row[7]),
                                                 sell_asset=in_row[9],
                                                 fee_quantity=in_row[7],
                                                 fee_asset=in_row[9],
                                                 wallet=WALLET)
    elif in_row[2] == "SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[8],
                                                 buy_asset=in_row[9],
                                                 sell_quantity=in_row[4],
                                                 sell_asset=in_row[5],
                                                 fee_quantity=in_row[7],
                                                 fee_asset=in_row[9],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase Pro Deposits/Withdrawals",
           ['type', 'time', 'amount', 'balance', 'amount/balance unit', 'transfer id', 'trade id',
            'order id'],
           worksheet_name="Coinbase Pro D,W",
           row_handler=parse_coinbase_pro_deposits_withdrawals)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase Pro Trades",
           ['trade id', 'product', 'side', 'created at', 'size', 'size unit', 'price', 'fee',
            'total', 'price/fee/total unit'],
           worksheet_name="Coinbase Pro T",
           row_handler=parse_coinbase_pro_trades)
