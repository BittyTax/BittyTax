# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "TradeSatoshi"

def parse_tradesatoshi_deposits2(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                             data_row.timestamp,
                                             buy_quantity=in_row[3],
                                             buy_asset=in_row[2],
                                             wallet=WALLET)

def parse_tradesatoshi_deposits(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[7])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                             data_row.timestamp,
                                             buy_quantity=in_row[3],
                                             buy_asset=in_row[2],
                                             wallet=WALLET)

def parse_tradesatoshi_withdrawals2(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                             data_row.timestamp,
                                             sell_quantity=Decimal(in_row[3]),
                                             sell_asset=in_row[2],
                                             wallet=WALLET)

def parse_tradesatoshi_withdrawals(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[10])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                             data_row.timestamp,
                                             sell_quantity=Decimal(in_row[3]) - \
                                                           Decimal(in_row[4]),
                                             sell_asset=in_row[2],
                                             fee_quantity=in_row[4],
                                             fee_asset=in_row[2],
                                             wallet=WALLET)

def parse_tradesatoshi_trades(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[6])

    if in_row[2] == "Buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[1].split('/')[0],
                                                 sell_quantity=Decimal(in_row[3]) * \
                                                               Decimal(in_row[4]),
                                                 sell_asset=in_row[1].split('/')[1],
                                                 fee_quantity=in_row[5],
                                                 fee_asset=in_row[1].split('/')[1],
                                                 wallet=WALLET)
    elif in_row[2] == "Sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[3]) * \
                                                              Decimal(in_row[4]),
                                                 buy_asset=in_row[1].split('/')[1],
                                                 sell_quantity=in_row[3],
                                                 sell_asset=in_row[1].split('/')[0],
                                                 fee_quantity=in_row[5],
                                                 fee_asset=in_row[1].split('/')[1],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

DataParser(DataParser.TYPE_EXCHANGE,
           "TradeSatoshi Deposits",
           ['TimeStamp', 'Currency', 'Symbol', 'Amount', 'Confirmation', 'TxId'],
           worksheet_name="TradeSatoshi D",
           row_handler=parse_tradesatoshi_deposits2)

DataParser(DataParser.TYPE_EXCHANGE,
           "TradeSatoshi Deposits",
           ['Id', 'Currency', 'Symbol', 'Amount', 'Status', 'Confirmations', 'TxId', 'TimeStamp'],
           worksheet_name="TradeSatoshi D",
           row_handler=parse_tradesatoshi_deposits)

DataParser(DataParser.TYPE_EXCHANGE,
           "TradeSatoshi Withdrawals",
           ['TimeStamp', 'Currency', 'Symbol', 'Amount', 'Confirmation', 'TxId', 'Address',
            'PaymentId', 'Status'],
           worksheet_name="TradeSatoshi W",
           row_handler=parse_tradesatoshi_withdrawals2)

DataParser(DataParser.TYPE_EXCHANGE,
           "TradeSatoshi Withdrawals",
           ['Id', 'User', 'Symbol', 'Amount', 'Fee', 'Net Amount', 'Status', 'Confirmations',
            'TxId', 'Address', 'TimeStamp'],
           worksheet_name="TradeSatoshi W",
           row_handler=parse_tradesatoshi_withdrawals)

DataParser(DataParser.TYPE_EXCHANGE,
           "TradeSatoshi Trades",
           ['Id', 'TradePair', lambda c: c in ('TradeType', 'TradeHistoryType'), 'Amount', 'Rate',
            'Fee', lambda c: c.lower() == 'timestamp', 'IsApi'],
           worksheet_name="TradeSatoshi T",
           row_handler=parse_tradesatoshi_trades)
