# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

from decimal import Decimal

from ..out_record import TransactionOutRecord as TxOutRec
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Yoroi"
TYPE = 'Type (Trade, IN or OUT)'

def parse_yoroi(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date'])

    if row_dict[TYPE] == "Deposit":
        if row_dict['Comment (optional)'].startswith("Staking Reward"):
            t_type = TxOutRec.TYPE_STAKING
        else:
            t_type = TxOutRec.TYPE_DEPOSIT

        data_row.t_record = TxOutRec(t_type,
                                     data_row.timestamp,
                                     buy_quantity=row_dict['Buy Amount'],
                                     buy_asset=row_dict['Buy Cur.'],
                                     wallet=WALLET,
                                     note=row_dict['Comment (optional)'])

    elif row_dict[TYPE] == "Withdrawal":
        if Decimal(row_dict['Sell Amount']) == 0:
            t_type = TxOutRec.TYPE_SPEND
        else:
            t_type = TxOutRec.TYPE_WITHDRAWAL

        data_row.t_record = TxOutRec(t_type,
                                     data_row.timestamp,
                                     sell_quantity=row_dict['Sell Amount'],
                                     sell_asset=row_dict['Sell Cur.'],
                                     fee_quantity=row_dict['Fee Amount (optional)'],
                                     fee_asset=row_dict['Fee Cur. (optional)'],
                                     wallet=WALLET,
                                     note=row_dict['Comment (optional)'])
    else:
        raise UnexpectedTypeError(parser.in_header.index(TYPE), TYPE, row_dict[TYPE])

DataParser(DataParser.TYPE_WALLET,
           "Yoroi",
           ['Type (Trade, IN or OUT)', 'Buy Amount', 'Buy Cur.', 'Sell Amount', 'Sell Cur.',
            'Fee Amount (optional)', 'Fee Cur. (optional)', 'Exchange (optional)',
            'Trade Group (optional)', 'Comment (optional)', 'Date'],
           worksheet_name="Yoroi",
           row_handler=parse_yoroi)
