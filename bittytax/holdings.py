# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging

from decimal import Decimal

from .config import config

log = logging.getLogger()

class Holdings(object):
    def __init__(self, asset):
        self.asset = asset
        self.quantity = Decimal(0)
        self.cost = Decimal(0)
        self.fees = Decimal(0)

    def add_tokens(self, quantity, cost, fees):
        self.quantity += quantity
        self.cost += cost
        self.fees += fees

        if config.args.debug:
            log.debug("%s=%s (+%s) cost=%s%s %s (+%s%s %s) fees=%s%s %s (+%s%s %s)",
                      self.asset,
                      '{:0,f}'.format(self.quantity.normalize()),
                      '{:0,f}'.format(quantity.normalize()),
                      config.sym(), '{:0,.2f}'.format(self.cost), config.CCY,
                      config.sym(), '{:0,.2f}'.format(cost), config.CCY,
                      config.sym(), '{:0,.2f}'.format(self.fees), config.CCY,
                      config.sym(), '{:0,.2f}'.format(fees), config.CCY)

    def subtract_tokens(self, quantity, cost, fees):
        self.quantity -= quantity
        self.cost -= cost
        self.fees -= fees

        if config.args.debug:
            log.debug("%s=%s (-%s) cost=%s%s %s (-%s%s %s) fees=%s%s %s (-%s%s %s)",
                      self.asset,
                      '{:0,f}'.format(self.quantity.normalize()),
                      '{:0,f}'.format(quantity.normalize()),
                      config.sym(), '{:0,.2f}'.format(self.cost), config.CCY,
                      config.sym(), '{:0,.2f}'.format(cost), config.CCY,
                      config.sym(), '{:0,.2f}'.format(self.fees), config.CCY,
                      config.sym(), '{:0,.2f}'.format(fees), config.CCY)
