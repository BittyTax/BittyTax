# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

HEADER = ['ID', 'Type', 'In/Out', 'Amount Fiat', 'Fee', 'Fiat', 'Amount Asset', 'Asset', 'Status',
          'Created at']

WALLET = "Bitpanda"

def parse_bitpanda(data_row, parser, **_kwargs):
    # Skip break between tables
    if len(data_row.row) < len(HEADER) or data_row.row == HEADER:
        return

    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Created at'])

    if row_dict['Status'] != "finished":
        return

    if row_dict['Type'] == "deposit":
        if Decimal(row_dict['Amount Asset']) == Decimal(0):
            buy_quantity = row_dict['Amount Fiat']
            buy_asset = row_dict['Fiat']
        else:
            buy_quantity = row_dict['Amount Asset']
            buy_asset = row_dict['Asset']

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(buy_quantity) + \
                                                              Decimal(row_dict['Fee']),
                                                 buy_asset=buy_asset,
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=buy_asset,
                                                 wallet=WALLET)
    elif row_dict['Type'] == "withdrawal":
        if Decimal(row_dict['Amount Asset']) == Decimal(0):
            sell_quantity = row_dict['Amount Fiat']
            sell_asset = row_dict['Fiat']
        else:
            sell_quantity = row_dict['Amount Asset']
            sell_asset = row_dict['Asset']

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=sell_quantity,
                                                 sell_asset=sell_asset,
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=sell_asset,
                                                 wallet=WALLET)
    elif row_dict['Type'] == "buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount Asset'],
                                                 buy_asset=row_dict['Asset'],
                                                 sell_quantity=row_dict['Amount Fiat'],
                                                 sell_asset=row_dict['Fiat'],
                                                 wallet=WALLET)
    elif row_dict['Type'] == "sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount Fiat'],
                                                 buy_asset=row_dict['Fiat'],
                                                 sell_quantity=row_dict['Amount Asset'],
                                                 sell_asset=row_dict['Asset'],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

DataParser(DataParser.TYPE_EXCHANGE,
           "Bitpanda",
           HEADER,
           worksheet_name="bitpanda",
           row_handler=parse_bitpanda)
