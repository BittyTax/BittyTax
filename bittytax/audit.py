# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging

from decimal import Decimal

from .config import config

log = logging.getLogger()

class AuditRecords(object):
    def __init__(self, transaction_records):
        self.wallets = {}
        self.totals = {}

        log.info("==AUDIT TRANSACTION RECORDS==")
        for tr in transaction_records:
            log.debug(tr)
            if tr.buy:
                self._add_tokens(tr.wallet, tr.buy.asset, tr.buy.quantity)

            if tr.sell:
                self._subtract_tokens(tr.wallet, tr.sell.asset, tr.sell.quantity)

            if tr.fee:
                self._subtract_tokens(tr.wallet, tr.fee.asset, tr.fee.quantity)

        log.debug("==TOTAL BALANCES==")
        for asset in sorted(self.totals):
            log.debug("%s=%s",
                      asset,
                      '{:0,f}'.format(self.totals[asset].normalize()))

    def _add_tokens(self, wallet, asset, quantity):
        if wallet not in self.wallets:
            self.wallets[wallet] = {}

        if asset not in self.wallets[wallet]:
            self.wallets[wallet][asset] = Decimal(0)

        self.wallets[wallet][asset] += quantity

        if asset not in self.totals:
            self.totals[asset] = Decimal(0)

        self.totals[asset] += quantity

        log.debug("%s:%s=%s (+%s)",
                  wallet,
                  asset,
                  '{:0,f}'.format(self.wallets[wallet][asset].normalize()),
                  '{:0,f}'.format(quantity.normalize()))

    def _subtract_tokens(self, wallet, asset, quantity):
        if wallet not in self.wallets:
            self.wallets[wallet] = {}

        if asset not in self.wallets[wallet]:
            self.wallets[wallet][asset] = Decimal(0)

        self.wallets[wallet][asset] -= quantity

        if asset not in self.totals:
            self.totals[asset] = Decimal(0)

        self.totals[asset] -= quantity

        log.debug("%s:%s=%s (-%s)",
                  wallet,
                  asset,
                  '{:0,f}'.format(self.wallets[wallet][asset].normalize()),
                  '{:0,f}'.format(quantity.normalize()))

        if self.wallets[wallet][asset] < 0 and asset not in config.fiat_list:
            log.warning("Balance at %s:%s is negative %s",
                        wallet,
                        asset,
                        '{:0,f}'.format(self.wallets[wallet][asset].normalize()))
