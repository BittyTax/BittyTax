# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging

from .config import config

log = logging.getLogger()

class Wallet(object):
    wallets = {}

    @classmethod
    def add_tokens(cls, wallet, asset, quantity):
        if (wallet, asset) not in cls.wallets:
            cls.wallets[(wallet, asset)] = Wallet(wallet, asset)

        cls.wallets[(wallet, asset)].add(quantity)

    @classmethod
    def subtract_tokens(cls, wallet, asset, quantity):
        if (wallet, asset) not in cls.wallets:
            cls.wallets[(wallet, asset)] = Wallet(wallet, asset)

        cls.wallets[(wallet, asset)].subtract(quantity)

    def __init__(self, wallet, asset):
        self.wallet = wallet
        self.asset = asset
        self.balance = 0

    def _format_balance(self):
        return '{:0,f}'.format(self.balance.normalize())

    def _format_wallet_name(self):
        return self.wallet + ":" + self.asset

    def add(self, quantity):
        self.balance += quantity
        log.debug("%s=%s (+%s)",
                  self._format_wallet_name(),
                  self._format_balance(),
                  '{:0,f}'.format(quantity.normalize()))

    def subtract(self, quantity):
        self.balance -= quantity
        log.debug("%s=%s (-%s)",
                  self._format_wallet_name(),
                  self._format_balance(),
                  '{:0,f}'.format(quantity.normalize()))

        if self.balance < 0 and self.asset not in config.fiat_list:
            log.warning("Balance at %s is negative %s",
                        self._format_wallet_name(),
                        self._format_balance())

    def __str__(self):
        return self._format_wallet_name() + "=" + self._format_balance()

def audit_records(transaction_records):
    log.debug("==FULL AUDIT TRANSACTION RECORDS==")
    for tr in transaction_records:
        log.debug(tr)
        if tr.buy_asset:
            Wallet.add_tokens(tr.wallet, tr.buy_asset, tr.buy_quantity)

        if tr.sell_asset:
            Wallet.subtract_tokens(tr.wallet, tr.sell_asset, tr.sell_quantity)

    log.info("==FINAL AUDIT BALANCES==")
    for w in sorted(Wallet.wallets):
        log.info(Wallet.wallets[w])
