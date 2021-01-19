# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "BlockFi"

def parse_blockfi(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[3])

    if in_row[2] == "Deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[1]),
                                                 buy_asset=in_row[0],
                                                 wallet=WALLET)
    elif in_row[2] == "Interest Payment":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[1]),
                                                 buy_asset=in_row[0],
                                                 wallet=WALLET)
    elif in_row[2] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[1])),
                                                 sell_asset=in_row[0],
                                                 wallet=WALLET)
    elif in_row[2] == "Trade":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[1])),
                                                 sell_asset=in_row[0],
                                                 wallet=WALLET)
    elif in_row[2] == "Bonus Payment":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INCOME,     
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[1])),
                                                 sell_asset=in_row[0],
                                                 wallet=WALLET)
    elif in_row[2] == "Withdrawal Fee":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[1])),
                                                 sell_asset=in_row[0],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(1, parser.in_header[1], in_row[2])

DataParser(DataParser.TYPE_WALLET,
           "BlockFi",
		['Cryptocurrency', 'Amount', 'Transaction Type', 'Confirmed At'],
           worksheet_name="BlockFi",
           row_handler=parse_blockfi)
