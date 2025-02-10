# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import copy
import sys
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import TYPE_CHECKING, Dict, List, NewType, Optional, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import AssetSymbol, TrType
from ...config import config
from ...constants import WARNING
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import (
    DataFilenameError,
    DataRowError,
    MissingValueError,
    UnexpectedContentError,
    UnexpectedTypeError,
)
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

PRECISION = Decimal("0." + "0" * 18)

WORKSHEET_NAME = "DeFi Taxes"

Chain = NewType("Chain", str)
TxHash = NewType("TxHash", str)
VaultId = NewType("VaultId", str)

getcontext().prec = 30


@dataclass
class TxRecord:
    quantity: Decimal
    asset: AssetSymbol
    value: Optional[Decimal]
    classification: str
    address: str
    chain: Chain
    vault_id: VaultId
    data_row: "DataRow"


@dataclass
class VaultRecord:
    quantity: Decimal = Decimal(0)
    value: Optional[Decimal] = None


def parse_defi_taxes(
    data_rows: List["DataRow"], parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    tx_ids: Dict[Chain, Dict[TxHash, List["DataRow"]]] = {}
    vaults: Dict[VaultId, Dict[AssetSymbol, VaultRecord]] = {}
    my_addresses = []

    for dr in data_rows:
        if not dr.row_dict["timestamp"]:
            # Skip empty rows
            continue

        chain = Chain(dr.row_dict["chain"])
        if chain not in tx_ids:
            tx_ids[chain] = {}

        tx_hash = TxHash(dr.row_dict["transaction hash"])
        if tx_hash not in tx_ids[chain]:
            tx_ids[chain][tx_hash] = [dr]
        else:
            tx_ids[chain][tx_hash].append(dr)

        dr.timestamp = DataParser.parse_timestamp(int(dr.row_dict["timestamp"]))
        dr.tx_raw = TxRawPos(
            parser.in_header.index("transaction hash"),
            parser.in_header.index("source address"),
            parser.in_header.index("destination address"),
        )

        # Try to identify own addresses
        if dr.row_dict["destination address"] == "network":
            if dr.row_dict["source address"] not in my_addresses:
                my_addresses.append(dr.row_dict["source address"])

    if config.debug:
        sys.stderr.write(f"{Fore.CYAN}conv: my addresses: {', '.join(my_addresses)}\n")

    for data_row in data_rows:
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f"row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if data_row.parsed:
            continue

        try:
            _parse_defi_taxes_row(
                data_rows, tx_ids, vaults, parser, data_row, my_addresses, kwargs["filename"]
            )
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, AttributeError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_defi_taxes_row(
    data_rows: List["DataRow"],
    tx_ids: Dict[Chain, Dict[TxHash, List["DataRow"]]],
    vaults: Dict[VaultId, Dict[AssetSymbol, VaultRecord]],
    parser: DataParser,
    data_row: "DataRow",
    my_addresses: List[str],
    filename: str,
) -> None:
    row_dict = data_row.row_dict

    if not row_dict["timestamp"]:
        # Skip empty rows
        return

    chain = Chain(row_dict["chain"])
    tx_hash = TxHash(row_dict["transaction hash"])

    if tx_hash:
        tx_rows = tx_ids[chain][tx_hash]
        tx_ins, tx_outs, tx_fee = _get_ins_outs(tx_rows, my_addresses, filename)
    else:
        # Must be a manual transaction
        tx_rows = [data_row]
        tx_ins, tx_outs, tx_fee = _get_ins_outs([data_row], my_addresses, filename)

    if config.debug:
        _output_tx_rows(tx_ins, tx_outs, tx_fee)

    ctx_ins, ctx_outs = _consolidate_tx(tx_ins, tx_outs, tx_hash)

    if config.debug:
        if ctx_ins != tx_ins or ctx_outs != tx_outs:
            sys.stderr.write(f"{Fore.GREEN}conv:  consolidated tx's\n")
            _output_tx_rows(ctx_ins, ctx_outs, tx_fee)

    last_tx_pos = len(tx_rows) - 1
    _make_t_record(ctx_ins, ctx_outs, tx_fee, parser, tx_rows, vaults)
    new_rows = tx_rows[last_tx_pos + 1 :]

    if new_rows:
        new_tx_pos = data_rows.index(tx_rows[last_tx_pos]) + 1
        data_rows[new_tx_pos:new_tx_pos] = new_rows

    if config.debug:
        for dr in tx_rows:
            if dr.t_record:
                print(f"{Fore.CYAN}conv:    TR {dr.t_record}")


def _make_t_record(
    tx_ins: List[TxRecord],
    tx_outs: List[TxRecord],
    tx_fee: Optional[TxRecord],
    parser: DataParser,
    tx_rows: List["DataRow"],
    vaults: Dict[VaultId, Dict[AssetSymbol, VaultRecord]],
) -> None:

    if tx_fee and not tx_ins and not tx_outs:
        # Fee only
        tx_fee.data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            tx_fee.data_row.timestamp,
            sell_quantity=Decimal(0),
            sell_asset=tx_fee.asset,
            fee_quantity=tx_fee.quantity,
            fee_asset=tx_fee.asset,
            fee_value=tx_fee.value,
            wallet=_get_wallet(tx_fee.chain, tx_fee.address),
            note=_get_note(tx_fee.data_row),
        )
    elif len(tx_ins) == 1 and not tx_outs:
        # Single transfer in
        tx_in = tx_ins[0]

        if tx_in.classification.startswith("transfer in") or not tx_in.classification:
            tx_in.data_row.t_record = _make_buy(TrType.DEPOSIT, tx_in, tx_fee)
        elif tx_in.classification.startswith(("withdraw", "unstake", "exit vault")):
            try:
                _do_unstake(tx_in, vaults, tx_rows, exit_vault="exit" in tx_in.classification)
            except ValueError as e:
                if tx_in.vault_id:
                    raise UnexpectedContentError(
                        parser.in_header.index("vault id"), "vault id", tx_in.vault_id
                    ) from e
                raise MissingValueError(parser.in_header.index("vault id"), "vault id", "") from e
            except AttributeError as e:
                raise UnexpectedContentError(
                    parser.in_header.index("token symbol"), "token symbol", tx_in.asset
                ) from e
            _do_fee_split(tx_fee, tx_rows)
        elif tx_in.classification.startswith(("mint", "swap")):
            tx_in.data_row.t_record = _make_buy(TrType.AIRDROP, tx_in, tx_fee)
        elif tx_in.classification.startswith("spam"):
            # Ignore spam Airdrops
            pass
        elif tx_in.classification.startswith("claim reward"):
            tx_in.data_row.t_record = _make_buy(TrType.STAKING_REWARD, tx_in, tx_fee)
        elif tx_in.classification == "balance adjustment":
            tx_in.data_row.t_record = _make_buy(TrType.AIRDROP, tx_in, tx_fee)
        elif tx_in.classification.startswith("transfer from your account elsewhere"):
            if tx_in.data_row.row_dict["vault id"]:
                _do_bridge_out(tx_in, vaults, tx_rows)
                _do_fee_split(tx_fee, tx_rows)
            else:
                tx_in.data_row.t_record = _make_buy(TrType.DEPOSIT, tx_in, tx_fee)
        elif tx_in.classification == "fee":
            # This looks like bridged tokens without a vault
            tx_in.data_row.t_record = _make_buy(TrType.DEPOSIT, tx_in, tx_fee)
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("classification"), "classification", tx_in.classification
            )
    elif len(tx_outs) == 1 and not tx_ins:
        # Single transfer out
        tx_out = tx_outs[0]

        if tx_out.classification.startswith("transfer out") or not tx_out.classification:
            tx_out.data_row.t_record = _make_sell(TrType.WITHDRAWAL, tx_out, tx_fee)
        elif tx_out.classification.startswith(("deposit", "stake")):
            tx_out.data_row.t_record = _make_sell(TrType.STAKE, tx_out, tx_fee)
            try:
                _do_stake(tx_out, vaults)
            except ValueError as e:
                _remove_t_records(tx_rows)
                raise MissingValueError(parser.in_header.index("vault id"), "vault id", "") from e
        elif tx_out.classification.startswith("transfer to your account elsewhere"):
            tx_out.data_row.t_record = _make_sell(TrType.WITHDRAWAL, tx_out, tx_fee)
            if tx_out.data_row.row_dict["vault id"]:
                _do_bridge_in(tx_out, vaults)
        elif tx_out.classification == "fee":
            tx_out.data_row.t_record = _make_sell(TrType.SPEND, tx_out, tx_fee)
        elif tx_out.classification == "balance adjustment":
            tx_out.value = Decimal(0)
            tx_out.data_row.t_record = _make_sell(TrType.SPEND, tx_out, tx_fee)
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("classification"), "classification", tx_out.classification
            )
    elif len(tx_ins) == 1 and len(tx_outs) == 1:
        # Single transfer in/out
        tx_in = tx_ins[0]
        tx_out = tx_outs[0]
        if (
            tx_in.classification.startswith(
                (
                    "swap",
                    "wrap",
                    "unwrap",
                    "mint",
                    "deposit",
                    "deposit with receipt",
                    "withdraw with receipt",
                    "transfer in",
                    "transfer out",
                )
            )
            or not tx_in.classification
        ):
            _next_free_row(tx_rows).t_record = _make_trade(tx_in, tx_out, tx_fee)
        elif tx_in.classification.startswith(("stake", "stake & claim reward")):
            _next_free_row(tx_rows).t_record = _make_sell(TrType.STAKE, tx_out, tx_fee)
            _next_free_row(tx_rows).t_record = _make_buy(TrType.STAKING_REWARD, tx_in, tx_fee)
            _do_fee_split(tx_fee, tx_rows)
            try:
                _do_stake(tx_out, vaults)
            except ValueError as e:
                _remove_t_records(tx_rows)
                raise MissingValueError(parser.in_header.index("vault id"), "vault id", "") from e

        elif tx_in.classification.startswith("interaction between your accounts"):
            _make_transfer(tx_in, tx_out, tx_fee, tx_rows)
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("classification"), "classification", tx_in.classification
            )
    elif len(tx_ins) > 1 and not tx_outs:
        # Multi transfer in
        for tx_in in tx_ins:
            if tx_in.classification.startswith(("mint", "swap")) or not tx_in.classification:
                tx_in.data_row.t_record = TransactionOutRecord(
                    TrType.AIRDROP,
                    tx_in.data_row.timestamp,
                    buy_quantity=tx_in.quantity,
                    buy_asset=tx_in.asset,
                    buy_value=tx_in.value,
                    wallet=_get_wallet(tx_in.chain, tx_in.address),
                    note=_get_note(tx_in.data_row),
                )
            elif tx_in.classification.startswith("borrow"):
                tx_in.data_row.t_record = TransactionOutRecord(
                    TrType.LOAN,
                    tx_in.data_row.timestamp,
                    buy_quantity=tx_in.quantity,
                    buy_asset=tx_in.asset,
                    buy_value=tx_in.value,
                    wallet=_get_wallet(tx_in.chain, tx_in.address),
                    note=_get_note(tx_in.data_row),
                )
            elif tx_in.classification.startswith("claim reward"):
                tx_in.data_row.t_record = TransactionOutRecord(
                    TrType.STAKING_REWARD,
                    tx_in.data_row.timestamp,
                    buy_quantity=tx_in.quantity,
                    buy_asset=tx_in.asset,
                    buy_value=tx_in.value,
                    wallet=_get_wallet(tx_in.chain, tx_in.address),
                    note=_get_note(tx_in.data_row),
                )
            elif tx_in.classification.startswith("transfer in"):
                tx_in.data_row.t_record = TransactionOutRecord(
                    TrType.DEPOSIT,
                    tx_in.data_row.timestamp,
                    buy_quantity=tx_in.quantity,
                    buy_asset=tx_in.asset,
                    buy_value=tx_in.value,
                    wallet=_get_wallet(tx_in.chain, tx_in.address),
                    note=_get_note(tx_in.data_row),
                )
            elif tx_in.classification.startswith(
                (
                    "unstake & claim reward",
                    "exit vault & claim reward",
                    "exit vault",
                    "unstake",
                    "withdraw",
                    "deposit",
                )
            ):
                if tx_in.data_row.row_dict["vault id"]:
                    try:
                        _do_unstake(
                            tx_in, vaults, tx_rows, exit_vault="exit" in tx_in.classification
                        )
                    except ValueError as e:
                        if tx_in.vault_id:
                            raise UnexpectedContentError(
                                parser.in_header.index("vault id"), "vault id", tx_in.vault_id
                            ) from e
                        raise MissingValueError(
                            parser.in_header.index("vault id"), "vault id", ""
                        ) from e
                    except AttributeError as e:
                        raise UnexpectedContentError(
                            parser.in_header.index("token symbol"), "token symbol", tx_in.asset
                        ) from e
                else:
                    _next_free_row(tx_rows).t_record = TransactionOutRecord(
                        TrType.STAKING_REWARD,
                        tx_in.data_row.timestamp,
                        buy_quantity=tx_in.quantity,
                        buy_asset=tx_in.asset,
                        buy_value=tx_in.value,
                        wallet=_get_wallet(tx_in.chain, tx_in.address),
                        note=_get_note(tx_in.data_row),
                    )
            elif tx_in.classification.startswith("spam"):
                # Ignore spam Airdrops
                pass
            else:
                raise UnexpectedTypeError(
                    parser.in_header.index("classification"), "classification", tx_in.classification
                )
        _do_fee_split(tx_fee, tx_rows)
    elif len(tx_outs) > 1 and not tx_ins:
        # Multi transfer out
        for tx_out in tx_outs:
            if tx_out.classification.startswith("swap") or tx_out.classification == "":
                tx_out.data_row.t_record = TransactionOutRecord(
                    TrType.SPEND,
                    tx_out.data_row.timestamp,
                    sell_quantity=abs(tx_out.quantity),
                    sell_asset=tx_out.asset,
                    sell_value=abs(tx_out.value) if tx_out.value else None,
                    wallet=_get_wallet(tx_out.chain, tx_out.address),
                    note=_get_note(tx_out.data_row),
                )
            elif tx_out.classification.startswith("repay"):
                tx_out.data_row.t_record = TransactionOutRecord(
                    TrType.LOAN_REPAYMENT,
                    tx_out.data_row.timestamp,
                    sell_quantity=abs(tx_out.quantity),
                    sell_asset=tx_out.asset,
                    sell_value=abs(tx_out.value) if tx_out.value else None,
                    wallet=_get_wallet(tx_out.chain, tx_out.address),
                    note=_get_note(tx_out.data_row),
                )
            elif tx_out.classification.startswith("transfer out"):
                tx_out.data_row.t_record = TransactionOutRecord(
                    TrType.WITHDRAWAL,
                    tx_out.data_row.timestamp,
                    sell_quantity=abs(tx_out.quantity),
                    sell_asset=tx_out.asset,
                    sell_value=abs(tx_out.value) if tx_out.value else None,
                    wallet=_get_wallet(tx_out.chain, tx_out.address),
                    note=_get_note(tx_out.data_row),
                )
            elif tx_out.classification.startswith(("deposit", "stake")):
                tx_out.data_row.t_record = TransactionOutRecord(
                    TrType.STAKE,
                    tx_out.data_row.timestamp,
                    sell_quantity=abs(tx_out.quantity),
                    sell_asset=tx_out.asset,
                    sell_value=abs(tx_out.value) if tx_out.value else None,
                    wallet=_get_wallet(tx_out.chain, tx_out.address),
                    note=_get_note(tx_out.data_row),
                )
                try:
                    _do_stake(tx_out, vaults)
                except ValueError as e:
                    _remove_t_records(tx_rows)
                    raise MissingValueError(
                        parser.in_header.index("vault id"), "vault id", ""
                    ) from e
            else:
                raise UnexpectedTypeError(
                    parser.in_header.index("classification"),
                    "classification",
                    tx_out.classification,
                )
        _do_fee_split(tx_fee, tx_rows)
    elif len(tx_ins) == 1 and tx_outs:
        # Single transfer in, multi transfer out
        if (
            tx_ins[0]
            .data_row.row_dict["classification"]
            .startswith(("swap", "mint", "deposit", "deposit with receipt", "stake"))
            or not tx_ins[0].data_row.row_dict["classification"]
        ):
            # Treat the "deposit" as "deposit with receipt" as we are getting a token back here
            _make_multi_sell(tx_ins[0], tx_outs, tx_rows)
            _do_fee_split(tx_fee, tx_rows)
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("classification"), "classification", tx_ins[0].classification
            )
    elif len(tx_outs) == 1 and tx_ins:
        # Single transfer out, multi transfer in
        if (
            tx_outs[0]
            .data_row.row_dict["classification"]
            .startswith(("swap", "mint", "withdraw with receipt"))
            or not tx_outs[0].data_row.row_dict["classification"]
        ):
            _make_multi_buy(tx_outs[0], tx_ins, tx_rows)
            _do_fee_split(tx_fee, tx_rows)
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("classification"),
                "classification",
                tx_outs[0].classification,
            )
    else:
        # Multi transfer in/out
        for tx_in in tx_ins:
            tx_in.data_row.t_record = TransactionOutRecord(
                TrType.AIRDROP,
                tx_in.data_row.timestamp,
                buy_quantity=tx_in.quantity,
                buy_asset=tx_in.asset,
                buy_value=tx_in.value,
                wallet=_get_wallet(tx_in.chain, tx_in.address),
                note=_get_note(tx_in.data_row),
            )
        for tx_out in tx_outs:
            tx_out.data_row.t_record = TransactionOutRecord(
                TrType.SPEND,
                tx_out.data_row.timestamp,
                sell_quantity=abs(tx_out.quantity),
                sell_asset=tx_out.asset,
                sell_value=abs(tx_out.value) if tx_out.value else None,
                wallet=_get_wallet(tx_out.chain, tx_out.address),
                note=_get_note(tx_out.data_row),
            )
        _do_fee_split(tx_fee, tx_rows)

    for dr in tx_rows:
        dr.parsed = True


def _make_buy(t_type: TrType, tx_in: TxRecord, tx_fee: Optional[TxRecord]) -> TransactionOutRecord:
    return TransactionOutRecord(
        t_type,
        tx_in.data_row.timestamp,
        buy_quantity=tx_in.quantity,
        buy_asset=tx_in.asset,
        buy_value=tx_in.value,
        fee_quantity=tx_fee.quantity if tx_fee else None,
        fee_asset=tx_fee.asset if tx_fee else "",
        fee_value=tx_fee.value if tx_fee else None,
        wallet=_get_wallet(tx_in.chain, tx_in.address),
        note=_get_note(tx_in.data_row),
    )


def _make_sell(
    t_type: TrType, tx_out: TxRecord, tx_fee: Optional[TxRecord]
) -> TransactionOutRecord:
    return TransactionOutRecord(
        t_type,
        tx_out.data_row.timestamp,
        sell_quantity=abs(tx_out.quantity),
        sell_asset=tx_out.asset,
        sell_value=abs(tx_out.value) if tx_out.value is not None else None,
        fee_quantity=tx_fee.quantity if tx_fee else None,
        fee_asset=tx_fee.asset if tx_fee else "",
        fee_value=tx_fee.value if tx_fee else None,
        wallet=_get_wallet(tx_out.chain, tx_out.address),
        note=_get_note(tx_out.data_row),
    )


def _make_trade(
    tx_in: TxRecord, tx_out: TxRecord, tx_fee: Optional[TxRecord]
) -> TransactionOutRecord:
    return TransactionOutRecord(
        TrType.TRADE,
        tx_in.data_row.timestamp,
        buy_quantity=tx_in.quantity,
        buy_asset=tx_in.asset,
        buy_value=tx_in.value,
        sell_quantity=abs(tx_out.quantity),
        sell_asset=tx_out.asset,
        sell_value=abs(tx_out.value) if tx_out.value is not None else None,
        fee_quantity=tx_fee.quantity if tx_fee else None,
        fee_asset=tx_fee.asset if tx_fee else "",
        fee_value=tx_fee.value if tx_fee else None,
        wallet=_get_wallet(tx_in.chain, tx_in.address),
        note=_get_note(tx_in.data_row),
    )


def _make_transfer(
    tx_in: TxRecord,
    tx_out: TxRecord,
    tx_fee: Optional[TxRecord],
    tx_rows: List["DataRow"],
) -> None:
    _next_free_row(tx_rows).t_record = TransactionOutRecord(
        TrType.WITHDRAWAL,
        tx_out.data_row.timestamp,
        sell_quantity=abs(tx_out.quantity),
        sell_asset=tx_out.asset,
        sell_value=abs(tx_out.value) if tx_out.value else None,
        fee_quantity=tx_fee.quantity if tx_fee else None,
        fee_asset=tx_fee.asset if tx_fee else "",
        fee_value=tx_fee.value if tx_fee else None,
        wallet=_get_wallet(tx_out.chain, tx_out.address),
        note=_get_note(tx_out.data_row),
    )

    next_row = _next_free_row(tx_rows)
    next_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        tx_in.data_row.timestamp,
        buy_quantity=tx_in.quantity,
        buy_asset=tx_in.asset,
        buy_value=tx_in.value,
        wallet=_get_wallet(tx_in.chain, tx_in.address),
        note=_get_note(tx_in.data_row),
    )
    next_row.worksheet_name = _get_worksheet_name(tx_in.chain, tx_in.address)


def _make_multi_sell(tx_in: TxRecord, tx_outs: List[TxRecord], tx_rows: List["DataRow"]) -> None:
    tot_buy_quantity = Decimal(0)
    tot_buy_value = Decimal(0)

    buy_quantity = tx_in.quantity
    buy_asset = tx_in.asset
    buy_value = tx_in.value

    for cnt, tx_out in enumerate(tx_outs):
        if cnt < len(tx_outs) - 1:
            split_buy_quantity = Decimal(buy_quantity / len(tx_outs)).quantize(PRECISION)
            tot_buy_quantity += split_buy_quantity
            if buy_value:
                split_buy_value = Decimal(buy_value / len(tx_outs)).quantize(PRECISION)
                tot_buy_value += split_buy_value
            else:
                split_buy_value = None
        else:
            # Last tx_out, use up remainder
            split_buy_quantity = buy_quantity - tot_buy_quantity
            if buy_value:
                split_buy_value = buy_value - tot_buy_value
            else:
                split_buy_value = None

        _next_free_row(tx_rows).t_record = TransactionOutRecord(
            TrType.TRADE,
            tx_out.data_row.timestamp,
            buy_quantity=split_buy_quantity,
            buy_asset=buy_asset,
            buy_value=split_buy_value,
            sell_quantity=abs(tx_out.quantity),
            sell_asset=tx_out.asset,
            sell_value=abs(tx_out.value) if tx_out.value else None,
            wallet=_get_wallet(tx_out.chain, tx_out.address),
            note=_get_note(tx_out.data_row),
        )


def _make_multi_buy(tx_out: TxRecord, tx_ins: List[TxRecord], tx_rows: List["DataRow"]) -> None:
    tot_sell_quantity = Decimal(0)
    tot_sell_value = Decimal(0)

    sell_quantity = abs(tx_out.quantity)
    sell_asset = tx_out.asset
    sell_value = abs(tx_out.value) if tx_out.value else None

    for cnt, tx_in in enumerate(tx_ins):
        if cnt < len(tx_ins) - 1:
            split_sell_quantity = Decimal(sell_quantity / len(tx_ins)).quantize(PRECISION)
            tot_sell_quantity += split_sell_quantity
            if sell_value:
                split_sell_value = Decimal(sell_value / len(tx_ins)).quantize(PRECISION)
                tot_sell_value += split_sell_value
            else:
                split_sell_value = None
        else:
            # Last tx_in, use up remainder
            split_sell_quantity = sell_quantity - tot_sell_quantity
            if sell_value:
                split_sell_value = sell_value - tot_sell_value
            else:
                split_sell_value = None

        _next_free_row(tx_rows).t_record = TransactionOutRecord(
            TrType.TRADE,
            tx_in.data_row.timestamp,
            buy_quantity=tx_in.quantity,
            buy_asset=tx_in.asset,
            buy_value=tx_in.value,
            sell_quantity=split_sell_quantity,
            sell_asset=sell_asset,
            sell_value=split_sell_value,
            wallet=_get_wallet(tx_in.chain, tx_in.address),
            note=_get_note(tx_in.data_row),
        )


def _do_stake(tx_out: TxRecord, vaults: Dict[VaultId, Dict[AssetSymbol, VaultRecord]]) -> None:
    vault_id = tx_out.vault_id
    asset = AssetSymbol(tx_out.asset)
    quantity = abs(tx_out.quantity)

    if not vault_id:
        raise ValueError("Missing vault id")

    if vault_id not in vaults:
        vaults[vault_id] = {}

    if asset not in vaults[vault_id]:
        vaults[vault_id][asset] = VaultRecord()

    vaults[vault_id][asset].quantity += quantity

    if config.debug:
        sys.stderr.write(
            f"{Fore.CYAN}stake:   {vault_id}: "
            f"{asset}={vaults[vault_id][asset].quantity.normalize():0,f} "
            f"(+{quantity.normalize():0,f})\n"
        )


def _do_unstake(
    tx_in: TxRecord,
    vaults: Dict[VaultId, Dict[AssetSymbol, VaultRecord]],
    tx_rows: List["DataRow"],
    exit_vault: bool = False,
) -> None:
    vault_id = tx_in.vault_id
    quantity = tx_in.quantity
    asset = AssetSymbol(tx_in.asset)
    rate = DataParser.convert_currency(
        tx_in.data_row.row_dict["USD rate"], "USD", tx_in.data_row.timestamp
    )
    staking_reward = None

    if vault_id not in vaults:
        raise ValueError(f"Vault: {vault_id} does not exist")

    if asset not in vaults[vault_id]:
        raise AttributeError(f"Vault: {vault_id} does not contain {asset}")

    vaults[vault_id][asset].quantity -= quantity

    if config.debug:
        sys.stderr.write(
            f"{Fore.CYAN}unstake: {vault_id}: "
            f"{asset}={vaults[vault_id][asset].quantity.normalize():0,f} "
            f"(-{quantity.normalize():0,f})\n"
        )

    if vaults[vault_id][asset].quantity < 0:
        # Getting back more than we staked
        staking_reward = abs(vaults[vault_id][asset].quantity)
        vaults[vault_id][asset].quantity = Decimal(0)
        quantity -= staking_reward

    _next_free_row(tx_rows).t_record = TransactionOutRecord(
        TrType.UNSTAKE,
        tx_in.data_row.timestamp,
        buy_quantity=quantity,
        buy_asset=asset,
        buy_value=quantity * rate if rate else None,
        wallet=_get_wallet(tx_in.chain, tx_in.address),
        note=_get_note(tx_in.data_row),
    )

    if staking_reward:
        _next_free_row(tx_rows).t_record = TransactionOutRecord(
            TrType.STAKING_REWARD,
            tx_in.data_row.timestamp,
            buy_quantity=staking_reward,
            buy_asset=asset,
            buy_value=staking_reward * rate if rate else None,
            wallet=_get_wallet(tx_in.chain, tx_in.address),
            note=_get_note(tx_in.data_row),
        )

    if exit_vault:
        # Check all holdings are empty
        for asset, vault_record in vaults[vault_id].items():
            if vault_record.quantity > Decimal(0):
                # Unstake before disposal so audit will balance
                _next_free_row(tx_rows).t_record = TransactionOutRecord(
                    TrType.UNSTAKE,
                    tx_in.data_row.timestamp,
                    buy_quantity=vault_record.quantity,
                    buy_asset=asset,
                    buy_value=Decimal(0),
                    wallet=_get_wallet(tx_in.chain, tx_in.address),
                    note=_get_note(tx_in.data_row),
                )
                _next_free_row(tx_rows).t_record = TransactionOutRecord(
                    TrType.SPEND,
                    tx_in.data_row.timestamp,
                    sell_quantity=vault_record.quantity,
                    sell_asset=asset,
                    sell_value=Decimal(0),
                    wallet=_get_wallet(tx_in.chain, tx_in.address),
                    note=_get_note(tx_in.data_row),
                )
                sys.stderr.write(
                    f"{WARNING} Closing vault:{vault_id} which is not empty, adding disposal for "
                    f"{vault_record.quantity.normalize():0,f} {asset}\n"
                )


def _do_bridge_in(tx_out: TxRecord, vaults: Dict[VaultId, Dict[AssetSymbol, VaultRecord]]) -> None:
    vault_id = tx_out.vault_id
    quantity = abs(tx_out.quantity)
    asset = AssetSymbol(tx_out.asset)
    value = abs(tx_out.value) if tx_out.value else None

    if not vault_id:
        raise ValueError("Missing vault id")

    if vault_id not in vaults:
        vaults[vault_id] = {}

    vaults[vault_id][asset] = VaultRecord(quantity, value)

    if config.debug:
        sys.stderr.write(
            f"{Fore.CYAN}bridge: {vault_id}: "
            f"{asset}={vaults[vault_id][asset].quantity.normalize():0,f} "
            f"(+{quantity.normalize():0,f})\n"
        )


def _do_bridge_out(
    tx_in: TxRecord, vaults: Dict[VaultId, Dict[AssetSymbol, VaultRecord]], tx_rows: List["DataRow"]
) -> None:
    vault_id = tx_in.vault_id
    quantity = tx_in.quantity
    asset = AssetSymbol(tx_in.asset)
    value = tx_in.value

    if vault_id not in vaults:
        raise ValueError(f"Vault: {vault_id} does not exist")

    if asset in vaults[vault_id]:
        # Getting back the exact same asset
        _next_free_row(tx_rows).t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            tx_in.data_row.timestamp,
            buy_quantity=vaults[vault_id][asset].quantity,
            buy_asset=asset,
            buy_value=vaults[vault_id][asset].value,
            wallet=_get_wallet(tx_in.chain, tx_in.address),
            note=_get_note(tx_in.data_row),
        )

        vaults[vault_id][asset].quantity -= quantity

        if config.debug:
            sys.stderr.write(
                f"{Fore.CYAN}bridge: {vault_id}: "
                f"{asset}={vaults[vault_id][asset].quantity.normalize():0,f} "
                f"(-{quantity.normalize():0,f})\n"
            )

        if vaults[vault_id][asset].quantity > 0:
            # Getting back less than we deposited
            _next_free_row(tx_rows).t_record = TransactionOutRecord(
                TrType.SPEND,
                tx_in.data_row.timestamp,
                sell_quantity=vaults[vault_id][asset].quantity,
                sell_asset=asset,
                sell_value=Decimal(0),
                wallet=_get_wallet(tx_in.chain, tx_in.address),
                note=_get_note(tx_in.data_row),
            )
        elif vaults[vault_id][asset].quantity < 0:
            # Getting back more than we deposited, probably never happen?
            rate = DataParser.convert_currency(
                tx_in.data_row.row_dict["USD rate"], "USD", tx_in.data_row.timestamp
            )
            _next_free_row(tx_rows).t_record = TransactionOutRecord(
                TrType.AIRDROP,
                tx_in.data_row.timestamp,
                buy_quantity=abs(vaults[vault_id][asset].quantity),
                buy_asset=asset,
                buy_value=abs(vaults[vault_id][asset].quantity) * rate if rate else None,
                wallet=_get_wallet(tx_in.chain, tx_in.address),
                note=_get_note(tx_in.data_row),
            )
    else:
        # Getting different asset back, do swap
        vault_assets = list(vaults[vault_id].keys())

        if len(vault_assets) > 1:
            raise RuntimeError(f"Vault: {vault_id} contains multiple assets")

        if config.debug:
            sys.stderr.write(
                f"{Fore.CYAN}bridge: {vault_id}: " f"{asset}={quantity.normalize():0,f} (swap)\n"
            )

        _next_free_row(tx_rows).t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            tx_in.data_row.timestamp,
            buy_quantity=vaults[vault_id][vault_assets[0]].quantity,
            buy_asset=vault_assets[0],
            buy_value=vaults[vault_id][vault_assets[0]].value,
            wallet=_get_wallet(tx_in.chain, tx_in.address),
            note=_get_note(tx_in.data_row),
        )

        _next_free_row(tx_rows).t_record = TransactionOutRecord(
            TrType.TRADE,
            tx_in.data_row.timestamp,
            buy_quantity=quantity,
            buy_asset=asset,
            buy_value=value,
            sell_quantity=vaults[vault_id][vault_assets[0]].quantity,
            sell_asset=vault_assets[0],
            sell_value=vaults[vault_id][vault_assets[0]].value,
            wallet=_get_wallet(tx_in.chain, tx_in.address),
            note=_get_note(tx_in.data_row),
        )


def _do_fee_split(tx_fee: Optional[TxRecord], tx_rows: List["DataRow"]) -> None:
    if not tx_fee:
        return

    tr_all = [dr.t_record for dr in tx_rows if dr.t_record]
    tot_fee_quantity = Decimal(0)
    tot_fee_value = Decimal(0)

    for cnt, tr in enumerate(tr_all):
        if cnt < len(tr_all) - 1:
            split_fee_quantity = Decimal(tx_fee.quantity / len(tr_all)).quantize(PRECISION)
            tot_fee_quantity += split_fee_quantity
            if tx_fee.value:
                split_fee_value = Decimal(tx_fee.value / len(tr_all)).quantize(PRECISION)
                tot_fee_value += split_fee_value
        else:
            # Last tr, use up remainder
            split_fee_quantity = tx_fee.quantity - tot_fee_quantity
            if tx_fee.value:
                split_fee_value = tx_fee.value - tot_fee_value
            else:
                split_fee_value = None

        tr.fee_quantity = split_fee_quantity
        tr.fee_asset = tx_fee.asset
        tr.fee_value = split_fee_value


def _next_free_row(tx_rows: List["DataRow"]) -> "DataRow":
    for data_row in tx_rows:
        if not data_row.t_record:
            return data_row

    dup_data_row = copy.copy(tx_rows[0])
    dup_data_row.row = []
    dup_data_row.t_record = None
    tx_rows.append(dup_data_row)

    return dup_data_row


def _get_ins_outs(
    tx_rows: List["DataRow"], my_addresses: List[str], filename: str
) -> Tuple[List[TxRecord], List[TxRecord], Optional[TxRecord]]:
    tx_ins = []
    tx_outs = []
    tx_fees = []

    for dr in tx_rows:
        row_dict = dr.row_dict
        my_address = False

        rate = DataParser.convert_currency(row_dict["USD rate"], "USD", dr.timestamp)
        quantity = Decimal(row_dict["amount transfered"])
        asset = _get_asset(row_dict["token symbol"], row_dict["token unique ID"])
        value = quantity * rate if rate else None
        classification = row_dict["classification"]
        vault_id = VaultId(row_dict["vault id"])
        chain = Chain(row_dict["chain"])

        if row_dict["destination address"] == "network":
            tx_fees.append(
                TxRecord(
                    quantity,
                    asset,
                    value,
                    classification,
                    row_dict["source address"],
                    chain,
                    vault_id,
                    dr,
                )
            )
            dr.worksheet_name = _get_worksheet_name(chain, row_dict["source address"])
            continue

        if (
            row_dict["destination address"] in my_addresses
            or row_dict["destination address"].lower() in filename.lower()
        ):
            tx_ins.append(
                TxRecord(
                    quantity,
                    asset,
                    value,
                    classification,
                    row_dict["destination address"],
                    chain,
                    vault_id,
                    dr,
                )
            )
            dr.worksheet_name = _get_worksheet_name(chain, row_dict["destination address"])
            my_address = True

        if (
            row_dict["source address"] in my_addresses
            or row_dict["source address"].lower() in filename.lower()
        ):
            tx_outs.append(
                TxRecord(
                    -abs(quantity),
                    asset,
                    -abs(value) if value else None,
                    classification,
                    row_dict["source address"],
                    chain,
                    vault_id,
                    dr,
                )
            )
            dr.worksheet_name = _get_worksheet_name(chain, row_dict["source address"])
            my_address = True

        if not my_address:
            raise DataFilenameError(filename, f"{row_dict['chain']} address")

    if not tx_fees:
        tx_fee = None
    elif len(tx_fees) == 1:
        tx_fee = tx_fees[0]
    else:
        raise RuntimeError("Multiple fees for tx")

    return tx_ins, tx_outs, tx_fee


def _consolidate_tx(
    tx_ins: List[TxRecord], tx_outs: List[TxRecord], tx_hash: TxHash
) -> Tuple[List[TxRecord], List[TxRecord]]:
    tx_assets: Dict[AssetSymbol, TxRecord] = {}

    for tx_in in tx_ins:
        if tx_in.classification.startswith("interaction between your accounts"):
            return tx_ins, tx_outs

        if tx_in.asset not in tx_assets:
            tx_assets[tx_in.asset] = tx_in
        else:
            tx_record = tx_assets[tx_in.asset]
            tx_record.quantity += tx_in.quantity

            if tx_record.value is not None and tx_in.value is not None:
                tx_record.value += tx_in.value
            elif tx_record.value is None and tx_in.value is not None:
                tx_record.value = tx_in.value

            if not tx_record.vault_id:
                tx_record.vault_id = tx_in.vault_id

            if tx_record.vault_id and tx_record.vault_id != tx_in.vault_id:
                sys.stderr.write(
                    f"{WARNING} Different Vault ID:{tx_in.vault_id} detected in TX:{tx_hash} "
                    f"Vault ID:{tx_record.vault_id}\n"
                )

    for tx_out in tx_outs:
        if tx_out.classification.startswith("interaction between your accounts"):
            return tx_ins, tx_outs

        if tx_out.asset not in tx_assets:
            tx_assets[tx_out.asset] = tx_out
        else:
            tx_record = tx_assets[tx_out.asset]
            tx_record.quantity += tx_out.quantity

            if tx_record.value is not None and tx_out.value is not None:
                tx_record.value += tx_out.value
            elif tx_record.value is None and tx_out.value is not None:
                tx_record.value = tx_out.value

            if not tx_record.vault_id:
                tx_record.vault_id = tx_out.vault_id

            if tx_record.vault_id and tx_record.vault_id != tx_out.vault_id:
                sys.stderr.write(
                    f"{WARNING} Different Vault ID:{tx_out.vault_id} detected in TX:{tx_hash} "
                    f"Vault ID:{tx_record.vault_id}\n"
                )

    ctx_ins = []
    ctx_outs = []
    for _, tx_record in tx_assets.items():
        if tx_record.quantity > 0:
            ctx_ins.append(tx_record)
        elif tx_record.quantity < 0:
            ctx_outs.append(tx_record)

    return ctx_ins, ctx_outs


def _output_tx_rows(
    tx_ins: List[TxRecord], tx_outs: List[TxRecord], tx_fee: Optional[TxRecord]
) -> None:
    for i, tx in enumerate(tx_ins):
        in_size = len(tx_ins)
        sys.stderr.write(
            f"{Fore.GREEN}conv:  TX-IN ({i + 1} of {in_size}): {tx.quantity} {tx.asset} "
            f"({tx.value}) {tx.data_row}\n"
        )
    for i, tx in enumerate(tx_outs):
        out_size = len(tx_outs)
        sys.stderr.write(
            f"{Fore.GREEN}conv:  TX-OUT ({i + 1} of {out_size}): {tx.quantity} {tx.asset} "
            f"({tx.value}) {tx.data_row}\n"
        )

    if tx_fee:
        sys.stderr.write(
            f"{Fore.GREEN}conv:  TX-FEE: {tx_fee.quantity} {tx_fee.asset} "
            f"({tx_fee.value}) {tx_fee.data_row}\n"
        )


def _remove_t_records(tx_rows: List["DataRow"]) -> None:
    for dr in tx_rows:
        dr.t_record = None


def _get_asset(token_symbol: str, token_unique_id: str) -> AssetSymbol:
    if token_unique_id:
        if len(token_unique_id) > 16:
            token_unique_id = f"{token_unique_id[:8]}...{token_unique_id[-8:]}"
        return AssetSymbol(f"{token_symbol} #{token_unique_id}")
    return AssetSymbol(token_symbol)


def _get_wallet(chain: str, address: str) -> str:
    return f"{chain}-{address.lower()[0 : TransactionOutRecord.WALLET_ADDR_LEN]}"


def _get_worksheet_name(chain: str, address: str) -> str:
    wallet = _get_wallet(chain, address)
    return f"{WORKSHEET_NAME} {wallet}"


def _get_note(data_row: "DataRow") -> str:
    classification = data_row.row_dict["classification"]
    operation = data_row.row_dict["operation (decoded hex signature)"]
    counterparty_name = data_row.row_dict["counterparty name"]

    if classification:
        if (
            classification
            and counterparty_name != "unknown"
            and counterparty_name not in classification
        ):
            return f"{classification} ({counterparty_name})"
        return classification
    if operation:
        if counterparty_name and counterparty_name != "unknown":
            return f"{operation} ({counterparty_name})"
        return operation
    return ""


DataParser(
    ParserType.ACCOUNTING,
    "DeFi Taxes",
    [
        "timestamp",
        "UTC datetime",
        "chain",
        "transaction hash",
        "color",
        "classification",
        "custom note",
        "counterparty address",
        "counterparty name",
        "function hex signature",
        "operation (decoded hex signature)",
        "source address",
        "destination address",
        "amount transfered",
        "token contract address",
        "token symbol",
        "token unique ID",
        "transfer type",
        "tax treatment",
        "vault id",
        "USD rate",
    ],
    worksheet_name=WORKSHEET_NAME,
    all_handler=parse_defi_taxes,
)
