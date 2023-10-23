# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from colorama import Fore
from tqdm import tqdm

from .bt_types import AssetSymbol
from .config import config
from .constants import WARNING


class Holdings:
    def __init__(self, asset: AssetSymbol) -> None:
        self.asset = asset
        self.quantity = Decimal(0)
        self.cost = Decimal(0)
        self.fees = Decimal(0)
        self.withdrawals = 0
        self.deposits = 0
        self.mismatches = 0

    def add_tokens(self, quantity: Decimal, cost: Decimal, fees: Decimal, is_deposit: bool) -> None:
        self.quantity += quantity
        self.cost += cost
        self.fees += fees

        if is_deposit:
            self.deposits += 1

        if config.debug:
            print(
                f"{Fore.YELLOW}section104:   "
                f"{self.asset}={self.quantity.normalize():0,f} (+{quantity.normalize():0,f}) "
                f"cost={config.sym()}{self.cost:0,.2f} {config.ccy} "
                f"(+{config.sym()}{cost:0,.2f} {config.ccy}) "
                f"fees={config.sym()}{self.fees:0,.2f} {config.ccy} "
                f"(+{config.sym()}{fees:0,.2f} {config.ccy})"
            )

    def subtract_tokens(
        self, quantity: Decimal, cost: Decimal, fees: Decimal, is_withdrawal: bool
    ) -> None:
        self.quantity -= quantity
        self.cost -= cost
        self.fees -= fees

        if is_withdrawal:
            self.withdrawals += 1

        if config.debug:
            print(
                f"{Fore.YELLOW}section104:   "
                f"{self.asset}={self.quantity.normalize():0,f} (-{quantity.normalize():0,f}) "
                f"cost={config.sym()}{self.cost:0,.2f} {config.ccy} "
                f"(-{config.sym()}{cost:0,.2f} {config.ccy}) "
                f"fees={config.sym()}{self.fees:0,.2f} {config.ccy} "
                f"(-{config.sym()}{fees:0,.2f} {config.ccy})"
            )

    def check_transfer_mismatch(self) -> None:
        if self.withdrawals > 0 and self.withdrawals != self.deposits:
            tqdm.write(
                f"{WARNING} Disposal detected between a Withdrawal and a Deposit "
                f"({self.withdrawals}:{self.deposits}) for {self.asset}, cost basis will be wrong"
            )
            self.mismatches += 1
