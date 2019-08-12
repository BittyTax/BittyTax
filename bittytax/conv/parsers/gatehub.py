# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import copy
from decimal import Decimal

from ...record import TransactionRecord
from ..dataparser import DataParser

WALLET = "Gatehub"

log = logging.getLogger()

def parse_gatehub(all_in_row_orig):
    all_in_row = copy.deepcopy(all_in_row_orig)
    t_records = []

    for i, in_row in enumerate(all_in_row):
        t_type = ""
        buy_quantity = None
        buy_asset = ""
        sell_quantity = None
        sell_asset = ""
        fee_quantity = None
        fee_asset = ""

        if not in_row[1] or not in_row[3]:
            # Skip if already matched, or Amount missing
            t_records.append(None)
            continue

        if in_row[2] == "payment":
            if Decimal(in_row[3]) < 0:
                t_type = TransactionRecord.TYPE_WITHDRAWAL
                sell_quantity = abs(Decimal(in_row[3]))
                sell_asset = in_row[4]
            else:
                t_type = TransactionRecord.TYPE_DEPOSIT
                buy_quantity = in_row[3]
                buy_asset = in_row[4]

            fee_quantity, fee_asset = find_same_tx(all_in_row, i,
                                                   "ripple_network_fee",
                                                   [sell_asset, buy_asset])
        elif in_row[2] == "exchange":
            t_type = TransactionRecord.TYPE_TRADE
            if Decimal(in_row[3]) < 0:
                sell_quantity = abs(Decimal(in_row[3]))
                sell_asset = in_row[4]

                buy_quantity, buy_asset = find_same_tx(all_in_row, i,
                                                       "exchange")
            else:
                buy_quantity = in_row[3]
                buy_asset = in_row[4]

                sell_quantity, sell_asset = find_same_tx(all_in_row, i,
                                                         "exchange")

            if sell_quantity is None or buy_quantity is None:
                # Skip if buy or sell is missing from Trade
                continue

            fee_quantity, fee_asset = find_same_tx(all_in_row, i,
                                                   "ripple_network_fee",
                                                   [sell_asset, buy_asset])
        elif in_row[2] == "ripple_network_fee":
            # Fees which are not associated with a payment or exchange are added
            # as a Spend
            t_type = TransactionRecord.TYPE_SPEND
            sell_quantity = abs(Decimal(in_row[3]))
            sell_asset = in_row[4]
        else:
            raise ValueError("Unrecognised Type: " + in_row[2])

        t_record = TransactionRecord(t_type,
                                     DataParser.parse_timestamp(in_row[0]),
                                     buy_quantity=buy_quantity,
                                     buy_asset=buy_asset,
                                     sell_quantity=sell_quantity,
                                     sell_asset=sell_asset,
                                     fee_quantity=fee_quantity,
                                     fee_asset=fee_asset,
                                     wallet=WALLET)
        t_records.append(t_record)
        in_row[1] = None    # Remove hash to prevent future matches

    for i, in_row in enumerate(all_in_row):
        # Check for unmatched transactions
        if in_row[1]:
            log.warning("Skipping row[%s]: %s", i + 2, in_row)

    return t_records

def find_same_tx(all_in_row, i, tx_type, currencies=None):
    tx_hash = all_in_row[i][1]
    quantity = None
    asset = ""

    for _, in_row in enumerate(all_in_row[i + 1:len(all_in_row)]):
        if in_row[1] == tx_hash and in_row[2] == tx_type and \
                (tx_type == "ripple_network_fee" and in_row[4] in currencies or
                 tx_type != "ripple_network_fee"):
            quantity = abs(Decimal(in_row[3]))
            asset = in_row[4]
            in_row[1] = None    # Remove hash to prevent future matches
            break

    return quantity, asset

DataParser(DataParser.TYPE_EXCHANGE,
           "GateHub (Ripple)",
           ['Time', 'TX hash', 'Type', 'Amount', 'Currency', 'Currency Issuer Address',
            'Currency Issuer Name', 'Balance'],
           all_handler=parse_gatehub)
