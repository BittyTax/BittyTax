# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Exodus"

def parse_exodus(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['DATE'], fuzzy=True)

    if row_dict['TYPE'] == "deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['INAMOUNT'],
                                                 buy_asset=row_dict['INCURRENCY'],
                                                 wallet=WALLET,
                                                 note=row_dict['PERSONALNOTE'])
    elif row_dict['TYPE'] == "withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(row_dict['OUTAMOUNT'])),
                                                 sell_asset=row_dict['OUTCURRENCY'],
                                                 fee_quantity=abs(Decimal(row_dict['FEEAMOUNT'])),
                                                 fee_asset=row_dict['FEECURRENCY'],
                                                 wallet=WALLET,
                                                 note=row_dict['PERSONALNOTE'])
    elif row_dict['TYPE'] == "exchange":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['INAMOUNT'],
                                                 buy_asset=row_dict['INCURRENCY'],
                                                 sell_quantity=abs(Decimal(row_dict['OUTAMOUNT'])),
                                                 sell_asset=row_dict['OUTCURRENCY'],
                                                 fee_quantity=abs(Decimal(row_dict['FEEAMOUNT'])),
                                                 fee_asset=row_dict['FEECURRENCY'],
                                                 wallet=WALLET,
                                                 note=row_dict['PERSONALNOTE'])
    else:
        raise UnexpectedTypeError(parser.in_header.index('TYPE'), 'TYPE', row_dict['TYPE'])

DataParser(DataParser.TYPE_WALLET,
           "Exodus",
           ['DATE', 'TYPE', 'FROMPORTFOLIO', 'TOPORTFOLIO', 'OUTAMOUNT', 'OUTCURRENCY', 'FEEAMOUNT',
            'FEECURRENCY', 'OUTTXID', 'OUTTXURL', 'INAMOUNT', 'INCURRENCY', 'INTXID', 'INTXURL',
            'ORDERID', 'PERSONALNOTE', 'TOADDRESS'],
           worksheet_name="Exodus",
           row_handler=parse_exodus)
