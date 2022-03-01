# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

import re

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedContentError

WALLET = "Bittylicious"

def parse_bittylicious(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Start Timestamp (UTC)'])
    buy_quantity, buy_asset = split_asset(row_dict['Amount'])
    if buy_quantity is None:
        raise UnexpectedContentError(parser.in_header.index('Amount'), 'Amount',
                                     row_dict['Amount'])

    sell_quantity, sell_asset = get_currency(row_dict['Fiat'])
    if sell_quantity is None:
        raise UnexpectedContentError(parser.in_header.index('Fiat'), 'Fiat', row_dict['Fiat'])

    if row_dict['Status'] == "Received":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=buy_quantity,
                                                 buy_asset=buy_asset,
                                                 sell_quantity=sell_quantity.replace(',', ''),
                                                 sell_asset=sell_asset,
                                                 wallet=WALLET)

def split_asset(amount):
    match = re.match(r'^(\d+|\d+\.\d+) (\w+)$', amount)
    if match:
        return match.group(1), match.group(2)
    return None, ''

def get_currency(fiat):
    match = re.match(r'^-?([£€])([\d|,]+(?:\.\d{2})?)$', fiat)
    if match:
        if match.group(1) == '£':
            return match.group(2), "GBP"

        if match.group(1) == '€':
            return match.group(2), "EUR"

    return None, ''

DataParser(DataParser.TYPE_EXCHANGE,
           "Bittylicious",
           ['Reference', 'Start Timestamp (UTC)', 'Status', 'Amount', 'Fiat'],
           worksheet_name="Bittylicious",
           row_handler=parse_bittylicious)
