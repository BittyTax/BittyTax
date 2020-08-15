# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataParserError, UnexpectedTypeError, MissingComponentError

WALLET = "Coinbase Pro"

def parse_coinbase_pro(data_rows, parser, _filename):
    for data_row in data_rows:
        if data_row.parsed:
            continue

        try:
            parse_coinbase_pro_row(data_rows, parser, data_row)
        except DataParserError as e:
            data_row.failure = e

def parse_coinbase_pro_row(data_rows, parser, data_row):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[2])
    data_row.parsed = True

    if in_row[1] == "withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[5],
                                                 wallet=WALLET)
    elif in_row[1] == "deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[5],
                                                 wallet=WALLET)
    elif in_row[1] == "match":
        if Decimal(in_row[3]) < 0:
            sell_quantity = abs(Decimal(in_row[3]))
            sell_asset = in_row[5]

            buy_quantity, buy_asset = find_same_trade(data_rows, in_row[7], "match")
        else:
            buy_quantity = in_row[3]
            buy_asset = in_row[5]

            sell_quantity, sell_asset = find_same_trade(data_rows, in_row[7], "match")

        if sell_quantity is None or buy_quantity is None:
            raise MissingComponentError(7, parser.in_header[7], in_row[7])

        fee_quantity, fee_asset = find_same_trade(data_rows, in_row[7], "fee")

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=buy_quantity,
                                                 buy_asset=buy_asset,
                                                 sell_quantity=sell_quantity,
                                                 sell_asset=sell_asset,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(1, parser.in_header[1], in_row[1])

def find_same_trade(data_rows, trade_id, t_type):
    quantity = None
    asset = ""

    data_rows = [data_row for data_row in data_rows
                 if data_row.in_row[7] == trade_id and not data_row.parsed]
    for data_row in data_rows:
        if t_type == data_row.in_row[1]:
            quantity = abs(Decimal(data_row.in_row[3]))
            asset = data_row.in_row[5]
            data_row.timestamp = DataParser.parse_timestamp(data_row.in_row[2])
            data_row.parsed = True
            break

    return quantity, asset

def parse_coinbase_pro_deposits_withdrawals(data_row, parser, _filename):
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

def parse_coinbase_pro_trades(data_row, parser, _filename):
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
           "Coinbase Pro",
           ['portfolio', 'type', 'time', 'amount', 'balance', 'amount/balance unit', 'transfer id',
            'trade id', 'order id'],
           worksheet_name="Coinbase Pro",
           all_handler=parse_coinbase_pro)

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
