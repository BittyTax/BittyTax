# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import copy
from decimal import Decimal

from .config import config
from .record import TransactionRecord

log = logging.getLogger()

class TransactionHistory(object):
    def __init__(self, transaction_records, value_asset):
        self.value_asset = value_asset
        self.transactions = []

        log.info("==SPLIT TRANSACTION RECORDS==")

        for tr in transaction_records:
            log.debug(tr)
            self.get_all_values(tr)

            # Attribute the fee value to the buy, the sell or both
            if tr.fee and tr.fee.disposal and tr.fee.proceeds is not None:
                if tr.buy and tr.sell:
                    if tr.buy.asset in config.fiat_list:
                        tr.sell.fee_value = tr.fee.proceeds
                        tr.sell.fee_fixed = tr.fee.proceeds_fixed
                    elif tr.sell.asset in config.fiat_list:
                        tr.buy.fee_value = tr.fee.proceeds
                        tr.buy.fee_fixed = tr.fee.proceeds_fixed
                    else:
                        # Split fee between both
                        tr.buy.fee_value = tr.fee.proceeds / 2
                        tr.buy.fee_fixed = tr.fee.proceeds_fixed
                        tr.sell.fee_value = tr.fee.proceeds - tr.buy.fee_value
                        tr.sell.fee_fixed = tr.fee.proceeds_fixed
                elif tr.buy:
                    tr.buy.fee_value = tr.fee.proceeds
                    tr.buy.fee_fixed = tr.fee.proceeds_fixed
                elif tr.sell:
                    tr.sell.fee_value = tr.fee.proceeds
                    tr.sell.fee_fixed = tr.fee.proceeds_fixed

            if tr.buy and tr.buy.asset not in config.fiat_list:
                tr.buy.set_tid()
                self.transactions.append(tr.buy)
                log.debug(tr.buy)
            if tr.sell and tr.sell.asset not in config.fiat_list:
                tr.sell.set_tid()
                self.transactions.append(tr.sell)
                log.debug(tr.sell)
            if tr.fee and tr.fee.asset not in config.fiat_list:
                tr.fee.set_tid()
                self.transactions.append(tr.fee)
                log.debug(tr.fee)

        log.info("Total transactions=%s", len(self.transactions))

    def get_all_values(self, tr):
        if tr.buy and tr.buy.acquisition and tr.buy.cost is None:
            if tr.sell:
                (tr.buy.cost,
                 tr.buy.cost_fixed) = self.which_asset_value(tr)
            else:
                (tr.buy.cost,
                 tr.buy.cost_fixed) = self.value_asset.get_value(tr.buy.asset,
                                                                 tr.buy.timestamp,
                                                                 tr.buy.quantity)

        if tr.sell and tr.sell.disposal and tr.sell.proceeds is None:
            if tr.buy:
                tr.sell.proceeds = tr.buy.cost
                tr.sell.proceeds_fixed = tr.buy.cost_fixed
            else:
                (tr.sell.proceeds,
                 tr.sell.proceeds_fixed) = self.value_asset.get_value(tr.sell.asset,
                                                                      tr.sell.timestamp,
                                                                      tr.sell.quantity)
        if tr.fee and tr.fee.disposal and tr.fee.proceeds is None:
            if tr.fee.asset not in config.fiat_list:
                if tr.buy and tr.buy.asset == tr.fee.asset:
                    price = tr.buy.cost / tr.buy.quantity if tr.buy.cost else Decimal(0)
                    tr.fee.proceeds = tr.fee.quantity * price
                    tr.fee.proceeds_fixed = tr.buy.cost_fixed
                elif tr.sell and tr.sell.asset == tr.fee.asset:
                    price = tr.sell.proceeds / tr.sell.quantity if tr.sell.proceeds else Decimal(0)
                    tr.fee.proceeds = tr.fee.quantity * price
                    tr.fee.proceeds_fixed = tr.sell.proceeds_fixed
                else:
                    # Must be a 3rd cryptoasset
                    (tr.fee.proceeds,
                     tr.fee.proceeds_fixed) = self.value_asset.get_value(tr.fee.asset,
                                                                         tr.fee.timestamp,
                                                                         tr.fee.quantity)
            else:
                # Fee paid in fiat
                (tr.fee.proceeds,
                 tr.fee.proceeds_fixed) = self.value_asset.get_value(tr.fee.asset,
                                                                     tr.fee.timestamp,
                                                                     tr.fee.quantity)
    def which_asset_value(self, tr):
        if config.trade_asset_type == config.TRADE_ASSET_TYPE_BUY:
            value, fixed = self.value_asset.get_value(tr.buy.asset,
                                                      tr.buy.timestamp,
                                                      tr.buy.quantity)
        elif config.trade_asset_type == config.TRADE_ASSET_TYPE_SELL:
            value, fixed = self.value_asset.get_value(tr.sell.asset,
                                                      tr.sell.timestamp,
                                                      tr.sell.quantity)
        else:
            pos_sell_asset = pos_buy_asset = len(config.asset_priority) + 1

            if tr.sell.asset in config.asset_priority:
                pos_sell_asset = config.asset_priority.index(tr.sell.asset)
            if tr.buy.asset in config.asset_priority:
                pos_buy_asset = config.asset_priority.index(tr.buy.asset)

            if pos_sell_asset <= pos_buy_asset:
                value, fixed = self.value_asset.get_value(tr.sell.asset,
                                                          tr.sell.timestamp,
                                                          tr.sell.quantity)
            else:
                value, fixed = self.value_asset.get_value(tr.buy.asset,
                                                          tr.buy.timestamp,
                                                          tr.buy.quantity)
        return value, fixed

class TransactionBase(object):
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
        self.matched = False
        self.pooled = []

    def set_tid(self):
        self.tid = self.t_record.set_tid()

    def _format_tid(self):
        return str(self.tid[0]) + "." + str(self.tid[1])

    def _format_quantity(self):
        if self.quantity is None:
            return '-'
        return '{:0,f}'.format(self.quantity.normalize())

    def _format_match_status(self):
        return " (M)" if self.matched else ""

    def _format_pooled(self):
        if self.pooled:
            return " [" + str(len(self.pooled)) + "]"
        return ''

    def _format_fee(self):
        if self.fee_value is not None:
            if self.fee_fixed:
                return ' + Fee=' + config.sym() + '{:0,.2f} {}'.format(self.fee_value, config.CCY)
            else:
                return ' + Fee=~' + config.sym() + '{:0,.2f} {}'.format(self.fee_value, config.CCY)

        return ''

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
            if k == 't_record':
                # Keep reference to the transaction record
                setattr(result, k, v)
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result

class Buy(TransactionBase):
    TYPE_DEPOSIT = TransactionRecord.TYPE_DEPOSIT
    TYPE_MINING = TransactionRecord.TYPE_MINING
    TYPE_INCOME = TransactionRecord.TYPE_INCOME
    TYPE_GIFT_RECEIVED = TransactionRecord.TYPE_GIFT_RECEIVED
    TYPE_TRADE = TransactionRecord.TYPE_TRADE

    ACQUISITION_TYPES = {TYPE_MINING, TYPE_INCOME, TYPE_GIFT_RECEIVED, TYPE_TRADE}

    def __init__(self, t_type, buy_quantity, buy_asset, buy_value):
        super(Buy, self).__init__(t_type, buy_asset, buy_quantity)
        self.cost = buy_value
        if self.cost is not None:
            self.cost_fixed = True
        else:
            self.cost_fixed = False

        self.acquisition = bool(self.t_type in self.ACQUISITION_TYPES)

    def __iadd__(self, other):
        if not self.pooled:
            self.pooled.append(copy.deepcopy(self))

        # Pool buys
        if self.asset != other.asset:
            raise Exception
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
            self.wallet = "<pooled>"

        if other.cost_fixed != self.cost_fixed:
            self.cost_fixed = False

        if other.fee_fixed != self.fee_fixed:
            self.fee_fixed = False

        self.pooled.append(other)
        return self

    def split_buy(self, sell_quantity):
        remainder = copy.deepcopy(self)

        self.cost = self.cost * (sell_quantity / self.quantity)

        if self.fee_value:
            self.fee_value = self.fee_value * (sell_quantity / self.quantity)

        self.quantity = sell_quantity
        self.set_tid()

        remainder.cost = remainder.cost - self.cost

        if self.fee_value:
            remainder.fee_value = remainder.fee_value - self.fee_value

        remainder.quantity = remainder.quantity - sell_quantity
        remainder.set_tid()

        log.debug("split: %s", self)
        log.debug("split: %s", remainder)

        return remainder

    def _format_cost(self):
        if self.cost is not None:
            if self.cost_fixed:
                return ' (=' + config.sym() + '{:0,.2f} {})'.format(self.cost, config.CCY)
            else:
                return ' (~' + config.sym() + '{:0,.2f} {})'.format(self.cost, config.CCY)
        return ''

    def _format_acquisition(self):
        if not self.acquisition:
            return '*'
        return ''

    def __str__(self):
        return "T-" + \
               type(self).__name__ + \
               self._format_acquisition() + " " + \
               "[TID:" + self._format_tid() + "] " + \
               self.t_type + ": " + \
               self._format_quantity() + " " + \
               self.asset + \
               self._format_cost() + \
               self._format_fee() + " '" + \
               self.wallet + "' " + \
               self.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z') + \
               self._format_pooled() + \
               self._format_match_status()

class Sell(TransactionBase):
    TYPE_WITHDRAWAL = TransactionRecord.TYPE_WITHDRAWAL
    TYPE_SPEND = TransactionRecord.TYPE_SPEND
    TYPE_GIFT_SENT = TransactionRecord.TYPE_GIFT_SENT
    TYPE_CHARITY_SENT = TransactionRecord.TYPE_CHARITY_SENT
    TYPE_TRADE = TransactionRecord.TYPE_TRADE

    DISPOSAL_TYPES = {TYPE_SPEND, TYPE_GIFT_SENT, TYPE_CHARITY_SENT, TYPE_TRADE}

    def __init__(self, t_type, sell_quantity, sell_asset, sell_value):
        super(Sell, self).__init__(t_type, sell_asset, sell_quantity)
        self.proceeds = sell_value
        if self.proceeds is not None:
            self.proceeds_fixed = True
        else:
            self.proceeds_fixed = False

        self.disposal = bool(self.t_type in self.DISPOSAL_TYPES)

    def __iadd__(self, other):
        if not self.pooled:
            self.pooled.append(copy.deepcopy(self))

        # Pool sells
        if self.asset != other.asset:
            raise Exception
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
            self.wallet = "<pooled>"

        if other.proceeds_fixed != self.proceeds_fixed:
            self.proceeds_fixed = False

        if other.fee_fixed != self.fee_fixed:
            self.fee_fixed = False

        self.pooled.append(other)
        return self

    def split_sell(self, buy_quantity):
        remainder = copy.deepcopy(self)

        self.proceeds = self.proceeds * (buy_quantity / self.quantity)

        if self.fee_value:
            self.fee_value = self.fee_value * (buy_quantity / self.quantity)

        self.quantity = buy_quantity
        self.set_tid()

        remainder.proceeds = remainder.proceeds - self.proceeds

        if self.fee_value:
            remainder.fee_value = remainder.fee_value - self.fee_value

        remainder.quantity = remainder.quantity - buy_quantity
        remainder.set_tid()

        log.debug("split: %s", self)
        log.debug("split: %s", remainder)

        return remainder

    def _format_proceeds(self):
        if self.proceeds is not None:
            if self.proceeds_fixed:
                return ' (=' + config.sym() + '{:0,.2f} {})'.format(self.proceeds, config.CCY)
            else:
                return ' (~' + config.sym() + '{:0,.2f} {})'.format(self.proceeds, config.CCY)
        return ''

    def _format_disposal(self):
        if not self.disposal:
            return '*'
        return ''

    def __str__(self):
        return "T-" + \
               type(self).__name__ + \
               self._format_disposal() + " " + \
               "[TID:" + self._format_tid() + "] " + \
               self.t_type + ": " + \
               self._format_quantity() + " " + \
               self.asset + \
               self._format_proceeds() + \
               self._format_fee() + " '" + \
               self.wallet + "' " + \
               self.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z') + \
               self._format_pooled() + \
               self._format_match_status()
