# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import copy
import sys

from colorama import Fore, Style
from tqdm import tqdm

from .config import config
from .record import TransactionRecord


class TransactionHistory:
    def __init__(self, transaction_records, value_asset):
        self.value_asset = value_asset
        self.transactions = []

        if config.debug:
            print(f"{Fore.CYAN}split transaction records")

        for tr in tqdm(
            transaction_records,
            unit="tr",
            desc=f"{Fore.CYAN}split transaction records{Fore.GREEN}",
            disable=bool(config.debug or not sys.stdout.isatty()),
        ):
            if config.debug:
                print(f"{Fore.MAGENTA}split: TR {tr}")

            self.get_all_values(tr)

            # Attribute the fee value (allowable cost) to the buy, the sell or both
            if tr.fee and tr.fee.disposal and tr.fee.proceeds:
                if tr.buy and tr.buy.acquisition and tr.sell and tr.sell.disposal:
                    if tr.buy.asset in config.fiat_list:
                        tr.sell.fee_value = tr.fee.proceeds
                        tr.sell.fee_fixed = tr.fee.proceeds_fixed
                    elif tr.sell.asset in config.fiat_list:
                        tr.buy.fee_value = tr.fee.proceeds
                        tr.buy.fee_fixed = tr.fee.proceeds_fixed
                    else:
                        # Crypto-to-crypto trades
                        if config.trade_allowable_cost_type == config.TRADE_ALLOWABLE_COST_BUY:
                            tr.buy.fee_value = tr.fee.proceeds
                            tr.buy.fee_fixed = tr.fee.proceeds_fixed
                        elif config.trade_allowable_cost_type == config.TRADE_ALLOWABLE_COST_SELL:
                            tr.sell.fee_value = tr.fee.proceeds
                            tr.sell.fee_fixed = tr.fee.proceeds_fixed
                        else:
                            # Split fee between both
                            tr.buy.fee_value = tr.fee.proceeds / 2
                            tr.buy.fee_fixed = tr.fee.proceeds_fixed
                            tr.sell.fee_value = tr.fee.proceeds - tr.buy.fee_value
                            tr.sell.fee_fixed = tr.fee.proceeds_fixed
                elif tr.buy and tr.buy.acquisition:
                    tr.buy.fee_value = tr.fee.proceeds
                    tr.buy.fee_fixed = tr.fee.proceeds_fixed
                elif tr.sell and tr.sell.disposal:
                    tr.sell.fee_value = tr.fee.proceeds
                    tr.sell.fee_fixed = tr.fee.proceeds_fixed
                else:
                    # Special case for transfer fees
                    if config.transfer_fee_allowable_cost:
                        tr.fee.fee_value = tr.fee.proceeds
                        tr.fee.fee_fixed = tr.fee.proceeds_fixed

            if tr.t_type != TransactionRecord.TYPE_LOST:
                if tr.buy and (tr.buy.quantity or tr.buy.fee_value):
                    tr.buy.set_tid()
                    self.transactions.append(tr.buy)
                    if config.debug:
                        print(f"{Fore.GREEN}split:   {tr.buy}")

                if tr.sell and (tr.sell.quantity or tr.sell.fee_value):
                    tr.sell.set_tid()
                    self.transactions.append(tr.sell)
                    if config.debug:
                        print(f"{Fore.GREEN}split:   {tr.sell}")
            else:
                # Special case for LOST sell must be before buy-back
                if tr.sell and (tr.sell.quantity or tr.sell.fee_value):
                    tr.sell.set_tid()
                    self.transactions.append(tr.sell)
                    if config.debug:
                        print(f"{Fore.GREEN}split:   {tr.sell}")

                if tr.buy and (tr.buy.quantity or tr.buy.fee_value):
                    tr.buy.set_tid()
                    self.transactions.append(tr.buy)
                    if config.debug:
                        print(f"{Fore.GREEN}split:   {tr.buy}")

            if tr.fee and tr.fee.quantity:
                tr.fee.set_tid()
                self.transactions.append(tr.fee)
                if config.debug:
                    print(f"{Fore.GREEN}split:   {tr.fee}")

        if config.debug:
            print(f"{Fore.CYAN}split: total transactions={len(self.transactions)}")

    def get_all_values(self, tr):
        if tr.buy and tr.buy.acquisition and tr.buy.cost is None:
            if tr.sell:
                (tr.buy.cost, tr.buy.cost_fixed) = self.which_asset_value(tr)
            else:
                (tr.buy.cost, tr.buy.cost_fixed) = self.value_asset.get_value(
                    tr.buy.asset, tr.buy.timestamp, tr.buy.quantity
                )

        if tr.sell and tr.sell.disposal and tr.sell.proceeds is None:
            if tr.buy:
                tr.sell.proceeds = tr.buy.cost
                tr.sell.proceeds_fixed = tr.buy.cost_fixed
            else:
                (tr.sell.proceeds, tr.sell.proceeds_fixed) = self.value_asset.get_value(
                    tr.sell.asset, tr.sell.timestamp, tr.sell.quantity
                )
        if tr.fee and tr.fee.disposal and tr.fee.proceeds is None:
            if tr.fee.asset not in config.fiat_list:
                if tr.buy and tr.buy.asset == tr.fee.asset:
                    if tr.buy.cost and tr.buy.quantity:
                        price = tr.buy.cost / tr.buy.quantity
                        tr.fee.proceeds = tr.fee.quantity * price
                        tr.fee.proceeds_fixed = tr.buy.cost_fixed
                    else:
                        (
                            tr.fee.proceeds,
                            tr.fee.proceeds_fixed,
                        ) = self.value_asset.get_value(
                            tr.fee.asset, tr.fee.timestamp, tr.fee.quantity
                        )
                elif tr.sell and tr.sell.asset == tr.fee.asset:
                    if tr.sell.proceeds and tr.sell.quantity:
                        price = tr.sell.proceeds / tr.sell.quantity
                        tr.fee.proceeds = tr.fee.quantity * price
                        tr.fee.proceeds_fixed = tr.sell.proceeds_fixed
                    else:
                        (
                            tr.fee.proceeds,
                            tr.fee.proceeds_fixed,
                        ) = self.value_asset.get_value(
                            tr.fee.asset, tr.fee.timestamp, tr.fee.quantity
                        )
                else:
                    # Must be a 3rd cryptoasset
                    (
                        tr.fee.proceeds,
                        tr.fee.proceeds_fixed,
                    ) = self.value_asset.get_value(tr.fee.asset, tr.fee.timestamp, tr.fee.quantity)
            else:
                # Fee paid in fiat
                (tr.fee.proceeds, tr.fee.proceeds_fixed) = self.value_asset.get_value(
                    tr.fee.asset, tr.fee.timestamp, tr.fee.quantity
                )

    def which_asset_value(self, tr):
        if config.trade_asset_type == config.TRADE_ASSET_TYPE_BUY:
            if tr.buy.cost is None:
                value, fixed = self.value_asset.get_value(
                    tr.buy.asset, tr.buy.timestamp, tr.buy.quantity
                )
            else:
                value, fixed = tr.buy.cost, tr.buy.cost_fixed
        elif config.trade_asset_type == config.TRADE_ASSET_TYPE_SELL:
            if tr.sell.proceeds is None:
                value, fixed = self.value_asset.get_value(
                    tr.sell.asset, tr.sell.timestamp, tr.sell.quantity
                )
            else:
                value, fixed = tr.sell.proceeds, tr.sell.proceeds_fixed
        else:
            pos_sell_asset = pos_buy_asset = len(config.asset_priority) + 1

            if tr.sell.asset in config.asset_priority:
                pos_sell_asset = config.asset_priority.index(tr.sell.asset)
            if tr.buy.asset in config.asset_priority:
                pos_buy_asset = config.asset_priority.index(tr.buy.asset)

            if pos_sell_asset <= pos_buy_asset:
                if tr.sell.proceeds is None:
                    value, fixed = self.value_asset.get_value(
                        tr.sell.asset, tr.sell.timestamp, tr.sell.quantity
                    )
                else:
                    value, fixed = tr.sell.proceeds, tr.sell.proceeds_fixed
            else:
                if tr.buy.cost is None:
                    value, fixed = self.value_asset.get_value(
                        tr.buy.asset, tr.buy.timestamp, tr.buy.quantity
                    )
                else:
                    value, fixed = tr.buy.cost, tr.buy.cost_fixed

        return value, fixed


class TransactionBase:  # pylint: disable=too-many-instance-attributes
    POOLED = "<pooled>"

    def __init__(self, t_type, asset, quantity):
        self.tid = None
        self.t_record = None
        self.t_type = t_type
        self.asset = asset
        self.quantity = quantity
        self.fee_value = None
        self.fee_fixed = True
        self.wallet = None
        self.timestamp = None
        self.note = None
        self.matched = False
        self.pooled = []

    def name(self):
        return self.__class__.__name__

    def set_tid(self):
        self.tid = self.t_record.set_tid()

    def is_crypto(self):
        return bool(self.asset not in config.fiat_list)

    def _format_quantity(self):
        if self.quantity is None:
            return ""
        return f"{self.quantity.normalize():0,f}"

    def _format_note(self):
        if self.note:
            return f"'{self.note}' "
        return ""

    def _format_pooled(self, bold=False):
        if self.pooled:
            return (
                f" {Style.BRIGHT if bold else ''}({len(self.pooled)})"
                f"{Style.NORMAL if bold else ''}"
            )
        return ""

    def _format_fee(self):
        if self.fee_value is not None:
            return (
                f" + fee={'' if self.fee_fixed else '~'}"
                f"{config.sym()}{self.fee_value:0,.2f} {config.ccy}"
            )

        return ""

    def _format_timestamp(self):
        if self.timestamp.microsecond:
            return f"{self.timestamp:%Y-%m-%dT%H:%M:%S.%f %Z}"
        return f"{self.timestamp:%Y-%m-%dT%H:%M:%S %Z}"

    def __eq__(self, other):
        return (self.asset, self.timestamp) == (other.asset, other.timestamp)

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return (self.asset, self.timestamp) < (other.asset, other.timestamp)

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == "t_record":
                # Keep reference to the transaction record
                setattr(result, k, v)
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result


class Buy(TransactionBase):  # pylint: disable=too-many-instance-attributes
    TYPE_DEPOSIT = TransactionRecord.TYPE_DEPOSIT
    TYPE_MINING = TransactionRecord.TYPE_MINING
    TYPE_STAKING = TransactionRecord.TYPE_STAKING
    TYPE_INTEREST = TransactionRecord.TYPE_INTEREST
    TYPE_DIVIDEND = TransactionRecord.TYPE_DIVIDEND
    TYPE_INCOME = TransactionRecord.TYPE_INCOME
    TYPE_GIFT_RECEIVED = TransactionRecord.TYPE_GIFT_RECEIVED
    TYPE_AIRDROP = TransactionRecord.TYPE_AIRDROP
    TYPE_TRADE = TransactionRecord.TYPE_TRADE

    ACQUISITION_TYPES = {
        TYPE_MINING,
        TYPE_STAKING,
        TYPE_INTEREST,
        TYPE_DIVIDEND,
        TYPE_INCOME,
        TYPE_GIFT_RECEIVED,
        TYPE_AIRDROP,
        TYPE_TRADE,
    }

    def __init__(self, t_type, buy_quantity, buy_asset, buy_value):
        super().__init__(t_type, buy_asset, buy_quantity)
        self.acquisition = bool(self.t_type in self.ACQUISITION_TYPES)
        self.cost = None
        self.cost_fixed = False

        if self.acquisition and buy_value is not None:
            self.cost = buy_value
            self.cost_fixed = True

    def __iadd__(self, other):
        if not self.pooled:
            self.pooled.append(copy.deepcopy(self))

        # Pool buys
        if self.asset != other.asset:
            raise ValueError("Assets do not match")
        self.quantity += other.quantity
        self.cost += other.cost

        if self.fee_value is not None and other.fee_value is not None:
            self.fee_value += other.fee_value
        elif self.fee_value is None and other.fee_value is not None:
            self.fee_value = other.fee_value

        if other.timestamp < self.timestamp:
            # Keep timestamp of earliest transaction
            self.timestamp = other.timestamp

        if other.wallet != self.wallet:
            self.wallet = self.POOLED

        if other.cost_fixed != self.cost_fixed:
            self.cost_fixed = False

        if other.fee_fixed != self.fee_fixed:
            self.fee_fixed = False

        if other.note != self.note:
            self.note = self.POOLED

        self.pooled.append(other)
        return self

    def split_buy(self, sell_quantity):
        remainder = copy.deepcopy(self)

        self.cost = self.cost * (sell_quantity / self.quantity)

        if self.fee_value:
            self.fee_value = self.fee_value * (sell_quantity / self.quantity)

        self.quantity = sell_quantity
        self.set_tid()

        # pylint: disable=attribute-defined-outside-init
        remainder.cost = remainder.cost - self.cost
        # pylint: enable=attribute-defined-outside-init

        if self.fee_value:
            remainder.fee_value = remainder.fee_value - self.fee_value

        remainder.quantity = remainder.quantity - sell_quantity
        remainder.set_tid()
        return remainder

    def _format_cost(self):
        if self.cost is not None:
            return (
                f" ({'=' if self.cost_fixed else '~'}"
                f"{config.sym()}{self.cost:0,.2f} {config.ccy})"
            )
        return ""

    def __str__(self, pooled_bold=False, quantity_bold=False):
        return (
            f"{self.name().upper()}{'*' if not self.acquisition else ''} "
            f"{self.t_type}"
            f"{Style.BRIGHT if quantity_bold else ''} "
            f"{self._format_quantity()} "
            f"{self.asset}"
            f"{Style.NORMAL if quantity_bold else ''}"
            f"{self._format_cost()}"
            f"{self._format_fee()} "
            f"'{self.wallet}' "
            f"{self._format_timestamp()} "
            f"{self._format_note()}"
            f"[TID:{self.tid[0]}.{self.tid[1]}]"
            f"{self._format_pooled()}"
        )


class Sell(TransactionBase):  # pylint: disable=too-many-instance-attributes
    TYPE_WITHDRAWAL = TransactionRecord.TYPE_WITHDRAWAL
    TYPE_SPEND = TransactionRecord.TYPE_SPEND
    TYPE_GIFT_SENT = TransactionRecord.TYPE_GIFT_SENT
    TYPE_GIFT_SPOUSE = TransactionRecord.TYPE_GIFT_SPOUSE
    TYPE_CHARITY_SENT = TransactionRecord.TYPE_CHARITY_SENT
    TYPE_LOST = TransactionRecord.TYPE_LOST
    TYPE_TRADE = TransactionRecord.TYPE_TRADE

    DISPOSAL_TYPES = {
        TYPE_SPEND,
        TYPE_GIFT_SENT,
        TYPE_GIFT_SPOUSE,
        TYPE_CHARITY_SENT,
        TYPE_LOST,
        TYPE_TRADE,
    }

    def __init__(self, t_type, sell_quantity, sell_asset, sell_value):
        super().__init__(t_type, sell_asset, sell_quantity)
        self.disposal = bool(self.t_type in self.DISPOSAL_TYPES)
        self.proceeds = None
        self.proceeds_fixed = False

        if self.disposal and sell_value is not None:
            self.proceeds = sell_value
            self.proceeds_fixed = True

    def __iadd__(self, other):
        if not self.pooled:
            self.pooled.append(copy.deepcopy(self))

        # Pool sells
        if self.asset != other.asset:
            raise ValueError("Assets do not match")
        self.quantity += other.quantity
        self.proceeds += other.proceeds

        if self.fee_value is not None and other.fee_value is not None:
            self.fee_value += other.fee_value
        elif self.fee_value is None and other.fee_value is not None:
            self.fee_value = other.fee_value

        if other.timestamp > self.timestamp:
            # Keep timestamp of latest transaction
            self.timestamp = other.timestamp

        if other.wallet != self.wallet:
            self.wallet = self.POOLED

        if other.proceeds_fixed != self.proceeds_fixed:
            self.proceeds_fixed = False

        if other.fee_fixed != self.fee_fixed:
            self.fee_fixed = False

        if other.note != self.note:
            self.note = self.POOLED

        self.pooled.append(other)
        return self

    def split_sell(self, buy_quantity):
        remainder = copy.deepcopy(self)

        self.proceeds = self.proceeds * (buy_quantity / self.quantity)

        if self.fee_value:
            self.fee_value = self.fee_value * (buy_quantity / self.quantity)

        self.quantity = buy_quantity
        self.set_tid()

        # pylint: disable=attribute-defined-outside-init
        remainder.proceeds = remainder.proceeds - self.proceeds
        # pylint: enable=attribute-defined-outside-init

        if self.fee_value:
            remainder.fee_value = remainder.fee_value - self.fee_value

        remainder.quantity = remainder.quantity - buy_quantity
        remainder.set_tid()
        return remainder

    def _format_proceeds(self):
        if self.proceeds is not None:
            return (
                f" ({'=' if self.proceeds_fixed else '~'}"
                f"{config.sym()}{self.proceeds:0,.2f} {config.ccy})"
            )
        return ""

    def __str__(self, pooled_bold=False, quantity_bold=False):
        return (
            f"{self.name().upper()}{'*' if not self.disposal else ''} "
            f"{self.t_type}"
            f"{Style.BRIGHT if quantity_bold else ''} "
            f"{self._format_quantity()} "
            f"{self.asset}"
            f"{Style.NORMAL if quantity_bold else ''}"
            f"{self._format_proceeds()}"
            f"{self._format_fee()} "
            f"'{self.wallet}' "
            f"{self._format_timestamp()} "
            f"{self._format_note()}"
            f"[TID:{self.tid[0]}.{self.tid[1]}]"
            f"{self._format_pooled()}"
        )
