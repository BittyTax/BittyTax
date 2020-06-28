# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Bitfinex"

PRECISION = Decimal('0.00000000')

def parse_bitfinex_trades(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[6], dayfirst=True)

    if Decimal(in_row[2]) > 0:
        sell_quantity = Decimal(in_row[3]) * Decimal(in_row[2])

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[2],
                                                 buy_asset=in_row[1].split('/')[0],
                                                 sell_quantity=sell_quantity.quantize(PRECISION),
                                                 sell_asset=in_row[1].split('/')[1],
                                                 fee_quantity=abs(Decimal(in_row[4])),
                                                 fee_asset=in_row[5],
                                                 wallet=WALLET)
    else:
        buy_quantity = Decimal(in_row[3]) * abs(Decimal(in_row[2]))

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=buy_quantity.quantize(PRECISION),
                                                 buy_asset=in_row[1].split('/')[1],
                                                 sell_quantity=abs(Decimal(in_row[2])),
                                                 sell_asset=in_row[1].split('/')[0],
                                                 fee_quantity=abs(Decimal(in_row[4])),
                                                 fee_asset=in_row[5],
                                                 wallet=WALLET)

def parse_bitfinex_deposits_withdrawals(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[1], dayfirst=True)

    if in_row[3] != "COMPLETED":
        return

    if Decimal(in_row[4]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=in_row[2],
                                                 fee_quantity=abs(Decimal(in_row[5])),
                                                 fee_asset=in_row[2],
                                                 wallet=WALLET)
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[4])),
                                                 sell_asset=in_row[2],
                                                 fee_quantity=abs(Decimal(in_row[5])),
                                                 fee_asset=in_row[2],
                                                 wallet=WALLET)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bitfinex Trades",
           ['#', 'PAIR', 'AMOUNT', 'PRICE', 'FEE', 'FEE CURRENCY', 'DATE', 'ORDER ID'],
           worksheet_name="Bitfinex T",
           row_handler=parse_bitfinex_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "Bitfinex Deposits/Withdrawals",
           ['#', 'DATE', 'CURRENCY', 'STATUS', 'AMOUNT', 'FEES', 'DESCRIPTION', 'TRANSACTION ID'],
           worksheet_name="Bitfinex D,W",
           row_handler=parse_bitfinex_deposits_withdrawals)
