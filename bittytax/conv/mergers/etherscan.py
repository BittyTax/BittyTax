# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import sys
import copy

from decimal import Decimal

from colorama import Fore, Back

from ...config import config
from ..out_record import TransactionOutRecord
from ..datamerge import DataMerge, MergeDataRow
from ..exceptions import UnexpectedContentError
from ..parsers.etherscan import etherscan_txns, etherscan_tokens, etherscan_nfts, etherscan_int, \
                                get_note

PRECISION = Decimal('0.' + '0' * 18)

TXNS = 'txn'
TOKENS = 'token'
NFTS = 'nft'
INTERNAL_TXNS = 'int'

def merge_etherscan(data_files):
    return do_merge_etherscan(data_files, [])

def do_merge_etherscan(data_files, staking_addresses):
    merge = False

    tx_ids = {}

    for file_id in data_files:
        if file_id not in (TOKENS, NFTS, INTERNAL_TXNS):
            continue

        for dr in data_files[file_id].data_rows:
            if dr.row_dict['Txhash'] in tx_ids:
                tx_ids[dr.row_dict['Txhash']].append(MergeDataRow(dr, data_files[file_id], file_id))
            else:
                tx_ids[dr.row_dict['Txhash']] = [MergeDataRow(dr, data_files[file_id], file_id)]

    for data_row in data_files[TXNS].data_rows:
        t_merge = [mdr for mdr in tx_ids.get(data_row.row_dict['Txhash'], [])
                   if not mdr.data_row.parsed]

        if t_merge:
            if config.debug:
                sys.stderr.write("%smerge: %s:%s\n" % (Fore.GREEN, TXNS.ljust(5), data_row))

            for t in t_merge:
                if config.debug:
                    sys.stderr.write("%smerge: %s:%s\n" % (Fore.GREEN, t.data_file_id.ljust(5),
                                                           t.data_row))

                data_row.parsed = True
        else:
            if config.debug:
                sys.stderr.write("%smerge: txn:  %s\n" % (Fore.BLUE, data_row))

            continue

        t_ins = [t.data_row for t in t_merge + [data_row] if t.data_row.t_record and
                 t.data_row.t_record.t_type == TransactionOutRecord.TYPE_DEPOSIT]
        t_outs = [t.data_row for t in t_merge + [data_row] if t.data_row.t_record and
                  t.data_row.t_record.t_type == TransactionOutRecord.TYPE_WITHDRAWAL]

        if config.debug:
            output_records(data_row, t_ins, t_outs)

        t_ins_orig = copy.copy(t_ins)
        fee_quantity = data_row.t_record.fee_quantity
        fee_asset = data_row.t_record.fee_asset

        method_handling(t_ins, data_row, staking_addresses)

        # Make trades
        if len(t_ins) == 1 and t_outs:
            do_etherscan_multi_sell(t_ins, t_outs, data_row)
        elif len(t_outs) == 1 and t_ins:
            do_etherscan_multi_buy(t_ins, t_outs, data_row)
        elif len(t_ins) > 1 and len(t_outs) > 1:
            # multi-sell to multi-buy trade not supported
            sys.stderr.write("%sWARNING%s Merge failure for Txhash: %s\n" % (
                Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, data_row.row_dict['Txhash']))

            for mdr in t_merge:
                mdr.data_row.failure = UnexpectedContentError(
                    mdr.data_file.parser.in_header.index('Txhash'),
                    'Txhash', mdr.data_row.row_dict['Txhash'])
                sys.stderr.write("%srow[%s] %s\n" % (
                    Fore.YELLOW,
                    mdr.data_file.parser.in_header_row_num + mdr.data_row.line_num,
                    mdr.data_row))
            continue

        # Split fees
        t_all = [t for t in t_ins_orig + t_outs if t.t_record]
        do_fee_split(t_all, data_row, fee_quantity, fee_asset)

        merge = True

        if config.debug:
            output_records(data_row, t_ins_orig, t_outs)

    return merge

def output_records(data_row, t_ins, t_outs):
    dup = bool(data_row in t_ins + t_outs)

    sys.stderr.write("%smerge:   TR-F%s: %s\n" % (
        Fore.YELLOW, '*' if dup else '', data_row.t_record))

    for t_in in t_ins:
        sys.stderr.write("%smerge:   TR-I%s: %s\n" % (
            Fore.YELLOW, '*' if data_row is t_in else '', t_in.t_record))
    for t_out in t_outs:
        sys.stderr.write("%smerge:   TR-O%s: %s\n" % (
            Fore.YELLOW, '*' if data_row is t_out else '', t_out.t_record))

def method_handling(t_ins, data_row, staking_addresses):
    if data_row.row_dict.get('Method') in ("Enter Staking", "Leave Staking", "Deposit", "Withdraw"):
        if t_ins:
            staking = [t for t in t_ins if t.row_dict['ContractAddress'] in staking_addresses
                       and t.row_dict['From'] != data_row.row_dict['To']]
            if staking:
                if len(staking) == 1:
                    staking[0].t_record.t_type = TransactionOutRecord.TYPE_STAKING
                    t_ins.remove(staking[0])

                    if config.debug:
                        sys.stderr.write("%smerge:     staking:\n" % (Fore.YELLOW))
                else:
                    raise Exception

def do_etherscan_multi_sell(t_ins, t_outs, data_row):
    if config.debug:
        sys.stderr.write("%smerge:     trade sell(s):\n" % (Fore.YELLOW))

    tot_buy_quantity = 0

    buy_quantity = t_ins[0].t_record.buy_quantity
    buy_asset = t_ins[0].t_record.buy_asset

    if config.debug:
        sys.stderr.write("%smerge:       buy_quantity=%s buy_asset=%s\n" % (
            Fore.YELLOW,
            TransactionOutRecord.format_quantity(buy_quantity), buy_asset))

    for cnt, t_out in enumerate(t_outs):
        if cnt < len(t_outs) - 1:
            split_buy_quantity = (buy_quantity / len(t_outs)).quantize(PRECISION)
            tot_buy_quantity += split_buy_quantity
        else:
            # Last t_out, use up remainder
            split_buy_quantity = buy_quantity - tot_buy_quantity

        if config.debug:
            sys.stderr.write("%smerge:       split_buy_quantity=%s\n" % (
                Fore.YELLOW,
                TransactionOutRecord.format_quantity(split_buy_quantity)))

        t_out.t_record.t_type = TransactionOutRecord.TYPE_TRADE
        t_out.t_record.buy_quantity = split_buy_quantity
        t_out.t_record.buy_asset = buy_asset
        t_out.t_record.note = get_note(data_row.row_dict)

    # Remove TR for buy now it's been added to each sell
    t_ins[0].t_record = None

def do_etherscan_multi_buy(t_ins, t_outs, data_row):
    if config.debug:
        sys.stderr.write("%smerge:     trade buy(s):\n" % (Fore.YELLOW))

    tot_sell_quantity = 0

    sell_quantity = t_outs[0].t_record.sell_quantity
    sell_asset = t_outs[0].t_record.sell_asset

    if config.debug:
        sys.stderr.write("%smerge:       sell_quantity=%s sell_asset=%s\n" % (
            Fore.YELLOW,
            TransactionOutRecord.format_quantity(sell_quantity), sell_asset))

    for cnt, t_in in enumerate(t_ins):
        if cnt < len(t_ins) - 1:
            split_sell_quantity = (sell_quantity / len(t_ins)).quantize(PRECISION)
            tot_sell_quantity += split_sell_quantity
        else:
            # Last t_in, use up remainder
            split_sell_quantity = sell_quantity - tot_sell_quantity

        if config.debug:
            sys.stderr.write("%smerge:       split_sell_quantity=%s\n" % (
                Fore.YELLOW,
                TransactionOutRecord.format_quantity(split_sell_quantity)))

        t_in.t_record.t_type = TransactionOutRecord.TYPE_TRADE
        t_in.t_record.sell_quantity = split_sell_quantity
        t_in.t_record.sell_asset = sell_asset
        t_in.t_record.note = get_note(data_row.row_dict)

    # Remove TR for sell now it's been added to each buy
    t_outs[0].t_record = None

def do_fee_split(t_all, data_row, fee_quantity, fee_asset):
    if config.debug:
        sys.stderr.write("%smerge:     split fees:\n" % (Fore.YELLOW))
        sys.stderr.write("%smerge:       fee_quantity=%s fee_asset=%s\n" % (
            Fore.YELLOW,
            TransactionOutRecord.format_quantity(fee_quantity), fee_asset))

    tot_fee_quantity = 0

    for cnt, t in enumerate(t_all):
        if cnt < len(t_all) - 1:
            split_fee_quantity = (fee_quantity / len(t_all)).quantize(PRECISION)
            tot_fee_quantity += split_fee_quantity
        else:
            # Last t, use up remainder
            split_fee_quantity = fee_quantity - tot_fee_quantity if fee_quantity else None

        if config.debug:
            sys.stderr.write("%smerge:       split_fee_quantity=%s\n" % (
                Fore.YELLOW,
                TransactionOutRecord.format_quantity(split_fee_quantity)))

        t.t_record.fee_quantity = split_fee_quantity
        t.t_record.fee_asset = fee_asset
        t.t_record.note = get_note(data_row.row_dict)

    # Remove TR for fee now it's been added to each withdrawal
    if data_row.t_record and data_row not in t_all:
        if data_row.t_record.t_type == TransactionOutRecord.TYPE_SPEND:
            data_row.t_record = None
        else:
            data_row.t_record.fee_quantity = None
            data_row.t_record.fee_asset = ''

DataMerge("Etherscan fees & multi-token transactions",
          {TXNS: {'req': DataMerge.MAN, 'obj': etherscan_txns},
           TOKENS: {'req': DataMerge.OPT, 'obj': etherscan_tokens},
           NFTS: {'req': DataMerge.OPT, 'obj': etherscan_nfts},
           INTERNAL_TXNS: {'req': DataMerge.OPT, 'obj': etherscan_int}},
          merge_etherscan)
