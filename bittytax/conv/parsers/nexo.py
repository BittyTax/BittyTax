# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import sys
from decimal import Decimal

from colorama import Fore, Back

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Nexo"

def parse_nexo(data_row, parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date / Time'])

    if "rejected" in row_dict['Details'] and not kwargs['unconfirmed']:
        sys.stderr.write("%srow[%s] %s\n" % (
            Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
        sys.stderr.write("%sWARNING%s Skipping unconfirmed transaction, "
                         "use the [-uc] option to include it\n" % (
                             Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW))
        return


    # Workaround: this looks like a bug in the exporter
    asset = row_dict['Currency'].replace('NEXONEXO', 'NEXO')

    if row_dict['Type'] in ("Deposit", "ExchangeDepositedOn"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=asset,
                                                 wallet=WALLET)
    elif row_dict['Type'] == "Interest":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=asset,
                                                 wallet=WALLET)
    elif row_dict['Type'] == "Bonus":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=asset,
                                                 wallet=WALLET)

    elif row_dict['Type'] in ("Withdrawal", "WithdrawExchanged"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(row_dict['Amount'])),
                                                 sell_asset=asset,
                                                 wallet=WALLET)
    elif row_dict['Type'] in ("DepositToExchange", "ExchangeToWithdraw",
                              "TransferIn", "TransferOut"):
        # Skip internal
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

DataParser(DataParser.TYPE_SAVINGS,
           "Nexo",
           ['Transaction', 'Type', 'Currency', 'Amount', 'Details', 'Outstanding Loan',
            'Date / Time'],
           worksheet_name="Nexo",
           row_handler=parse_nexo)
