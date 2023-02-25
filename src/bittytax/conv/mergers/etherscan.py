# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import copy
import sys
from decimal import Decimal

from colorama import Back, Fore

from ...config import config
from ..datamerge import DataMerge, MergeDataRow
from ..exceptions import UnexpectedContentError
from ..out_record import TransactionOutRecord
from ..parsers.etherscan import (
    ETHERSCAN_INT,
    ETHERSCAN_NFTS,
    ETHERSCAN_TOKENS,
    ETHERSCAN_TXNS,
    _get_note,
)

PRECISION = Decimal("0." + "0" * 18)

TXNS = "txn"
TOKENS = "token"
NFTS = "nft"
INTERNAL_TXNS = "int"


def merge_etherscan(data_files):
    return _do_merge_etherscan(data_files, [])


def _do_merge_etherscan(data_files, staking_addresses):  # pylint: disable=too-many-locals
    merge = False
    tx_ids = {}

    for file_id in data_files:
        for dr in data_files[file_id].data_rows:
            if not dr.t_record:
                continue

            wallet = dr.t_record.wallet[-abs(TransactionOutRecord.WALLET_ADDR_LEN) :]
            if wallet not in tx_ids:
                tx_ids[wallet] = {}

            if dr.row_dict["Txhash"] not in tx_ids[wallet]:
                tx_ids[wallet][dr.row_dict["Txhash"]] = []

            tx_ids[wallet][dr.row_dict["Txhash"]].append(
                MergeDataRow(dr, data_files[file_id], file_id)
            )

    for wallet in tx_ids:
        for txn in tx_ids[wallet]:
            if len(tx_ids[wallet][txn]) == 1:
                if config.debug:
                    sys.stderr.write(
                        "%smerge: %s:%s\n"
                        % (
                            Fore.BLUE,
                            tx_ids[wallet][txn][0].data_file_id.ljust(5),
                            tx_ids[wallet][txn][0].data_row,
                        )
                    )
                continue

            for t in tx_ids[wallet][txn]:
                if config.debug:
                    sys.stderr.write(
                        "%smerge: %s:%s\n" % (Fore.GREEN, t.data_file_id.ljust(5), t.data_row)
                    )

            t_ins, t_outs, t_fee = _get_ins_outs(tx_ids[wallet][txn])

            if config.debug:
                _output_records(t_ins, t_outs, t_fee)
                sys.stderr.write("%smerge:     consolidate:\n" % (Fore.YELLOW))

            _consolidate(tx_ids[wallet][txn], [TXNS, INTERNAL_TXNS])

            t_ins, t_outs, t_fee = _get_ins_outs(tx_ids[wallet][txn])

            if config.debug:
                _output_records(t_ins, t_outs, t_fee)
                sys.stderr.write("%smerge:     merge:\n" % (Fore.YELLOW))

            if t_fee:
                fee_quantity = t_fee.t_record.fee_quantity
                fee_asset = t_fee.t_record.fee_asset

            t_ins_orig = copy.copy(t_ins)
            if t_fee:
                _method_handling(t_ins, t_fee, staking_addresses)

            # Make trades
            if len(t_ins) == 1 and t_outs:
                _do_etherscan_multi_sell(t_ins, t_outs, t_fee)
            elif len(t_outs) == 1 and t_ins:
                _do_etherscan_multi_buy(t_ins, t_outs, t_fee)
            elif len(t_ins) > 1 and len(t_outs) > 1:
                # Multi-sell to multi-buy trade not supported
                sys.stderr.write(
                    "%sWARNING%s Merge failure for Txhash: %s\n"
                    % (Back.YELLOW + Fore.BLACK, Back.RESET + Fore.YELLOW, txn)
                )

                for mdr in tx_ids[wallet][txn]:
                    mdr.data_row.failure = UnexpectedContentError(
                        mdr.data_file.parser.in_header.index("Txhash"),
                        "Txhash",
                        mdr.data_row.row_dict["Txhash"],
                    )
                    sys.stderr.write(
                        "%srow[%s] %s\n"
                        % (
                            Fore.YELLOW,
                            mdr.data_file.parser.in_header_row_num + mdr.data_row.line_num,
                            mdr.data_row,
                        )
                    )
                continue

            if t_fee:
                # Split fees
                t_all = [t for t in t_ins_orig + t_outs if t.t_record]
                _do_fee_split(t_all, t_fee, fee_quantity, fee_asset)

            merge = True

            if config.debug:
                _output_records(t_ins_orig, t_outs, t_fee)

    return merge


def _get_ins_outs(tx_ids):
    t_ins = [
        t.data_row
        for t in tx_ids
        if t.data_row.t_record and t.data_row.t_record.t_type == TransactionOutRecord.TYPE_DEPOSIT
    ]
    t_outs = [
        t.data_row
        for t in tx_ids
        if t.data_row.t_record
        and t.data_row.t_record.t_type == TransactionOutRecord.TYPE_WITHDRAWAL
    ]
    t_fees = [
        t.data_row for t in tx_ids if t.data_row.t_record and t.data_row.t_record.fee_quantity
    ]

    if not t_fees:
        t_fee = None
    elif len(t_fees) == 1:
        t_fee = t_fees[0]
    else:
        raise ValueError("Multiple fees")

    return t_ins, t_outs, t_fee


def _consolidate(tx_ids, file_ids):
    tx_assets = {}

    for txn in list(tx_ids):
        if txn.data_file_id not in file_ids:
            return

        asset = txn.data_row.t_record.get_asset()
        if asset not in tx_assets:
            tx_assets[asset] = txn
            tx_assets[asset].quantity += txn.data_row.t_record.get_quantity()
        else:
            tx_assets[asset].quantity += txn.data_row.t_record.get_quantity()
            txn.data_row.t_record = None
            tx_ids.remove(txn)

    for asset in tx_assets:
        txn = tx_assets[asset]
        if txn.quantity > 0:
            txn.data_row.t_record.t_type = TransactionOutRecord.TYPE_DEPOSIT
            txn.data_row.t_record.buy_asset = asset
            txn.data_row.t_record.buy_quantity = txn.quantity
            txn.data_row.t_record.sell_asset = ""
            txn.data_row.t_record.sell_quantity = None
        elif tx_assets[asset].quantity < 0:
            txn.data_row.t_record.t_type = TransactionOutRecord.TYPE_WITHDRAWAL
            txn.data_row.t_record.buy_asset = ""
            txn.data_row.t_record.buy_quantity = None
            txn.data_row.t_record.sell_asset = asset
            txn.data_row.t_record.sell_quantity = abs(txn.quantity)
        else:
            if txn.data_row.t_record.fee_quantity:
                txn.data_row.t_record.t_type = TransactionOutRecord.TYPE_SPEND
                txn.data_row.t_record.buy_asset = ""
                txn.data_row.t_record.buy_quantity = None
                txn.data_row.t_record.sell_asset = asset
                txn.data_row.t_record.sell_quantity = Decimal(0)
            else:
                tx_ids.remove(txn)


def _output_records(t_ins, t_outs, t_fee):
    dup = bool(t_fee and t_fee in t_ins + t_outs)

    if t_fee:
        sys.stderr.write(
            "%smerge:   TR-F%s: %s\n" % (Fore.YELLOW, "*" if dup else "", t_fee.t_record)
        )

    for t_in in t_ins:
        sys.stderr.write(
            "%smerge:   TR-I%s: %s\n" % (Fore.YELLOW, "*" if t_fee is t_in else "", t_in.t_record)
        )
    for t_out in t_outs:
        sys.stderr.write(
            "%smerge:   TR-O%s: %s\n" % (Fore.YELLOW, "*" if t_fee is t_out else "", t_out.t_record)
        )


def _method_handling(t_ins, t_fee, staking_addresses):
    if t_fee.row_dict.get("Method") in (
        "Enter Staking",
        "Leave Staking",
        "Deposit",
        "Withdraw",
    ):
        if t_ins:
            staking = [
                t
                for t in t_ins
                if t.row_dict["ContractAddress"] in staking_addresses
                and t.row_dict["From"] != t_fee.row_dict["To"]
            ]
            if staking:
                if len(staking) == 1:
                    staking[0].t_record.t_type = TransactionOutRecord.TYPE_STAKING
                    t_ins.remove(staking[0])

                    if config.debug:
                        sys.stderr.write("%smerge:     staking:\n" % (Fore.YELLOW))
                else:
                    raise ValueError("Multiple transactions")


def _do_etherscan_multi_sell(t_ins, t_outs, t_fee):
    if config.debug:
        sys.stderr.write("%smerge:     trade sell(s):\n" % (Fore.YELLOW))

    tot_buy_quantity = 0

    buy_quantity = t_ins[0].t_record.buy_quantity
    buy_asset = t_ins[0].t_record.buy_asset

    if config.debug:
        sys.stderr.write(
            "%smerge:       buy_quantity=%s buy_asset=%s\n"
            % (
                Fore.YELLOW,
                TransactionOutRecord.format_quantity(buy_quantity),
                buy_asset,
            )
        )

    for cnt, t_out in enumerate(t_outs):
        if cnt < len(t_outs) - 1:
            split_buy_quantity = (buy_quantity / len(t_outs)).quantize(PRECISION)
            tot_buy_quantity += split_buy_quantity
        else:
            # Last t_out, use up remainder
            split_buy_quantity = buy_quantity - tot_buy_quantity

        if config.debug:
            sys.stderr.write(
                "%smerge:       split_buy_quantity=%s\n"
                % (
                    Fore.YELLOW,
                    TransactionOutRecord.format_quantity(split_buy_quantity),
                )
            )

        t_out.t_record.t_type = TransactionOutRecord.TYPE_TRADE
        t_out.t_record.buy_quantity = split_buy_quantity
        t_out.t_record.buy_asset = buy_asset
        if t_fee:
            t_out.t_record.note = _get_note(t_fee.row_dict)

    # Remove TR for buy now it's been added to each sell
    t_ins[0].t_record = None


def _do_etherscan_multi_buy(t_ins, t_outs, t_fee):
    if config.debug:
        sys.stderr.write("%smerge:     trade buy(s):\n" % (Fore.YELLOW))

    tot_sell_quantity = 0

    sell_quantity = t_outs[0].t_record.sell_quantity
    sell_asset = t_outs[0].t_record.sell_asset

    if config.debug:
        sys.stderr.write(
            "%smerge:       sell_quantity=%s sell_asset=%s\n"
            % (
                Fore.YELLOW,
                TransactionOutRecord.format_quantity(sell_quantity),
                sell_asset,
            )
        )

    for cnt, t_in in enumerate(t_ins):
        if cnt < len(t_ins) - 1:
            split_sell_quantity = (sell_quantity / len(t_ins)).quantize(PRECISION)
            tot_sell_quantity += split_sell_quantity
        else:
            # Last t_in, use up remainder
            split_sell_quantity = sell_quantity - tot_sell_quantity

        if config.debug:
            sys.stderr.write(
                "%smerge:       split_sell_quantity=%s\n"
                % (
                    Fore.YELLOW,
                    TransactionOutRecord.format_quantity(split_sell_quantity),
                )
            )

        t_in.t_record.t_type = TransactionOutRecord.TYPE_TRADE
        t_in.t_record.sell_quantity = split_sell_quantity
        t_in.t_record.sell_asset = sell_asset
        if t_fee:
            t_in.t_record.note = _get_note(t_fee.row_dict)

    # Remove TR for sell now it's been added to each buy
    t_outs[0].t_record = None


def _do_fee_split(t_all, t_fee, fee_quantity, fee_asset):
    if config.debug:
        sys.stderr.write("%smerge:     split fees:\n" % (Fore.YELLOW))
        sys.stderr.write(
            "%smerge:       fee_quantity=%s fee_asset=%s\n"
            % (
                Fore.YELLOW,
                TransactionOutRecord.format_quantity(fee_quantity),
                fee_asset,
            )
        )

    tot_fee_quantity = 0

    for cnt, t in enumerate(t_all):
        if cnt < len(t_all) - 1:
            split_fee_quantity = (fee_quantity / len(t_all)).quantize(PRECISION)
            tot_fee_quantity += split_fee_quantity
        else:
            # Last t, use up remainder
            split_fee_quantity = fee_quantity - tot_fee_quantity if fee_quantity else None

        if config.debug:
            sys.stderr.write(
                "%smerge:       split_fee_quantity=%s\n"
                % (
                    Fore.YELLOW,
                    TransactionOutRecord.format_quantity(split_fee_quantity),
                )
            )

        t.t_record.fee_quantity = split_fee_quantity
        t.t_record.fee_asset = fee_asset
        t.t_record.note = _get_note(t_fee.row_dict)

    # Remove TR for fee now it's been added to each withdrawal
    if t_fee.t_record and t_fee not in t_all:
        if t_fee.t_record.t_type == TransactionOutRecord.TYPE_SPEND:
            t_fee.t_record = None
        else:
            t_fee.t_record.fee_quantity = None
            t_fee.t_record.fee_asset = ""


DataMerge(
    "Etherscan fees & multi-token transactions",
    {
        TXNS: {"req": DataMerge.MAN, "obj": ETHERSCAN_TXNS},
        TOKENS: {"req": DataMerge.OPT, "obj": ETHERSCAN_TOKENS},
        NFTS: {"req": DataMerge.OPT, "obj": ETHERSCAN_NFTS},
        INTERNAL_TXNS: {"req": DataMerge.OPT, "obj": ETHERSCAN_INT},
    },
    merge_etherscan,
)
