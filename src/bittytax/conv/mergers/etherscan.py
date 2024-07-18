# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import copy
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from colorama import Fore

from ...bt_types import FileId, TrType
from ...config import config
from ...constants import WARNING
from ..datamerge import DataMerge, MergeDataRow, ParserRequired
from ..exceptions import UnexpectedContentError
from ..out_record import TransactionOutRecord
from ..parsers.etherscan import (
    _get_note,
    etherscan_int,
    etherscan_nfts,
    etherscan_tokens,
    etherscan_txns,
)

if TYPE_CHECKING:
    from ..datafile import DataFile
    from ..datarow import DataRow

PRECISION = Decimal("0." + "0" * 18)

TXNS = FileId("txn")
TOKENS = FileId("token")
NFTS = FileId("nft")
INTERNAL_TXNS = FileId("int")

STAKE_ADDRESSES = [
    "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82",  # PancakeSwap (BNB)
    "0x5fad6fbba4bba686ba9b8052cf0bd51699f38b93",  # MakiSwap (HT)
]


def merge_etherscan(data_files: Dict[FileId, "DataFile"]) -> bool:
    return _do_merge_etherscan(data_files, STAKE_ADDRESSES)


def _do_merge_etherscan(
    data_files: Dict[FileId, "DataFile"], staking_addresses: List[str]
) -> bool:  # pylint: disable=too-many-locals
    merge = False
    tx_ids: Dict[str, Dict[str, List[MergeDataRow]]] = {}

    for file_id in data_files:
        for dr in data_files[file_id].data_rows:
            if not dr.t_record:
                continue

            wallet = dr.t_record.wallet
            if wallet not in tx_ids:
                tx_ids[wallet] = {}

            if "Txhash" in dr.row_dict:
                dr.row_dict["Transaction Hash"] = dr.row_dict["Txhash"]

            if dr.row_dict["Transaction Hash"] not in tx_ids[wallet]:
                tx_ids[wallet][dr.row_dict["Transaction Hash"]] = []

            tx_ids[wallet][dr.row_dict["Transaction Hash"]].append(
                MergeDataRow(dr, data_files[file_id], file_id)
            )

    for _, wallet_tx_ids in tx_ids.items():
        for txn in wallet_tx_ids:
            if len(wallet_tx_ids[txn]) == 1:
                if config.debug:
                    sys.stderr.write(
                        f"{Fore.BLUE}merge: {wallet_tx_ids[txn][0].data_file_id:<5}:"
                        f"{wallet_tx_ids[txn][0].data_row}\n"
                    )
                continue

            for t in wallet_tx_ids[txn]:
                if config.debug:
                    sys.stderr.write(f"{Fore.GREEN}merge: {t.data_file_id:<5}:{t.data_row}\n")

            t_ins, t_outs, t_fee = _get_ins_outs(wallet_tx_ids[txn])

            if config.debug:
                _output_records(t_ins, t_outs, t_fee)
                sys.stderr.write(f"{Fore.YELLOW}merge:     consolidate:\n")

            _consolidate(wallet_tx_ids[txn], [TXNS, INTERNAL_TXNS])

            t_ins, t_outs, t_fee = _get_ins_outs(wallet_tx_ids[txn])

            if config.debug:
                _output_records(t_ins, t_outs, t_fee)
                sys.stderr.write(f"{Fore.YELLOW}merge:     merge:\n")

            if t_fee:
                if not t_fee.t_record:
                    raise RuntimeError("Missing t_record")

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
                sys.stderr.write(f"{WARNING} Merge failure for Transaction Hash: {txn}\n")

                for mdr in wallet_tx_ids[txn]:
                    if "Txhash" in mdr.data_row.row_dict:
                        mdr.data_row.failure = UnexpectedContentError(
                            mdr.data_file.parser.in_header.index("Txhash"),
                            "Txhash",
                            mdr.data_row.row_dict["Txhash"],
                        )
                    else:
                        mdr.data_row.failure = UnexpectedContentError(
                            mdr.data_file.parser.in_header.index("Transaction Hash"),
                            "Transaction Hash",
                            mdr.data_row.row_dict["Transaction Hash"],
                        )

                    if mdr.data_file.parser.in_header_row_num is None:
                        raise RuntimeError("Missing in_header_row_num")

                    sys.stderr.write(
                        f"{Fore.YELLOW}"
                        f"row[{mdr.data_file.parser.in_header_row_num + mdr.data_row.line_num}]"
                        f" {mdr.data_row}\n"
                    )
                continue

            if t_fee:
                if fee_quantity is None:
                    raise RuntimeError("Missing fee_quantity")

                # Split fees
                t_all = [t for t in t_ins_orig + t_outs if t.t_record]
                _do_fee_split(t_all, t_fee, fee_quantity, fee_asset)

            merge = True

            if config.debug:
                _output_records(t_ins_orig, t_outs, t_fee)

    return merge


def _get_ins_outs(
    tx_ids: List[MergeDataRow],
) -> Tuple[List["DataRow"], List["DataRow"], Optional["DataRow"]]:
    t_ins = [
        t.data_row
        for t in tx_ids
        if t.data_row.t_record and t.data_row.t_record.t_type is TrType.DEPOSIT
    ]
    t_outs = [
        t.data_row
        for t in tx_ids
        if t.data_row.t_record and t.data_row.t_record.t_type is TrType.WITHDRAWAL
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


def _consolidate(tx_ids: List[MergeDataRow], file_ids: List[str]) -> None:
    tx_assets = {}

    for txn in list(tx_ids):
        if txn.data_file_id not in file_ids:
            continue

        if not txn.data_row.t_record:
            continue

        asset = txn.data_row.t_record.get_asset()
        if asset not in tx_assets:
            tx_assets[asset] = txn
            tx_assets[asset].quantity += txn.data_row.t_record.get_quantity()
        else:
            tx_assets[asset].quantity += txn.data_row.t_record.get_quantity()
            txn.data_row.t_record = None
            tx_ids.remove(txn)

    for _, txn in tx_assets.items():
        if not txn.data_row.t_record:
            continue

        if txn.quantity > 0:
            txn.data_row.t_record.t_type = TrType.DEPOSIT
            txn.data_row.t_record.buy_asset = asset
            txn.data_row.t_record.buy_quantity = txn.quantity
            txn.data_row.t_record.sell_asset = ""
            txn.data_row.t_record.sell_quantity = None
        elif txn.quantity < 0:
            txn.data_row.t_record.t_type = TrType.WITHDRAWAL
            txn.data_row.t_record.buy_asset = ""
            txn.data_row.t_record.buy_quantity = None
            txn.data_row.t_record.sell_asset = asset
            txn.data_row.t_record.sell_quantity = abs(txn.quantity)
        else:
            if txn.data_row.t_record.fee_quantity:
                txn.data_row.t_record.t_type = TrType.SPEND
                txn.data_row.t_record.buy_asset = ""
                txn.data_row.t_record.buy_quantity = None
                txn.data_row.t_record.sell_asset = asset
                txn.data_row.t_record.sell_quantity = Decimal(0)
            else:
                tx_ids.remove(txn)


def _output_records(
    t_ins: List["DataRow"], t_outs: List["DataRow"], t_fee: Optional["DataRow"]
) -> None:
    dup = bool(t_fee and t_fee in t_ins + t_outs)

    if t_fee:
        sys.stderr.write(f"{Fore.YELLOW}merge:   TR-F{'*' if dup else ''}: {t_fee.t_record}\n")

    for t_in in t_ins:
        sys.stderr.write(
            f"{Fore.YELLOW}merge:   TR-I{'*' if t_fee is t_in else ''}: {t_in.t_record}\n"
        )
    for t_out in t_outs:
        sys.stderr.write(
            f"{Fore.YELLOW}merge:   TR-O{'*' if t_fee is t_out else ''}: {t_out.t_record}\n"
        )


def _method_handling(
    t_ins: List["DataRow"], t_fee: "DataRow", staking_addresses: List[str]
) -> None:
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
                    if not staking[0].t_record:
                        raise RuntimeError("Missing t_record")

                    staking[0].t_record.t_type = TrType.STAKING
                    t_ins.remove(staking[0])

                    if config.debug:
                        sys.stderr.write(f"{Fore.YELLOW}merge:     staking:\n")
                else:
                    raise ValueError("Multiple transactions")


def _do_etherscan_multi_sell(
    t_ins: List["DataRow"], t_outs: List["DataRow"], t_fee: Optional["DataRow"]
) -> None:
    if config.debug:
        sys.stderr.write(f"{Fore.YELLOW}merge:     trade sell(s):\n")

    tot_buy_quantity = Decimal(0)

    if not t_ins[0].t_record:
        raise RuntimeError("Missing t_record")

    buy_quantity = t_ins[0].t_record.buy_quantity
    buy_asset = t_ins[0].t_record.buy_asset

    if buy_quantity is None:
        raise RuntimeError("Missing buy_quantity")

    if config.debug:
        sys.stderr.write(
            f"{Fore.YELLOW}merge:       buy_quantity="
            f"{TransactionOutRecord.format_quantity(buy_quantity)} buy_asset={buy_asset}\n"
        )

    for cnt, t_out in enumerate(t_outs):
        if cnt < len(t_outs) - 1:
            split_buy_quantity = Decimal(buy_quantity / len(t_outs)).quantize(PRECISION)
            tot_buy_quantity += split_buy_quantity
        else:
            # Last t_out, use up remainder
            split_buy_quantity = buy_quantity - tot_buy_quantity

        if config.debug:
            sys.stderr.write(
                f"{Fore.YELLOW}merge:       split_buy_quantity="
                f"{TransactionOutRecord.format_quantity(split_buy_quantity)}\n"
            )

        if not t_out.t_record:
            raise RuntimeError("Missing t_record")

        t_out.t_record.t_type = TrType.TRADE
        t_out.t_record.buy_quantity = split_buy_quantity
        t_out.t_record.buy_asset = buy_asset
        if t_fee:
            t_out.t_record.note = _get_note(t_fee.row_dict)

    # Remove TR for buy now it's been added to each sell
    t_ins[0].t_record = None


def _do_etherscan_multi_buy(
    t_ins: List["DataRow"], t_outs: List["DataRow"], t_fee: Optional["DataRow"]
) -> None:
    if config.debug:
        sys.stderr.write(f"{Fore.YELLOW}merge:     trade buy(s):\n")

    tot_sell_quantity = Decimal(0)

    if not t_outs[0].t_record:
        raise RuntimeError("Missing t_record")

    sell_quantity = t_outs[0].t_record.sell_quantity
    sell_asset = t_outs[0].t_record.sell_asset

    if sell_quantity is None:
        raise RuntimeError("Missing sell_quantity")

    if config.debug:
        sys.stderr.write(
            f"{Fore.YELLOW}merge:       sell_quantity="
            f"{TransactionOutRecord.format_quantity(sell_quantity)} sell_asset={sell_asset}\n"
        )

    for cnt, t_in in enumerate(t_ins):
        if cnt < len(t_ins) - 1:
            split_sell_quantity = Decimal(sell_quantity / len(t_ins)).quantize(PRECISION)
            tot_sell_quantity += split_sell_quantity
        else:
            # Last t_in, use up remainder
            split_sell_quantity = sell_quantity - tot_sell_quantity

        if config.debug:
            sys.stderr.write(
                f"{Fore.YELLOW}merge:       split_sell_quantity="
                f"{TransactionOutRecord.format_quantity(split_sell_quantity)}\n"
            )

        if not t_in.t_record:
            raise RuntimeError("Missing t_record")

        t_in.t_record.t_type = TrType.TRADE
        t_in.t_record.sell_quantity = split_sell_quantity
        t_in.t_record.sell_asset = sell_asset
        if t_fee:
            t_in.t_record.note = _get_note(t_fee.row_dict)

    # Remove TR for sell now it's been added to each buy
    t_outs[0].t_record = None


def _do_fee_split(
    t_all: List["DataRow"],
    t_fee: "DataRow",
    fee_quantity: Decimal,
    fee_asset: str,
) -> None:
    if config.debug:
        sys.stderr.write(f"{Fore.YELLOW}merge:     split fees:\n")
        sys.stderr.write(
            f"{Fore.YELLOW}merge:       fee_quantity="
            f"{TransactionOutRecord.format_quantity(fee_quantity)} fee_asset={fee_asset}\n"
        )

    tot_fee_quantity = Decimal(0)

    for cnt, t in enumerate(t_all):
        if cnt < len(t_all) - 1:
            split_fee_quantity = Decimal(fee_quantity / len(t_all)).quantize(PRECISION)
            tot_fee_quantity += split_fee_quantity
        else:
            # Last t, use up remainder
            split_fee_quantity = fee_quantity - tot_fee_quantity

        if config.debug:
            sys.stderr.write(
                f"{Fore.YELLOW}merge:       split_fee_quantity="
                f"{TransactionOutRecord.format_quantity(split_fee_quantity)}\n"
            )

        if not t.t_record:
            raise RuntimeError("Missing t_record")

        t.t_record.fee_quantity = split_fee_quantity
        t.t_record.fee_asset = fee_asset
        t.t_record.note = _get_note(t_fee.row_dict)

    # Remove TR for fee now it's been added to each withdrawal
    if t_fee.t_record and t_fee not in t_all:
        if t_fee.t_record.t_type is TrType.SPEND:
            t_fee.t_record = None
        else:
            t_fee.t_record.fee_quantity = None
            t_fee.t_record.fee_asset = ""


DataMerge(
    "Etherscan fees & multi-token transactions",
    {
        TXNS: {"req": ParserRequired.MANDATORY, "obj": etherscan_txns},
        TOKENS: {"req": ParserRequired.OPTIONAL, "obj": etherscan_tokens},
        NFTS: {"req": ParserRequired.OPTIONAL, "obj": etherscan_nfts},
        INTERNAL_TXNS: {"req": ParserRequired.OPTIONAL, "obj": etherscan_int},
    },
    merge_etherscan,
)
