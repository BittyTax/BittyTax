# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Ledger Live"

def parse_ledger_live(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    # ERC-20 tokens don't include fees
    if in_row[4]:
        fee_quantity = Decimal(in_row[4])
        fee_asset = in_row[1]
        buy_fee_quantity = Decimal(in_row[4])
    else:
        fee_quantity = None
        fee_asset = ''
        buy_fee_quantity = 0

    if in_row[2] == "IN":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[3]) + \
                                                              buy_fee_quantity,
                                                 buy_asset=in_row[1],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    elif in_row[2] == "OUT":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=Decimal(in_row[3]) - \
                                                               fee_quantity,
                                                 sell_asset=in_row[1],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

DataParser(DataParser.TYPE_WALLET,
           "Ledger Live",
           ['Operation Date', 'Currency Ticker', 'Operation Type', 'Operation Amount',
            'Operation Fees', 'Operation Hash', 'Account Name', 'Account xpub'],
           worksheet_name="Ledger",
           row_handler=parse_ledger_live)

DataParser(DataParser.TYPE_WALLET,
           "Ledger Live",
           ['Operation Date', 'Currency Ticker', 'Operation Type', 'Operation Amount',
            'Operation Fees', 'Operation Hash', 'Account Name', 'Account id'],
           worksheet_name="Ledger",
           row_handler=parse_ledger_live)
