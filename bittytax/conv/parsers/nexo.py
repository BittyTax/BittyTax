# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Nexo"

def parse_nexo(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[6])

    if in_row[1] == "Deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[3]),
                                                 buy_asset=in_row[2],
                                                 wallet=WALLET)
    elif in_row[1] == "Interest":
        asset = in_row[2]
        # Workaround: this looks like a bug in the exporter for Nexo interest payments
        if asset == "NEXONEXO":
            asset = "NEXO"

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[3]),
                                                 buy_asset=asset,
                                                 wallet=WALLET)
    elif in_row[1] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(1, parser.in_header[1], in_row[1])

DataParser(DataParser.TYPE_WALLET,
           "Nexo",
           ['Transaction', 'Type', 'Currency', 'Amount', 'Details',
           'Outstanding Loan', 'Date / Time'],
           worksheet_name="Nexo",
           row_handler=parse_nexo)
