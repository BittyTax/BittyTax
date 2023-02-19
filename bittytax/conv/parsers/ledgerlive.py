# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Ledger Live"

AMOUNT = 'Operation Amount'
FEES = 'Operation Fees'

def parse_ledger_live(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Operation Date'])

    if row_dict['Operation Type'] == "IN":
        if row_dict['Operation Fees']:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=Decimal(row_dict[AMOUNT]) +
                                                     Decimal(row_dict[FEES]),
                                                     buy_asset=row_dict['Currency Ticker'],
                                                     fee_quantity=row_dict['Operation Fees'],
                                                     fee_asset=row_dict['Currency Ticker'],
                                                     wallet=WALLET)
        else:
            # ERC-20 tokens don't include fees
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Operation Amount'],
                                                     buy_asset=row_dict['Currency Ticker'],
                                                     wallet=WALLET)
    elif row_dict['Operation Type'] == "OUT":
        if row_dict['Operation Fees']:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                     data_row.timestamp,
                                                     sell_quantity=Decimal(row_dict[AMOUNT]) -
                                                     Decimal(row_dict[FEES]),
                                                     sell_asset=row_dict['Currency Ticker'],
                                                     fee_quantity=row_dict['Operation Fees'],
                                                     fee_asset=row_dict['Currency Ticker'],
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                     data_row.timestamp,
                                                     sell_quantity=row_dict['Operation Amount'],
                                                     sell_asset=row_dict['Currency Ticker'],
                                                     wallet=WALLET)
    elif row_dict['Operation Type'] in ("FEES", "REVEAL"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=Decimal(row_dict[AMOUNT]) -
                                                 Decimal(row_dict[FEES]),
                                                 sell_asset=row_dict['Currency Ticker'],
                                                 fee_quantity=row_dict['Operation Fees'],
                                                 fee_asset=row_dict['Currency Ticker'],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Operation Type'), 'Operation Type',
                                  row_dict['Operation Type'])

DataParser(DataParser.TYPE_WALLET,
           "Ledger Live",
           ['Operation Date', 'Currency Ticker', 'Operation Type', 'Operation Amount',
            'Operation Fees', 'Operation Hash', 'Account Name', 'Account xpub',
            'Countervalue Ticker', 'Countervalue at Operation Date', 'Countervalue at CSV Export'],
           worksheet_name="Ledger",
           row_handler=parse_ledger_live)

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
