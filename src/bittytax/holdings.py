# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from bisect import bisect_right
from decimal import Decimal

from datetime import datetime, timedelta
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
        self.balance_history = [(None, Decimal(0))]
        self.cost_history = [(None, Decimal(0))]

    def _addto_balance_history(self, quantity: Decimal, transaction_date: datetime) -> None:
        last_balance = self.balance_history[-1][1]
        new_balance = last_balance + quantity
        self._update_balance_history(new_balance, transaction_date)

    def _subctractto_balance_history(self, quantity: Decimal, transaction_date: datetime) -> None:
        last_balance = self.balance_history[-1][1]
        new_balance = last_balance - quantity
        self._update_balance_history(new_balance, transaction_date)

    def _update_balance_history(self, new_balance: Decimal, transaction_date: datetime) -> None:
        if self.balance_history[-1][0] is None:
            self.balance_history[-1] = (transaction_date.date(), new_balance)
        else:
            last_balance = self.balance_history[-1][1]
            if new_balance != last_balance:
                self.balance_history.append((transaction_date.date(), new_balance))

    def add_tokens(self, quantity: Decimal, cost: Decimal, fees: Decimal, is_deposit: bool, transaction_date: datetime) -> None:
        self.quantity += quantity
        self.cost += cost
        self.fees += fees
        self._addto_balance_history(quantity, transaction_date) 

        if is_deposit:
            self.deposits += 1

        if config.debug:
            print(
                f"{Fore.YELLOW}holdings:   "
                f"{self.asset}={self.quantity.normalize():0,f} (+{quantity.normalize():0,f}) "
                f"cost={config.sym()}{self.cost:0,.2f} {config.ccy} "
                f"(+{config.sym()}{cost:0,.2f} {config.ccy}) "
                f"fees={config.sym()}{self.fees:0,.2f} {config.ccy} "
                f"(+{config.sym()}{fees:0,.2f} {config.ccy})"
            )

    def subtract_tokens(
        self, quantity: Decimal, cost: Decimal, fees: Decimal, is_withdrawal: bool, transaction_date: datetime
    ) -> None:
        self.quantity -= quantity
        self.cost -= cost
        self.fees -= fees
        self._subctractto_balance_history(quantity, transaction_date) 

        if is_withdrawal:
            self.withdrawals += 1

        if config.debug:
            print(
                f"{Fore.YELLOW}holdings:   "
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

    def get_balance_at_date(self, target_date: datetime.date) -> Decimal:
        dates = [date for date, balance in self.balance_history]
        pos = bisect_right(dates, target_date) - 1  # Find the index closest to the target_date
        if pos >= 0:
            return self.balance_history[pos][1]  # Returns the corresponding balance
        return Decimal(0)

    def calculate_average_balance(self, start_date: datetime.date, end_date: datetime.date) -> Decimal:
        total_balance = Decimal(0)
        day_count = 0

        # Extract balance_history for convenience
        balance_history = self.balance_history
        balance_history_len = len(balance_history)

        # If there is no historical data, return 0 immediately
        if balance_history_len == 0:
            return Decimal(0)

        # We start with a balance of 0 until we reach the first available date
        current_date = start_date
        previous_balance = Decimal(0)

        for i, (date, balance) in enumerate(balance_history):
            # If the current balance date is beyond the end date, we can exit
            if date > end_date:
                break
        
            # If there are days between current_date and the current date of the balance_history
            if date > current_date:
                # Calculates the number of days between current_date and the current balance sheet date
                days_in_between = (min(date, end_date) - current_date).days
                if days_in_between > 0:
                    total_balance += previous_balance * Decimal(days_in_between)
                    day_count += days_in_between

            # Update current_date to the latest between current balance date and start_date
            current_date = max(current_date, date)
            previous_balance = balance

            # If we are past end_date, we can finish
            if current_date > end_date:
                break

        # If there are still days remaining between current_date and end_date, add the final balance
        if current_date <= end_date:
            days_in_between = (end_date - current_date).days + 1
            total_balance += previous_balance * Decimal(days_in_between)
            day_count += days_in_between

        # Calculating the average if there are days counted
        if day_count > 0:
            return total_balance / Decimal(day_count)
        return Decimal(0)