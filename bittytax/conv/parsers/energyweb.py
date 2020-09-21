# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Energy Web"

def parse_energy_web(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[2])

    if in_row[6] == "IN":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[7]) / 10 ** 18,
                                                 buy_asset="EWT",
                                                 wallet=WALLET)
    elif in_row[6] == "OUT":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=Decimal(in_row[7]) / 10 ** 18,
                                                 sell_asset="EWT",
                                                 fee_quantity=Decimal(in_row[8]) / 10 ** 18,
                                                 fee_asset="EWT",
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(6, parser.in_header[6], in_row[6])

DataParser(DataParser.TYPE_EXPLORER,
           "Energy Web",
           ['TxHash', 'BlockNumber', 'UnixTimestamp', 'FromAddress', 'ToAddress', 'ContractAddress',
            'Type', 'Value', 'Fee', 'Status', 'ErrCode', 'CurrentPrice', 'TxDateOpeningPrice',
            'TxDateClosingPrice'],
           worksheet_name="Energy Web",
           row_handler=parse_energy_web)
