# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataParserError, UnexpectedTypeError, \
                         MissingValueError, MissingComponentError

WALLET = "Gatehub"

log = logging.getLogger()

def parse_gatehub(data_rows, parser):
    for data_row in data_rows:
        if data_row.parsed:
            continue

        try:
            parse_gatehub_row(data_rows, parser, data_row)
        except DataParserError as e:
            data_row.failure = e

def parse_gatehub_row(data_rows, parser, data_row):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])
    data_row.parsed = True

    t_type = ""
    buy_quantity = None
    buy_asset = ""
    sell_quantity = None
    sell_asset = ""
    fee_quantity = None
    fee_asset = ""

    if not in_row[3]:
        raise MissingValueError(3, parser.in_header[3])

    if in_row[2] == "payment":
        if Decimal(in_row[3]) < 0:
            t_type = TransactionOutRecord.TYPE_WITHDRAWAL
            sell_quantity = abs(Decimal(in_row[3]))
            sell_asset = in_row[4]
        else:
            t_type = TransactionOutRecord.TYPE_DEPOSIT
            buy_quantity = in_row[3]
            buy_asset = in_row[4]

        fee_quantity, fee_asset = find_same_tx(data_rows, in_row[1],
                                               "ripple_network_fee")
    elif in_row[2] == "exchange":
        t_type = TransactionOutRecord.TYPE_TRADE
        if Decimal(in_row[3]) < 0:
            sell_quantity = abs(Decimal(in_row[3]))
            sell_asset = in_row[4]

            buy_quantity, buy_asset = find_same_tx(data_rows, in_row[1],
                                                   "exchange")
        else:
            buy_quantity = in_row[3]
            buy_asset = in_row[4]

            sell_quantity, sell_asset = find_same_tx(data_rows, in_row[1],
                                                     "exchange")

        if sell_quantity is None or buy_quantity is None:
            raise MissingComponentError(1, parser.in_header[1], in_row[1])

        fee_quantity, fee_asset = find_same_tx(data_rows, in_row[1],
                                               "ripple_network_fee")
    elif in_row[2] == "ripple_network_fee":
        # Fees which are not associated with a payment or exchange are added
        # as a Spend
        t_type = TransactionOutRecord.TYPE_SPEND
        sell_quantity = abs(Decimal(in_row[3]))
        sell_asset = in_row[4]
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

    data_row.t_record = TransactionOutRecord(t_type,
                                             data_row.timestamp,
                                             buy_quantity=buy_quantity,
                                             buy_asset=buy_asset,
                                             sell_quantity=sell_quantity,
                                             sell_asset=sell_asset,
                                             fee_quantity=fee_quantity,
                                             fee_asset=fee_asset,
                                             wallet=WALLET)

def find_same_tx(data_rows, tx_hash, tx_type):
    quantity = None
    asset = ""

    data_rows = [data_row for data_row in data_rows
                 if data_row.in_row[1] == tx_hash and not data_row.parsed]
    for data_row in data_rows:
        if tx_type == data_row.in_row[2]:
            quantity = abs(Decimal(data_row.in_row[3]))
            asset = data_row.in_row[4]
            data_row.timestamp = DataParser.parse_timestamp(data_row.in_row[0])
            data_row.parsed = True
            break

    return quantity, asset

DataParser(DataParser.TYPE_EXCHANGE,
           "GateHub (Ripple)",
           ['Time', 'TX hash', 'Type', 'Amount', 'Currency', 'Currency Issuer Address',
            'Currency Issuer Name', 'Balance'],
           worksheet_name="Gatehub",
           all_handler=parse_gatehub)
