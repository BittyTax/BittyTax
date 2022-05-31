# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Mercatox"

def parse_mercatox(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Time'])

    if row_dict['Type'] == "Deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=row_dict['Currency'],
                                                 wallet=WALLET)
    elif row_dict['Type'] == "Withdraw":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Amount'],
                                                 sell_asset=row_dict['Currency'],
                                                 fee_quantity=row_dict['Fee'],
                                                 fee_asset=row_dict['Currency'],
                                                 wallet=WALLET)
    elif row_dict['Type'] == "Deal":
        if row_dict['Action'] == "buy":
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Amount'],
                                                     buy_asset=row_dict['Pair'].split('/')[0],
                                                     sell_quantity=row_dict['Total'],
                                                     sell_asset=row_dict['Pair'].split('/')[1],
                                                     wallet=WALLET)
        elif row_dict['Action'] == "sell":
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Total'],
                                                     buy_asset=row_dict['Pair'].split('/')[1],
                                                     sell_quantity=row_dict['Amount'],
                                                     sell_asset=row_dict['Pair'].split('/')[0],
                                                     wallet=WALLET)
        else:
            raise UnexpectedTypeError(parser.in_header.index('Action'), 'Action',
                                      row_dict['Action'])
    elif row_dict['Type'] == "Promo":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_AIRDROP,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=row_dict['Currency'],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

DataParser(DataParser.TYPE_EXCHANGE,
           "Mercatox",
           ['MX Transaction Id', 'NT Transaction Id', 'Withdraw addr', 'Type', 'Currency', 'Pair',
            'Fee', 'Amount', 'Price', 'Total', 'Action', 'From', 'To', 'Time'],
           worksheet_name="Mercatox",
           row_handler=parse_mercatox)
