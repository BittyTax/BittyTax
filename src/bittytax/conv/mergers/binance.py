# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2025

import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, NewType

from colorama import Fore

from ...bt_types import AssetSymbol, FileId, TrType
from ...config import config
from ..datamerge import DataMerge, ParserRequired
from ..out_record import TransactionOutRecord
from ..parsers.binance import WALLET, statements

if TYPE_CHECKING:
    from ..datafile import DataFile
    from ..datarow import DataRow

BS = FileId("binance_statement")
VaultId = NewType("VaultId", str)

LIQUID_SWAP = VaultId("Liquid Swap")
SIMPLE_EARN_FLEXIBLE = VaultId("Simple Earn Flexible")


# Using a merger for Binance so we process the entire statements history in order
def merge_binance(data_files: Dict[FileId, "DataFile"]) -> bool:
    merge = False
    vaults: Dict[VaultId, Dict[AssetSymbol, Decimal]] = {}

    data_rows = sorted(data_files[BS].data_rows, key=lambda dr: dr.timestamp, reverse=False)
    for dr in data_rows:
        if dr.row_dict["Operation"] in (
            "Liquid Swap Add",
            "Liquid Swap Add/Sell",
            "Liquidity Farming Remove",
        ):
            if Decimal(dr.row_dict["Change"]) < 0:
                _do_stake(dr, vaults, LIQUID_SWAP)
            else:
                _do_unstake(dr, vaults, LIQUID_SWAP, is_exit(data_rows, dr))
            merge = True
        elif dr.row_dict["Operation"] in (
            "Simple Earn Flexible Subscription",
            "Simple Earn Flexible Redemption",
        ):
            if Decimal(dr.row_dict["Change"]) < 0:
                _do_stake(dr, vaults, SIMPLE_EARN_FLEXIBLE)
            else:
                _do_unstake(dr, vaults, SIMPLE_EARN_FLEXIBLE, is_exit(data_rows, dr))
            merge = True

    for vault_id, vault in vaults.items():
        for asset in vault:
            sys.stderr.write(
                f"{Fore.CYAN}staked: '{vault_id}' {asset}={vault[asset].normalize():0,f}\n"
            )
    return merge


def _do_stake(
    data_row: "DataRow", vaults: Dict[VaultId, Dict[AssetSymbol, Decimal]], vault_id: VaultId
) -> None:
    if vault_id not in vaults:
        vaults[vault_id] = {}

    asset = AssetSymbol(data_row.row_dict["Coin"])
    quantity = abs(Decimal(data_row.row_dict["Change"]))

    if asset not in vaults[vault_id]:
        vaults[vault_id][asset] = quantity
    else:
        vaults[vault_id][asset] += quantity

    if config.debug:
        sys.stderr.write(
            f"{Fore.YELLOW}merge: stake '{vault_id}' "
            f"{asset}={vaults[vault_id][asset].normalize():0,f} "
            f"(+{quantity.normalize():0,f})\n"
        )


def _do_unstake(
    data_row: "DataRow",
    vaults: Dict[VaultId, Dict[AssetSymbol, Decimal]],
    vault_id: VaultId,
    exit_vault: bool,
) -> None:
    if vault_id not in vaults:
        raise ValueError(f"Vault: {vault_id} does not exist")

    asset = AssetSymbol(data_row.row_dict["Coin"])
    quantity = Decimal(data_row.row_dict["Change"])

    if asset not in vaults[vault_id]:
        raise AttributeError(f"Vault: {vault_id} does not contain {asset}")

    vaults[vault_id][asset] -= quantity

    if config.debug:
        sys.stderr.write(
            f"{Fore.YELLOW}merge: unstake '{vault_id}' "
            f"{asset}={vaults[vault_id][asset].normalize():0,f} "
            f"(-{quantity.normalize():0,f}) {Fore.CYAN}"
        )

    if vaults[vault_id][asset] < 0:
        # Getting back more than we staked
        staking_reward = abs(vaults[vault_id][asset])
        del vaults[vault_id][asset]

        data_row.t_record = TransactionOutRecord(
            TrType.STAKING,
            data_row.timestamp,
            buy_quantity=staking_reward,
            buy_asset=asset,
            wallet=WALLET,
            note=f'Gain from "{vault_id}"',
        )
        if config.debug:
            sys.stderr.write(f"{Fore.CYAN}Gain {staking_reward.normalize():0,f} {asset}")
    elif vaults[vault_id][asset] == 0:
        del vaults[vault_id][asset]
        if config.debug:
            sys.stderr.write(f"{Fore.CYAN}Empty")
    elif exit_vault:
        if vaults[vault_id][asset] > 0:
            # Assume any tokens remained staked are lost
            data_row.t_record = TransactionOutRecord(
                TrType.SPEND,
                data_row.timestamp,
                sell_quantity=vaults[vault_id][asset],
                sell_asset=asset,
                sell_value=Decimal(0),
                wallet=WALLET,
                note=f'Loss from "{vault_id}"',
            )
            if config.debug:
                sys.stderr.write(
                    f"{Fore.CYAN}Loss {vaults[vault_id][asset].normalize():0,f} {asset}"
                )

            del vaults[vault_id][asset]
    if config.debug:
        sys.stderr.write("\n")


def is_exit(data_rows: List["DataRow"], data_row: "DataRow") -> bool:
    # Is this the last unstake?
    unstake_rows = [
        dr
        for dr in data_rows
        if dr.row_dict["Operation"] == data_row.row_dict["Operation"]
        and dr.row_dict["Coin"] == data_row.row_dict["Coin"]
    ]
    return bool(unstake_rows[-1] is data_row)


DataMerge(
    "Binance stake/unstake",
    {
        BS: {"req": ParserRequired.MANDATORY, "obj": statements},
    },
    merge_binance,
)
