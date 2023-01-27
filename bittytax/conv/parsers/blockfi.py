# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import sys
from decimal import Decimal

from colorama import Fore, Back

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "BlockFi"

def parse_blockfi(data_row, parser, **kwargs):
    row_dict = data_row.row_dict

    if row_dict['Confirmed At'] == "" and not kwargs['unconfirmed']:
        sys.stderr.write("%srow[%s] %s\n" % (
            Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
        sys.stderr.write("%sWARNING%s Skipping unconfirmed transaction, "
                         "use the [-uc] option to include it\n" % (
                             Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW))
        return

    data_row.timestamp = DataParser.parse_timestamp(row_dict['Confirmed At'])

    if row_dict['Transaction Type'] in ("Deposit", "Wire Deposit", "ACH Deposit"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=row_dict['Cryptocurrency'],
                                                 wallet=WALLET)
    elif row_dict['Transaction Type'] in ("Withdrawal", "Wire Withdrawal", "ACH Withdrawal"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(row_dict['Amount'])),
                                                 sell_asset=row_dict['Cryptocurrency'],
                                                 wallet=WALLET)
    elif row_dict['Transaction Type'] == "Withdrawal Fee":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=0,
                                                 sell_asset=row_dict['Cryptocurrency'],
                                                 fee_quantity=abs(Decimal(row_dict['Amount'])),
                                                 fee_asset=row_dict['Cryptocurrency'],
                                                 wallet=WALLET)
    elif row_dict['Transaction Type'] == "Interest Payment":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=row_dict['Cryptocurrency'],
                                                 wallet=WALLET)
    elif row_dict['Transaction Type'] in ("Bonus Payment", "Referral Bonus"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=row_dict['Cryptocurrency'],
                                                 wallet=WALLET)
    elif row_dict['Transaction Type'] == "Trade":
        # Skip trades
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index('Transaction Type'), 'Transaction Type',
                                  row_dict['Transaction Type'])

def parse_blockfi_trades(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date'])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                             data_row.timestamp,
                                             buy_quantity=row_dict['Buy Quantity'],
                                             buy_asset=row_dict['Buy Currency'].upper(),
                                             sell_quantity=abs(Decimal(row_dict['Sold Quantity'])),
                                             sell_asset=row_dict['Sold Currency'].upper(),
                                             wallet=WALLET)

DataParser(DataParser.TYPE_SAVINGS,
           "BlockFi",
           ['Cryptocurrency', 'Amount', 'Transaction Type', 'Confirmed At'],
           worksheet_name="BlockFi",
           row_handler=parse_blockfi)

DataParser(DataParser.TYPE_SAVINGS,
           "BlockFi Trades",
           ['Trade ID', 'Date', 'Buy Quantity', 'Buy Currency', 'Sold Quantity', 'Sold Currency',
            'Rate Amount', 'Rate Currency', 'Type'],
           worksheet_name="BlockFi T",
           row_handler=parse_blockfi_trades)
