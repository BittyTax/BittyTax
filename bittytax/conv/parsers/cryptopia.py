# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Cryptopia"

def parse_cryptopia_deposits(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[7])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                             data_row.timestamp,
                                             buy_quantity=in_row[2],
                                             buy_asset=in_row[1],
                                             wallet=WALLET)

def parse_cryptopia_withdrawals(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[7])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                             data_row.timestamp,
                                             sell_quantity=Decimal(in_row[2]) - Decimal(in_row[3]),
                                             sell_asset=in_row[1],
                                             fee_quantity=in_row[3],
                                             fee_asset=in_row[1],
                                             wallet=WALLET)

def parse_cryptopia_trades(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[7])

    if in_row[2] == "Buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=in_row[1].split('/')[0],
                                                 sell_quantity=Decimal(in_row[3]) * \
                                                               Decimal(in_row[4]),
                                                 sell_asset=in_row[1].split('/')[1],
                                                 fee_quantity=in_row[6],
                                                 fee_asset=in_row[1].split('/')[0],
                                                 wallet=WALLET)
    elif in_row[2] == "Sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[3]) * \
                                                              Decimal(in_row[4]),
                                                 buy_asset=in_row[1].split('/')[1],
                                                 sell_quantity=in_row[4],
                                                 sell_asset=in_row[1].split('/')[0],
                                                 fee_quantity=in_row[6],
                                                 fee_asset=in_row[1].split('/')[1],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

DataParser(DataParser.TYPE_EXCHANGE,
           "Cryptopia Deposits",
           ['#', 'Currency', 'Amount', 'Status', 'Type', 'Transaction', 'Conf.', 'Timestamp'],
           worksheet_name="Cryptopia D",
           row_handler=parse_cryptopia_deposits)

DataParser(DataParser.TYPE_EXCHANGE,
           "Cryptopia Withdrawals",
           ['#', 'Currency', 'Amount', 'Fee', 'Status', 'TransactionId', 'Address', 'Timestamp'],
           worksheet_name="Cryptopia W",
           row_handler=parse_cryptopia_withdrawals)

DataParser(DataParser.TYPE_EXCHANGE,
           "Cryptopia Trades",
           ['#', 'Market', 'Type', 'Rate', 'Amount', 'Total', 'Fee', 'Timestamp'],
           worksheet_name="Cryptopia T",
           row_handler=parse_cryptopia_trades)
