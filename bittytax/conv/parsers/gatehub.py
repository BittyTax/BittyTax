# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import copy
from decimal import Decimal

from ...config import config
from ...record import TransactionRecord
from ..dataparser import DataParser

WALLET = "Gatehub"

log = logging.getLogger()

def parse_gatehub(all_in_row):
    all_out_row = copy.deepcopy(all_in_row)
    i = 0

    while i < len(all_in_row):
        in_row = all_in_row[i]
        t_type = ""
        buy_quantity = None
        buy_asset = ""
        sell_quantity = None
        sell_asset = ""
        fee_quantity = None
        fee_asset = ""

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
                                                   in_row[1],
                                                   "ripple_network_fee",
                                                   [sell_asset, buy_asset])
        elif in_row[2] == "exchange":
            if in_row[3]:
                t_type = TransactionRecord.TYPE_TRADE
                if Decimal(in_row[3]) < 0:
                    sell_quantity = abs(Decimal(in_row[3]))
                    sell_asset = in_row[4]

                    buy_quantity, buy_asset = find_same_tx(all_in_row, i,
                                                           in_row[1],
                                                           "exchange", [])
                    fee_quantity, fee_asset = find_same_tx(all_in_row, i,
                                                           in_row[1],
                                                           "ripple_network_fee",
                                                           [sell_asset, buy_asset])
                else:
                    i += 1
                    continue
            else:
                i += 1
                continue
        elif in_row[2] == "ripple_network_fee":
            # Check for left over fees last
            i += 1
            continue
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

        all_out_row[i].extend(t_record.to_csv())
        in_row[1] = ""    # remove hash to prevent future matches

        i += 1

    i = 0
    while i < len(all_in_row):
        # Search for any remaining unmatched fees
        in_row = all_in_row[i]
        if in_row[2] == "ripple_network_fee" and in_row[1] != "":
            t_type = "Spend"
            sell_quantity = abs(Decimal(in_row[3]))
            sell_asset = in_row[4]

            t_record = TransactionRecord(TransactionRecord.TYPE_SPEND,
                                         DataParser.parse_timestamp(in_row[0]),
                                         sell_quantity=sell_quantity,
                                         sell_asset=sell_asset,
                                         wallet=WALLET)

            all_out_row[i].extend(t_record.to_csv())
            in_row[1] = ""    # remove hash to prevent future matches

        i += 1

    for i, _ in enumerate(all_in_row):
        # Check for unmatched transactions
        if all_in_row[i][1] != "":
            log.warning("Skipping row: %s", all_in_row[i])

    if not config.args.append:
        for i, _ in enumerate(all_in_row):
            del all_out_row[i][0:len(all_in_row[i])]

        all_out_row = filter(None, all_out_row)

    return all_out_row

def find_same_tx(all_in_row, i, tx_hash, tx_type, currencies):
    x = 0
    quantity = None
    asset = ""

    while x < len(all_in_row):
        in_row = all_in_row[x]

        if in_row[1] == tx_hash and in_row[2] == tx_type and i != x:
            if (tx_type == "ripple_network_fee" and
                    in_row[4] in currencies) or tx_type != "ripple_network_fee":
                quantity = abs(Decimal(in_row[3]))
                asset = in_row[4]
                in_row[1] = ""    # remove hash to prevent future matches
                break

        x += 1

    return quantity, asset

DataParser(DataParser.TYPE_EXCHANGE,
           "GateHub (Ripple)",
           ['Time', 'TX hash', 'Type', 'Amount', 'Currency', 'Currency Issuer Address',
            'Currency Issuer Name', 'Balance'],
           all_handler=parse_gatehub)
