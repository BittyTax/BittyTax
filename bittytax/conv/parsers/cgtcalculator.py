# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal
from datetime import datetime

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError, UnexpectedContentError

WALLET = "CGTCalculator"

def parse_cgtcalculator(data_row, parser, _filename):
    in_row = data_row.in_row

    data_row.timestamp = DataParser.parse_timestamp(in_row[1])

    if in_row[0] == "B":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 sell_quantity=Decimal(in_row[3]) * \
                                                               Decimal(in_row[4]),
                                                 sell_asset=config.CCY,
                                                 fee_quantity=Decimal(in_row[5]) + \
                                                              Decimal(in_row[6]),
                                                 fee_asset=config.CCY,
                                                 wallet=WALLET)
    elif in_row[0] == "S":
        if data_row.timestamp >= datetime(2008, 4, 6, tzinfo=config.TZ_UTC):
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=Decimal(in_row[3]) * \
                                                                  Decimal(in_row[4]),
                                                     buy_asset=config.CCY,
                                                     sell_quantity=in_row[3],
                                                     sell_asset=in_row[2],
                                                     fee_quantity=Decimal(in_row[5]) + \
                                                                  Decimal(in_row[6]),
                                                     fee_asset=config.CCY,
                                                     wallet=WALLET)
        else:
            raise UnexpectedContentError(1, parser.in_header[1], in_row[1])
    elif in_row[0] == "T":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_SPOUSE,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[3],
                                                 sell_asset=in_row[2],
                                                 fee_quantity=in_row[4],
                                                 fee_asset=config.CCY,
                                                 wallet=WALLET)

    else:
        raise UnexpectedTypeError(0, parser.in_header[0], in_row[0])

DataParser(DataParser.TYPE_SHARES,
           "CGTCalculator",
           ['B/S', 'Date', 'Company', 'Shares', 'Price', 'Charges', 'Tax'],
           worksheet_name="CGTCalculator",
           row_handler=parse_cgtcalculator)

DataParser(DataParser.TYPE_SHARES,
           "CGTCalculator",
           ['B/S', 'Date', 'Company', 'Shares', 'Price', 'Charges', 'Tax', ''],
           worksheet_name="CGTCalculator",
           row_handler=parse_cgtcalculator)
