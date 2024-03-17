# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal
from typing import Dict, List, Optional

from colorama import Fore, Style
from tqdm import tqdm
from typing_extensions import TypedDict

from .bt_types import AssetSymbol, Wallet
from .config import config
from .constants import WARNING
from .holdings import Holdings
from .record import TransactionRecord


class ComparePoolFail(TypedDict):  # pylint: disable=too-few-public-methods
    asset: AssetSymbol
    audit_tot: Decimal
    s104_tot: Optional[Decimal]


class AuditRecords:
    def __init__(self, transaction_records: List[TransactionRecord]) -> None:
        self.wallets: Dict[Wallet, Dict[AssetSymbol, Decimal]] = {}
        self.totals: Dict[AssetSymbol, Decimal] = {}
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
                self._add_tokens(tr.wallet, tr.buy.asset, tr.buy.quantity)

            if tr.sell:
                self._subtract_tokens(tr.wallet, tr.sell.asset, tr.sell.quantity)

            if tr.fee:
                self._subtract_tokens(tr.wallet, tr.fee.asset, tr.fee.quantity)

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
                    f"{self.totals[asset].normalize():0,f}{Style.NORMAL}"
                )

        if config.audit_hide_empty:
            self._prune_empty()

    def _add_tokens(self, wallet: Wallet, asset: AssetSymbol, quantity: Decimal) -> None:
        if wallet not in self.wallets:
            self.wallets[wallet] = {}

        if asset not in self.wallets[wallet]:
            self.wallets[wallet][asset] = Decimal(0)

        self.wallets[wallet][asset] += quantity

        if asset not in self.totals:
            self.totals[asset] = Decimal(0)

        self.totals[asset] += quantity

        if config.debug:
            print(
                f"{Fore.GREEN}audit:   {wallet}:{asset}="
                f"{self.wallets[wallet][asset].normalize():0,f} (+{quantity.normalize():0,f})"
            )

    def _subtract_tokens(self, wallet: Wallet, asset: AssetSymbol, quantity: Decimal) -> None:
        if wallet not in self.wallets:
            self.wallets[wallet] = {}

        if asset not in self.wallets[wallet]:
            self.wallets[wallet][asset] = Decimal(0)

        self.wallets[wallet][asset] -= quantity

        if asset not in self.totals:
            self.totals[asset] = Decimal(0)

        self.totals[asset] -= quantity

        if config.debug:
            print(
                f"{Fore.GREEN}audit:   {wallet}:{asset}="
                f"{self.wallets[wallet][asset].normalize():0,f} (-{quantity.normalize():0,f})"
            )

        if self.wallets[wallet][asset] < 0 and asset not in config.fiat_list:
            tqdm.write(
                f"{WARNING} Balance at {wallet}:{asset} "
                f"is negative {self.wallets[wallet][asset].normalize():0,f}"
            )

    def _prune_empty(self) -> None:
        for wallet in list(self.wallets):
            for asset in list(self.wallets[wallet]):
                if self.wallets[wallet][asset] == Decimal(0):
                    self.wallets[wallet].pop(asset)
            if not self.wallets[wallet]:
                self.wallets.pop(wallet)

    def compare_pools(self, holdings: Dict[AssetSymbol, Holdings]) -> bool:
        passed = True
        for asset in sorted(self.totals):
            if asset in config.fiat_list:
                continue

            if asset in holdings:
                if self.totals[asset] == holdings[asset].quantity:
                    if config.debug:
                        print(f"{Fore.GREEN}check pool: {asset} (ok)")
                else:
                    if config.debug:
                        print(
                            f"{Fore.RED}check pool: {asset}"
                            f"{(holdings[asset].quantity - self.totals[asset]).normalize():+0,f} "
                            f"(mismatch)"
                        )

                    self._log_failure(asset, self.totals[asset], holdings[asset].quantity)
                    passed = False
            else:
                if config.debug:
                    print(f"{Fore.RED}check pool: {asset} (missing)")

                self._log_failure(asset, self.totals[asset], None)
                passed = False

        return passed

    def _log_failure(
        self, asset: AssetSymbol, audit_tot: Decimal, s104_tot: Optional[Decimal]
    ) -> None:
        failure: ComparePoolFail = {"asset": asset, "audit_tot": audit_tot, "s104_tot": s104_tot}
        self.failures.append(failure)

    def report_failures(self) -> None:
        print(
            f"\n{Fore.YELLOW}"
            f'{"Asset":<8} {"Audit Balance":>25} {"Section 104 Pool":>25} {"Difference":>25}'
        )

        for failure in self.failures:
            if failure["s104_tot"] is not None:
                print(
                    f'{Fore.WHITE}{failure["asset"]:<8} {failure["audit_tot"].normalize():25,f} '
                    f'{failure["s104_tot"].normalize():25,f} '
                    f'{Fore.RED}{(failure["s104_tot"] - failure["audit_tot"]).normalize():+25,f}'
                )
            else:
                print(
                    f'{Fore.WHITE}{failure["asset"]:<8} {failure["audit_tot"].normalize():25,f} '
                    f'{Fore.RED}{"<missing>":>25}'
                )
