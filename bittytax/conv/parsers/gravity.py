# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataParserError, UnexpectedTypeError

WALLET = "Gravity"
SYSTEM_ACCOUNT = "00000000-0000-0000-0000-000000000000"

def parse_gravity(data_rows, parser, _filename):
    for data_row in data_rows:
        if data_row.parsed:
            continue

        try:
            parse_gravity_row(data_rows, parser, data_row)
        except DataParserError as e:
            data_row.failure = e

def parse_gravity_row(data_rows, parser, data_row):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[3])
    data_row.parsed = True

    t_type = ""
    buy_quantity = None
    buy_asset = ""
    sell_quantity = None
    sell_asset = ""
    fee_quantity = None
    fee_asset = ""

    if in_row[4] == "deposit":
        if in_row[1] == SYSTEM_ACCOUNT:
            t_type = TransactionOutRecord.TYPE_DEPOSIT
            buy_quantity = in_row[6]
            buy_asset = in_row[7]
        else:
            return

    elif in_row[4] == "withdrawal":
        if in_row[2] == SYSTEM_ACCOUNT:
            t_type = TransactionOutRecord.TYPE_WITHDRAWAL
            sell_quantity = in_row[6]
            sell_asset = in_row[7]
            quantity, asset = find_same_tx(data_rows, in_row[0],
                                           "withdrawal", 2)
            if Decimal(sell_quantity) < Decimal(quantity):
                #swap sell/fee around
                fee_quantity = sell_quantity
                fee_asset = sell_asset
                sell_quantity = quantity
                sell_asset = asset
            else:
                fee_quantity = quantity
                fee_asset = asset

        else:
            return
    elif in_row[4] == "trade" and in_row[1] == SYSTEM_ACCOUNT:
        t_type = TransactionOutRecord.TYPE_TRADE
        buy_quantity = in_row[6]
        buy_asset = in_row[7]

        sell_quantity, sell_asset = find_same_tx(data_rows, in_row[0],
                                                 "trade", 2)
        if sell_quantity is None:
            return
    elif in_row[4] == "trade" and in_row[2] == SYSTEM_ACCOUNT:
        t_type = TransactionOutRecord.TYPE_TRADE
        sell_quantity = in_row[6]
        sell_asset = in_row[7]

        buy_quantity, buy_asset = find_same_tx(data_rows, in_row[0],
                                               "trade", 1)
        if buy_quantity is None:
            return
    elif in_row[4] == "referral fees grouping":
        t_type = TransactionOutRecord.TYPE_GIFT_RECEIVED
        buy_quantity = in_row[6]
        buy_asset = in_row[7]
    elif in_row[4] in ("referral fees collection", "referral fees transfer"):
        return
    else:
        raise UnexpectedTypeError(4, parser.in_header[4], in_row[4])

    data_row.t_record = TransactionOutRecord(t_type,
                                             data_row.timestamp,
                                             buy_quantity=buy_quantity,
                                             buy_asset=buy_asset,
                                             sell_quantity=sell_quantity,
                                             sell_asset=sell_asset,
                                             fee_quantity=fee_quantity,
                                             fee_asset=fee_asset,
                                             wallet=WALLET)

def find_same_tx(data_rows, tx_hash, tx_type, system_acc):
    quantity = None
    asset = ""

    data_rows = [data_row for data_row in data_rows
                 if data_row.in_row[0] == tx_hash and not data_row.parsed]
    for data_row in data_rows:
        if tx_type == data_row.in_row[4] and data_row.in_row[system_acc] == SYSTEM_ACCOUNT:
            quantity = data_row.in_row[6]
            asset = data_row.in_row[7]
            data_row.timestamp = DataParser.parse_timestamp(data_row.in_row[3])
            data_row.parsed = True
            break

    return quantity, asset

DataParser(DataParser.TYPE_EXCHANGE,
           "Gravity (Bitstocks)",
           ['transaction id', 'from account', 'to account', 'date utc', 'transaction type',
            'status', 'amount', 'currency'],
           worksheet_name="Gravity",
           all_handler=parse_gravity)
