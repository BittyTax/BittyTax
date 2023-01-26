# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import re
from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Exodus"

def parse_exodus_v2(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['DATE'], fuzzy=True)

    if row_dict['TYPE'] == "deposit":
        buy_quantity, buy_asset = split_asset(row_dict['COINAMOUNT'])

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=buy_quantity,
                                                 buy_asset=buy_asset,
                                                 wallet=WALLET,
                                                 note=row_dict['PERSONALNOTE'])
    elif row_dict['TYPE'] == "withdrawal":
        sell_quantity, sell_asset = split_asset(row_dict['COINAMOUNT'])
        fee_quantity, fee_asset = split_asset(row_dict['FEE'])

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=sell_quantity,
                                                 sell_asset=sell_asset,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 wallet=WALLET,
                                                 note=row_dict['PERSONALNOTE'])
    else:
        raise UnexpectedTypeError(parser.in_header.index('TYPE'), 'TYPE', row_dict['TYPE'])

def split_asset(coinamount):
    match = re.match(r'^[-]?(\d+|[\d|,]*\.\d+) (\w+)$', coinamount)
    if match:
        return match.group(1), match.group(2)
    return None, ''

def parse_exodus_v1(data_row, parser, **_kwargs):
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
           ['TXID', 'TXURL', 'DATE', 'TYPE', 'FROMPORTFOLIO', 'TOPORTFOLIO', 'COINAMOUNT', 'FEE',
            'BALANCE', 'EXCHANGE', 'PERSONALNOTE'],
           worksheet_name="Exodus",
           row_handler=parse_exodus_v2)

DataParser(DataParser.TYPE_WALLET,
           "Exodus",
           ['DATE', 'TYPE', 'FROMPORTFOLIO', 'TOPORTFOLIO', 'OUTAMOUNT', 'OUTCURRENCY', 'FEEAMOUNT',
            'FEECURRENCY', 'TOADDRESS', 'OUTTXID', 'OUTTXURL', 'INAMOUNT', 'INCURRENCY', 'INTXID',
            'INTXURL', 'ORDERID', 'PERSONALNOTE'],
           worksheet_name="Exodus",
           row_handler=parse_exodus_v1)

DataParser(DataParser.TYPE_WALLET,
           "Exodus",
           ['DATE', 'TYPE', 'FROMPORTFOLIO', 'TOPORTFOLIO', 'OUTAMOUNT', 'OUTCURRENCY', 'FEEAMOUNT',
            'FEECURRENCY', 'OUTTXID', 'OUTTXURL', 'INAMOUNT', 'INCURRENCY', 'INTXID', 'INTXURL',
            'ORDERID', 'PERSONALNOTE', 'TOADDRESS'],
           worksheet_name="Exodus",
           row_handler=parse_exodus_v1)
