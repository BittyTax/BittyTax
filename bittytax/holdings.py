# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from .config import config, log

class Holdings(object):
    def __init__(self, asset):
        self.asset = asset
        self.quantity = Decimal(0)
        self.cost = Decimal(0)

    def add_tokens(self, quantity, cost):
        self.quantity += quantity
        self.cost += cost

        if config.args.debug:
            log.debug("%s=%s (+%s) %s%s %s (+%s%s %s)",
                      self.asset,
                      self.format_quantity(),
                      '{:0,f}'.format(quantity.normalize()),
                      config.sym(), self._format_cost(), config.CCY,
                      config.sym(), '{:0,.2f}'.format(cost), config.CCY)
    def subtract_tokens(self, quantity, cost):
        self.quantity -= quantity
        self.cost -= cost

        if config.args.debug:
            log.debug("%s=%s (-%s) %s%s %s (-%s%s %s)",
                      self.asset,
                      self.format_quantity(),
                      '{:0,f}'.format(quantity.normalize()),
                      config.sym(), self._format_cost(), config.CCY,
                      config.sym(), '{:0,.2f}'.format(cost), config.CCY)

    def format_quantity(self):
        return '{:0,f}'.format(self.quantity.normalize())

    def _format_cost(self):
        return '{:0,.2f}'.format(self.cost)
