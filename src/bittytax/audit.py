# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from colorama import Fore, Style
from tqdm import tqdm
from typing_extensions import TypedDict

from .bt_types import AssetSymbol, TrRecordPart, TrType, Wallet
from .config import config
from .constants import WARNING
from .holdings import Holdings
from .t_record import TransactionRecord
from .transactions import Buy, Sell


@dataclass
class AuditTotals:
    total: Decimal = Decimal(0)
    transfers_mismatch: Decimal = Decimal(0)


@dataclass
class AuditLogEntry:
    change: Optional[Decimal]
    fee: Optional[Decimal]
    balance: Decimal
    wallet: Wallet
    total: Decimal
    tr_part: TrRecordPart
    t_record: TransactionRecord


class ComparePoolFail(TypedDict):  # pylint: disable=too-few-public-methods
    asset: AssetSymbol
    audit_tot: Decimal
    holding_tot: Optional[Decimal]


class AuditRecords:
    def __init__(self, transaction_records: List[TransactionRecord]) -> None:
        self.wallets: Dict[Wallet, Dict[AssetSymbol, Decimal]] = {}
        self.totals: Dict[AssetSymbol, AuditTotals] = {}
        self.audit_log: Dict[AssetSymbol, List[AuditLogEntry]] = {}
        self.failures: List[ComparePoolFail] = []

        if config.debug:
            print(f"{Fore.CYAN}audit transaction records")

        for tr in tqdm(
            transaction_records,
            unit="tr",
            desc=f"{Fore.CYAN}audit transaction records{Fore.GREEN}",
            disable=bool(config.debug or not sys.stdout.isatty()),
        ):
            if config.debug:
                print(f"{Fore.MAGENTA}audit: TR {tr}")

            if tr.buy:
                self._add_tokens(tr.wallet, tr.buy)
                self._audit_log(
                    tr.buy.asset, tr.wallet, tr.buy.quantity, None, TrRecordPart.BUY, tr
                )
            if tr.sell:
                self._subtract_tokens(tr.wallet, tr.sell)
                self._audit_log(
                    tr.sell.asset, tr.wallet, -abs(tr.sell.quantity), None, TrRecordPart.SELL, tr
                )

            if tr.fee:
                self._subtract_tokens(tr.wallet, tr.fee)
                self._audit_log(
                    tr.fee.asset, tr.wallet, None, -abs(tr.fee.quantity), TrRecordPart.FEE, tr
                )

        if config.debug:
            print(f"{Fore.CYAN}audit: final balances by wallet")
            for wallet in sorted(self.wallets, key=str.lower):
                for asset in sorted(self.wallets[wallet]):
                    print(
                        f"{Fore.YELLOW}audit: {wallet}:{asset}={Style.BRIGHT}"
                        f"{self.wallets[wallet][asset].normalize():0,f}{Style.NORMAL}"
                    )

            print(f"{Fore.CYAN}audit: final balances by asset")
            for asset in sorted(self.totals):
                print(
                    f"{Fore.YELLOW}audit: {asset}={Style.BRIGHT}"
                    f"{self.totals[asset].total.normalize():0,f}{Style.NORMAL}"
                )

        for asset in sorted(self.totals):
            if self.totals[asset].transfers_mismatch:
                print(
                    f"{WARNING} Transfers mismatch of "
                    f"{self.totals[asset].transfers_mismatch.normalize():+0,f} {asset} detected"
                )

        if config.audit_hide_empty:
            self._prune_empty()

    def _add_tokens(self, wallet: Wallet, buy: Buy) -> None:
        if wallet not in self.wallets:
            self.wallets[wallet] = {}

        if buy.asset not in self.wallets[wallet]:
            self.wallets[wallet][buy.asset] = Decimal(0)

        self.wallets[wallet][buy.asset] += buy.quantity

        if buy.asset not in self.totals:
            self.totals[buy.asset] = AuditTotals()

        self.totals[buy.asset].total += buy.quantity

        if buy.t_type == TrType.DEPOSIT and buy.is_crypto():
            self.totals[buy.asset].transfers_mismatch += buy.quantity

        if config.debug:
            print(
                f"{Fore.GREEN}audit:   {wallet}:{buy.asset}="
                f"{self.wallets[wallet][buy.asset].normalize():0,f} "
                f"(+{buy.quantity.normalize():0,f})"
            )

    def _subtract_tokens(self, wallet: Wallet, sell: Sell) -> None:
        if wallet not in self.wallets:
            self.wallets[wallet] = {}

        if sell.asset not in self.wallets[wallet]:
            self.wallets[wallet][sell.asset] = Decimal(0)

        self.wallets[wallet][sell.asset] -= sell.quantity

        if sell.asset not in self.totals:
            self.totals[sell.asset] = AuditTotals()

        self.totals[sell.asset].total -= sell.quantity

        if sell.t_type == TrType.WITHDRAWAL and sell.is_crypto():
            self.totals[sell.asset].transfers_mismatch -= sell.quantity

        if config.debug:
            print(
                f"{Fore.GREEN}audit:   {wallet}:{sell.asset}="
                f"{self.wallets[wallet][sell.asset].normalize():0,f} "
                f"(-{sell.quantity.normalize():0,f})"
            )
        if self.wallets[wallet][sell.asset] < 0 and sell.is_crypto():
            tqdm.write(
                f"{WARNING} Balance at {wallet}:{sell.asset} "
                f"is negative {self.wallets[wallet][sell.asset].normalize():0,f}"
            )

    def _audit_log(
        self,
        asset: AssetSymbol,
        wallet: Wallet,
        quantity: Optional[Decimal],
        fee: Optional[Decimal],
        tr_part: TrRecordPart,
        tr: TransactionRecord,
    ) -> None:
        audit_log_entry = AuditLogEntry(
            quantity,
            fee,
            self.wallets[wallet][asset],
            wallet,
            self.totals[asset].total,
            tr_part,
            tr,
        )

        if asset not in self.audit_log:
            self.audit_log[asset] = []

        self.audit_log[asset].append(audit_log_entry)

    def _prune_empty(self) -> None:
        for wallet in list(self.wallets):
            for asset in list(self.wallets[wallet]):
                if self.wallets[wallet][asset] == Decimal(0):
                    self.wallets[wallet].pop(asset)
            if not self.wallets[wallet]:
                self.wallets.pop(wallet)

        for asset in list(self.totals):
            if not self.totals[asset].total and not self.totals[asset].transfers_mismatch:
                self.totals.pop(asset)

    def compare_holdings(self, holdings: Dict[AssetSymbol, Holdings]) -> bool:
        passed = True
        for asset in sorted(self.totals):
            if asset in config.fiat_list:
                continue

            if asset in holdings:
                difference = holdings[asset].quantity - self.totals[asset].total
                if not difference:
                    if config.debug:
                        print(f"{Fore.GREEN}check holding: {asset} (ok)")
                else:
                    if config.debug:
                        print(
                            f"{Fore.RED}check holding: {asset} "
                            f"{difference.normalize():+0,f} (mismatch)"
                        )

                    self._log_failure(asset, self.totals[asset].total, holdings[asset].quantity)
                    passed = False
            else:
                if config.debug:
                    print(f"{Fore.RED}check holding: {asset} (missing)")

                self._log_failure(asset, self.totals[asset].total, None)
                passed = False

        return passed

    def _log_failure(
        self, asset: AssetSymbol, audit_tot: Decimal, holding_tot: Optional[Decimal]
    ) -> None:
        failure: ComparePoolFail = {
            "asset": asset,
            "audit_tot": audit_tot,
            "holding_tot": holding_tot,
        }
        self.failures.append(failure)

    def report_failures(self) -> None:
        print(
            f"\n{Fore.YELLOW}"
            f'{"Asset":<8} {"Audit Balance":>25} {"Holding":>25} {"Difference":>25}'
        )

        for failure in self.failures:
            if failure["holding_tot"] is not None:
                print(
                    f'{Fore.WHITE}{failure["asset"]:<8} {failure["audit_tot"].normalize():25,f} '
                    f'{failure["holding_tot"].normalize():25,f} '
                    f'{Fore.RED}{(failure["holding_tot"] - failure["audit_tot"]).normalize():+25,f}'
                )
            else:
                print(
                    f'{Fore.WHITE}{failure["asset"]:<8} {failure["audit_tot"].normalize():25,f} '
                    f'{Fore.RED}{"<missing>":>25}'
                )
