# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from colorama import Fore, Back
from tqdm import tqdm

from .config import config

class Holdings(object):
    def __init__(self, asset):
        self.asset = asset
        self.quantity = Decimal(0)
        self.cost = Decimal(0)
        self.fees = Decimal(0)
        self.withdrawals = 0
        self.deposits = 0
        self.mismatches = 0

    def add_tokens(self, quantity, cost, fees, is_deposit):
        self.quantity += quantity
        self.cost += cost
        self.fees += fees

        if is_deposit:
            self.deposits += 1

        if config.args.debug:
            print("%ssection104:   %s=%s (+%s) cost=%s %s (+%s %s) fees=%s %s (+%s %s}" % (
                Fore.YELLOW,
                self.asset,
                '{:0,f}'.format(self.quantity.normalize()),
                '{:0,f}'.format(quantity.normalize()),
                config.sym() + '{:0,.2f}'.format(self.cost),
                config.CCY,
                config.sym() + '{:0,.2f}'.format(cost),
                config.CCY,
                config.sym() + '{:0,.2f}'.format(self.fees),
                config.CCY,
                config.sym() + '{:0,.2f}'.format(fees),
                config.CCY))

    def subtract_tokens(self, quantity, cost, fees, is_withdrawal):
        self.quantity -= quantity
        self.cost -= cost
        self.fees -= fees

        if is_withdrawal:
            self.withdrawals += 1

        if config.args.debug:
            print("%ssection104:   %s=%s (-%s) cost=%s %s (-%s %s) fees=%s %s (-%s %s}" % (
                Fore.YELLOW,
                self.asset,
                '{:0,f}'.format(self.quantity.normalize()),
                '{:0,f}'.format(quantity.normalize()),
                config.sym() + '{:0,.2f}'.format(self.cost),
                config.CCY,
                config.sym() + '{:0,.2f}'.format(cost),
                config.CCY,
                config.sym() + '{:0,.2f}'.format(self.fees),
                config.CCY,
                config.sym() + '{:0,.2f}'.format(fees),
                config.CCY))

    def check_transfer_mismatch(self):
        if self.withdrawals != self.deposits:
            tqdm.write("%sWARNING%s Disposal detected between a Withdrawal and a Deposit "
                       "(%s:%s) for %s, cost basis will be wrong" % ( Back.RED+Fore.BLACK,
                           Back.RESET+Fore.RED, self.withdrawals, self.deposits, self.asset))
            self.mismatches += 1
