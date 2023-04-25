# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal

from colorama import Fore, Style
from tqdm import tqdm

from .config import config
from .constants import WARNING


class AuditRecords:
    def __init__(self, transaction_records):
        self.wallets = {}
        self.totals = {}
        self.failures = []

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
            self.prune_empty(self.wallets)

    @staticmethod
    def prune_empty(wallets):
        for wallet in list(wallets):
            for asset in list(wallets[wallet]):
                if wallets[wallet][asset] == Decimal(0):
                    wallets[wallet].pop(asset)
            if not wallets[wallet]:
                wallets.pop(wallet)

    def _add_tokens(self, wallet, asset, quantity):
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

    def _subtract_tokens(self, wallet, asset, quantity):
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

    def compare_pools(self, holdings):
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

    def _log_failure(self, asset, audit, s104):
        failure = {}
        failure["asset"] = asset
        failure["audit"] = audit
        failure["s104"] = s104

        self.failures.append(failure)

    def report_failures(self):
        print(
            f"\n{Fore.YELLOW}"
            f'{"Asset":<8} {"Audit Balance":>25} {"Section 104 Pool":>25} {"Difference":>25}'
        )

        for failure in self.failures:
            if failure["s104"] is not None:
                print(
                    f'{Fore.WHITE}{failure["asset"]:<8} {failure["audit"].normalize():25,f} '
                    f'{failure["s104"].normalize():25,f} '
                    f'{Fore.RED}{(failure["s104"] - failure["audit"]).normalize():+25,f}'
                )
            else:
                print(
                    f'{Fore.WHITE}{failure["asset"]<8} {failure["audit"].normalize():25,f} '
                    f'{Fore.RED}{"<missing>":>25}'
                )
