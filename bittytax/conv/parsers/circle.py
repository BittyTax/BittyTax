# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ...config import config
from ..out_record import TransactionOutRecord as TxOutRec
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Circle"

def parse_circle(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date'])

    if row_dict['Transaction Type'] in ("deposit", "internal_switch_currency", "switch_currency"):
        data_row.t_record = TxOutRec(TxOutRec.TYPE_TRADE,
                                     data_row.timestamp,
                                     buy_quantity=row_dict['To Amount'].strip('£€$').split(' ')[0],
                                     buy_asset=row_dict['To Currency'],
                                     sell_quantity=row_dict['From Amount'].strip('£€$').
                                     split(' ')[0],
                                     sell_asset=row_dict['From Currency'],
                                     wallet=WALLET)
    elif row_dict['Transaction Type'] == "spend":
        data_row.t_record = TxOutRec(TxOutRec.TYPE_WITHDRAWAL,
                                     data_row.timestamp,
                                     sell_quantity=row_dict['From Amount'].strip('£€$').
                                     split(' ')[0],
                                     sell_asset=row_dict['From Currency'],
                                     sell_value=row_dict['To Amount'].strip('£€$')
                                     if row_dict['To Currency'] == config.ccy else None,
                                     wallet=WALLET)
    elif row_dict['Transaction Type'] == "receive":
        data_row.t_record = TxOutRec(TxOutRec.TYPE_DEPOSIT,
                                     data_row.timestamp,
                                     buy_quantity=row_dict['To Amount'].strip('£€$').split(' ')[0],
                                     buy_asset=row_dict['To Currency'],
                                     buy_value=row_dict['From Amount'].strip('£€$')
                                     if row_dict['From Currency'] == config.ccy else None,
                                     wallet=WALLET)
    elif row_dict['Transaction Type'] == "fork":
        data_row.t_record = TxOutRec(TxOutRec.TYPE_AIRDROP,
                                     data_row.timestamp,
                                     buy_quantity=row_dict['To Amount'].strip('£€$').split(' ')[0],
                                     buy_asset=row_dict['To Currency'],
                                     buy_value=0,
                                     wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Transaction Type'), 'Transaction Type',
                                  row_dict['Transaction Type'])

DataParser(DataParser.TYPE_EXCHANGE,
           "Circle",
           ['Date', 'Reference ID', 'Transaction Type', 'From Account', 'To Account',
            'From Amount', 'From Currency', 'To Amount', 'To Currency', 'Status'],
           worksheet_name="Circle",
           row_handler=parse_circle)
