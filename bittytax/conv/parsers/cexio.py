# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

import re
from decimal import Decimal, ROUND_DOWN

from ...config import config
from ..out_record import TransactionOutRecord as TxOutRec
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError, UnexpectedContentError

WALLET = "CEX.IO"

def parse_cexio(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['DateUTC'])

    if row_dict['FeeAmount']:
        fee_quantity = row_dict['FeeAmount']
        fee_asset = row_dict['FeeSymbol']
    else:
        fee_quantity = None
        fee_asset = ""

    if row_dict['Type'] == "deposit":
        if row_dict['Balance'] == "pending":
            return

        if row_dict['Comment'].endswith("Completed") or row_dict['Comment'].startswith("Confirmed"):
            data_row.t_record = TxOutRec(TxOutRec.TYPE_DEPOSIT,
                                         data_row.timestamp,
                                         buy_quantity=row_dict['Amount'],
                                         buy_asset=row_dict['Symbol'],
                                         fee_quantity=fee_quantity,
                                         fee_asset=fee_asset,
                                         wallet=WALLET,
                                         note=row_dict['Comment'])
    elif row_dict['Type'] == "withdraw":
        if fee_quantity:
            sell_quantity = abs(Decimal(row_dict['Amount'])) - Decimal(fee_quantity)
        else:
            sell_quantity = abs(Decimal(row_dict['Amount']))

        data_row.t_record = TxOutRec(TxOutRec.TYPE_WITHDRAWAL,
                                     data_row.timestamp,
                                     sell_quantity=sell_quantity,
                                     sell_asset=row_dict['Symbol'],
                                     fee_quantity=fee_quantity,
                                     fee_asset=fee_asset,
                                     wallet=WALLET,
                                     note=row_dict['Comment'])
    elif row_dict['Type'] in ("buy", "sell"):
        trade_info = get_trade_info(row_dict['Comment'], row_dict['Type'])

        if trade_info is None:
            raise UnexpectedContentError(parser.in_header.index('Comment'), 'Comment',
                                         row_dict['Comment'])

        if trade_info[0] == "Bought":
            buy_quantity = row_dict['Amount']
            buy_asset = row_dict['Symbol']
            sell_quantity = Decimal(trade_info[1]) * Decimal(trade_info[3])
            sell_asset = trade_info[4]
            if sell_asset in config.fiat_list:
                sell_quantity = sell_quantity.quantize(Decimal('0.00'), ROUND_DOWN)
        elif trade_info[0] == "Sold":
            if fee_quantity:
                buy_quantity = Decimal(row_dict['Amount']) + Decimal(fee_quantity)
            else:
                buy_quantity = Decimal(row_dict['Amount'])
            buy_asset = row_dict['Symbol']
            sell_quantity = trade_info[1]
            sell_asset = trade_info[2]
        else:
            # Skip corresponding "Buy/Sell Order" row
            return

        data_row.t_record = TxOutRec(TxOutRec.TYPE_TRADE,
                                     data_row.timestamp,
                                     buy_quantity=buy_quantity,
                                     buy_asset=buy_asset,
                                     sell_quantity=sell_quantity,
                                     sell_asset=sell_asset,
                                     fee_quantity=fee_quantity,
                                     fee_asset=fee_asset,
                                     wallet=WALLET,
                                     note=row_dict['Comment'])
    elif row_dict['Type'] in ("referral", "checksum", "costsNothing"):
        data_row.t_record = TxOutRec(TxOutRec.TYPE_GIFT_RECEIVED,
                                     data_row.timestamp,
                                     buy_quantity=row_dict['Amount'],
                                     buy_asset=row_dict['Symbol'],
                                     wallet=WALLET,
                                     note=row_dict['Comment'])

    elif row_dict['Type'] == "staking":
        data_row.t_record = TxOutRec(TxOutRec.TYPE_STAKING,
                                     data_row.timestamp,
                                     buy_quantity=row_dict['Amount'],
                                     buy_asset=row_dict['Symbol'],
                                     wallet=WALLET,
                                     note=row_dict['Comment'])
    elif row_dict['Type'] == "cancel":
        # Skip
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

def get_trade_info(comment, t_type):
    if t_type == "buy":
        match = re.match(r'^(Bought) (\d+|\d+\.\d+) (\w+) at (\d+|\d+\.\d+) (\w+)$'
                         r'|^Buy Order.*$', comment)
    elif t_type == "sell":
        match = re.match(r'^(Sold) (\d+|\d+\.\d+) (\w+) at (\d+|\d+\.\d+) (\w+)$'
                         r'|^Sell Order.*$', comment)
    else:
        return None

    if match:
        return match.groups()
    return None

DataParser(DataParser.TYPE_EXCHANGE,
           "CEX.IO",
           ['DateUTC', 'Amount', 'Symbol', 'Balance', 'Type', 'Pair', 'FeeSymbol', 'FeeAmount',
            'Comment'],
           worksheet_name="CEX.IO",
           row_handler=parse_cexio)
