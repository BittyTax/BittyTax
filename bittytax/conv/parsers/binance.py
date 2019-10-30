# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ...record import TransactionRecordBase as TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Binance"

def parse_binance_trades(data_row, parser):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[2] == "BUY":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=in_row[7],
                                                 sell_quantity=in_row[5],
                                                 sell_asset=in_row[1].replace(in_row[7], ''),
                                                 fee_quantity=in_row[6],
                                                 fee_asset=in_row[7],
                                                 wallet=WALLET)
    elif in_row[2] == "SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=in_row[7],
                                                 sell_quantity=in_row[4],
                                                 sell_asset=in_row[1].replace(in_row[7], ''),
                                                 fee_quantity=in_row[6],
                                                 fee_asset=in_row[7],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

def parse_binance_deposits_withdrawals(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[8] != "Completed":
        return

    # Assume that a transaction fee of 0 must be a Deposit
    if Decimal(in_row[3]) == 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[2],
                                                 buy_asset=in_row[1],
                                                 wallet=WALLET)
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[2],
                                                 sell_asset=in_row[1],
                                                 fee_quantity=in_row[3],
                                                 fee_asset=in_row[1],
                                                 wallet=WALLET)

DataParser(DataParser.TYPE_EXCHANGE,
           "Binance Trades",
           ['Date(UTC)', 'Market', 'Type', 'Price', 'Amount', 'Total', 'Fee', 'Fee Coin'],
           worksheet_name="Binance T",
           row_handler=parse_binance_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "Binance Deposits/Withdrawals",
           ['Date', 'Coin', 'Amount', 'TransactionFee', 'Address', 'TXID', 'SourceAddress',
            'PaymentID', 'Status'],
           worksheet_name="Binance D,W",
           row_handler=parse_binance_deposits_withdrawals)
