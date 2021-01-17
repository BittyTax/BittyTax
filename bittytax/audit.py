# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal

from colorama import Fore, Back, Style
from tqdm import tqdm

from .config import config
from .audit_fix.asset import Asset

class AuditRecords(object):
    def __init__(self, transaction_records):
        self.wallets = {}
        self.totals = {}

        if config.args.debug:
            print("%saudit transaction records" % Fore.CYAN)

        for tr in tqdm(transaction_records,
                       unit='tr',
                       desc="%saudit transaction records%s" % (Fore.CYAN, Fore.GREEN),
                       disable=bool(config.args.debug or not sys.stdout.isatty())):
            if config.args.debug:
                print("%saudit: TR %s" % (Fore.MAGENTA, tr))

            # adjust (if required) the available assets based on the way transactions are shown
            # for example, coinbase doesn't show fiat currency deposit as seperate lines
            found, asset, quantity = Asset.find_missing_asset(tr)
            if found and asset == tr.sell.asset:
                self._add_tokens(tr.wallet, asset, quantity, deposit=True)

            if tr.buy:
                self._add_tokens(tr.wallet, tr.buy.asset, tr.buy.quantity)

            if tr.sell:
                self._subtract_tokens(tr.wallet, tr.sell.asset, tr.sell.quantity)

            if tr.fee:
                self._subtract_tokens(tr.wallet, tr.fee.asset, tr.fee.quantity)

        if config.args.debug:
            print("%saudit: final balances by wallet" % Fore.CYAN)
            for wallet in sorted(self.wallets, key=str.lower):
                for asset in sorted(self.wallets[wallet]):
                    print("%saudit: %s:%s=%s%s%s" % (
                        Fore.YELLOW,
                        wallet,
                        asset,
                        Style.BRIGHT,
                        '{:0,f}'.format(self.wallets[wallet][asset].normalize()),
                        Style.NORMAL))

            print("%saudit: final balances by asset" % Fore.CYAN)
            for asset in sorted(self.totals):
                print("%saudit: %s=%s%s%s" % (
                    Fore.YELLOW,
                    asset,
                    Style.BRIGHT,
                    '{:0,f}'.format(self.totals[asset].normalize()),
                    Style.NORMAL))

    def _add_tokens(self, wallet, asset, quantity, deposit=False):
        if wallet not in self.wallets:
            self.wallets[wallet] = {}

        if asset not in self.wallets[wallet]:
            self.wallets[wallet][asset] = Decimal(0)

        self.wallets[wallet][asset] += quantity

        if asset not in self.totals:
            self.totals[asset] = Decimal(0)

        self.totals[asset] += quantity

        if config.args.debug:
            print("%saudit:   %s:%s=%s (+%s) %s" % (
                Fore.GREEN,
                wallet,
                asset,
                '{:0,f}'.format(self.wallets[wallet][asset].normalize()),
                '{:0,f}'.format(quantity.normalize()),
                deposit and 'deposit' or ''))

    def _subtract_tokens(self, wallet, asset, quantity):
        if wallet not in self.wallets:
            self.wallets[wallet] = {}

        if asset not in self.wallets[wallet]:
            self.wallets[wallet][asset] = Decimal(0)

        self.wallets[wallet][asset] -= quantity

        if asset not in self.totals:
            self.totals[asset] = Decimal(0)

        self.totals[asset] -= quantity

        if config.args.debug:
            print("%saudit:   %s:%s=%s (-%s)" %(
                Fore.GREEN,
                wallet,
                asset,
                '{:0,f}'.format(self.wallets[wallet][asset].normalize()),
                '{:0,f}'.format(quantity.normalize())))

        if self.wallets[wallet][asset] < 0 and asset not in config.fiat_list:
            tqdm.write("%sWARNING%s Balance at %s:%s is negative %s" % (
                Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW,
                wallet, asset, '{:0,f}'.format(self.wallets[wallet][asset].normalize())))
