# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Bitstamp"

def parse_bitstamp(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Datetime'])

    if row_dict['Type'] in ("Ripple deposit", "Deposit"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'].split(' ')[0],
                                                 buy_asset=row_dict['Amount'].split(' ')[1],
                                                 wallet=WALLET)
    elif row_dict['Type'] in ("Ripple payment", "Withdrawal"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Amount'].split(' ')[0],
                                                 sell_asset=row_dict['Amount'].split(' ')[1],
                                                 wallet=WALLET)
    elif row_dict['Type'] == "Staking reward":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_STAKING,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'].split(' ')[0],
                                                 buy_asset=row_dict['Amount'].split(' ')[1],
                                                 wallet=WALLET)
    elif row_dict['Type'] == "Market":
        if row_dict['Fee']:
            fee_quantity = row_dict['Fee'].split(' ')[0]
            fee_asset = row_dict['Fee'].split(' ')[1]
        else:
            fee_quantity = None
            fee_asset = ''

        if row_dict['Sub Type'] == "Buy":
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Amount'].split(' ')[0],
                                                     buy_asset=row_dict['Amount'].split(' ')[1],
                                                     sell_quantity=row_dict['Value'].split(' ')[0],
                                                     sell_asset=row_dict['Value'].split(' ')[1],
                                                     fee_quantity=fee_quantity,
                                                     fee_asset=fee_asset,
                                                     wallet=WALLET)
        elif row_dict['Sub Type'] == "Sell":
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Value'].split(' ')[0],
                                                     buy_asset=row_dict['Value'].split(' ')[1],
                                                     sell_quantity=row_dict['Amount'].split(' ')[0],
                                                     sell_asset=row_dict['Amount'].split(' ')[1],
                                                     fee_quantity=fee_quantity,
                                                     fee_asset=fee_asset,
                                                     wallet=WALLET)
        else:
            raise UnexpectedTypeError(parser.in_header.index('Sub Type'), 'Sub Type',
                                      row_dict['Sub Type'])
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

DataParser(DataParser.TYPE_EXCHANGE,
           "Bitstamp",
           ['Type', 'Datetime', 'Account', 'Amount', 'Value', 'Rate', 'Fee', 'Sub Type'],
           worksheet_name="Bitstamp",
           row_handler=parse_bitstamp)
