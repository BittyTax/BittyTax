# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import copy
from decimal import Decimal

from .config import config
from .record import TransactionInRecord

PRECISION = Decimal('0.00')

log = logging.getLogger()

class TransactionHistory(object):
    def __init__(self, transaction_records, value_asset):
        self.transactions = []
        log.debug("==SPLIT TRANSACTION RECORDS==")

        for tr in transaction_records:
            if tr.sell_asset and tr.sell_asset not in config.fiat_list:
                value = self.which_asset_value(tr, value_asset)
                sell = Sell(tr.tid, tr.t_type, tr.wallet, tr.timestamp,
                            tr.sell_quantity, tr.sell_asset, value)
                self.transactions.append(sell)
                log.debug(sell)

            if tr.buy_asset and tr.buy_asset not in config.fiat_list:
                value = self.which_asset_value(tr, value_asset)
                buy = Buy(tr.tid, tr.t_type, tr.wallet, tr.timestamp,
                          tr.buy_quantity, tr.buy_asset, value)
                self.transactions.append(buy)
                log.debug(buy)

        log.debug("Total transactions=%s", len(self.transactions))

    @staticmethod
    def which_asset_value(tr, value_asset):
        value = None
        if tr.t_type in tr.BUY_VALUE_TYPES:
            value = value_asset.get_value(tr.buy_asset,
                                          tr.timestamp,
                                          tr.buy_quantity,
                                          tr.buy_value)
        elif tr.t_type in tr.SELL_VALUE_TYPES:
            value = value_asset.get_value(tr.sell_asset,
                                          tr.timestamp,
                                          tr.sell_quantity,
                                          tr.sell_value)
        elif tr.t_type == tr.TYPE_TRADE:
            if config.trade_asset_type == config.TRADE_ASSET_TYPE_BUY:
                value = value_asset.get_value(tr.buy_asset,
                                              tr.timestamp,
                                              tr.buy_quantity,
                                              tr.buy_value)
            elif config.trade_asset_type == config.TRADE_ASSET_TYPE_SELL:
                value = value_asset.get_value(tr.sell_asset,
                                              tr.timestamp,
                                              tr.sell_quantity,
                                              tr.sell_value)
            else:
                pos_sell_asset = pos_buy_asset = len(config.asset_priority) + 1

                if tr.sell_asset in config.asset_priority:
                    pos_sell_asset = config.asset_priority.index(tr.sell_asset)
                if tr.buy_asset in config.asset_priority:
                    pos_buy_asset = config.asset_priority.index(tr.buy_asset)

                if pos_sell_asset <= pos_buy_asset:
                    value = value_asset.get_value(tr.sell_asset,
                                                  tr.timestamp,
                                                  tr.sell_quantity,
                                                  tr.sell_value)
                else:
                    value = value_asset.get_value(tr.buy_asset,
                                                  tr.timestamp,
                                                  tr.buy_quantity,
                                                  tr.buy_value)
        if value is not None:
            value = value.quantize(PRECISION)

        return value

class TransactionBase(object):
    def __init__(self, tid, t_type, asset, wallet, timestamp):
        self.tid = [tid, 0]
        self.t_type = t_type
        self.asset = asset
        self.wallet = wallet
        self.timestamp = timestamp
        self.matched = False
        self.pooled = []

    def _format_tid(self):
        if self.tid[1] == 0:
            return str(self.tid[0])
        return str(self.tid[0]) + "." + str(self.tid[1])

    def _format_match_status(self):
        return " (M)" if self.matched else ""

    def _format_pooled(self):
        if len(self.pooled) > 1:
            return " [" + str(len(self.pooled)) + "]"
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
            setattr(result, k, copy.deepcopy(v, memo))
        return result

class Buy(TransactionBase):
    TYPE_DEPOSIT = TransactionInRecord.TYPE_DEPOSIT
    TYPE_MINING = TransactionInRecord.TYPE_MINING
    TYPE_INCOME = TransactionInRecord.TYPE_INCOME
    TYPE_GIFT_RECEIVED = TransactionInRecord.TYPE_GIFT_RECEIVED
    TYPE_TRADE = TransactionInRecord.TYPE_TRADE

    ACQUISITION_TYPES = {TYPE_MINING, TYPE_INCOME, TYPE_GIFT_RECEIVED, TYPE_TRADE}

    def __init__(self, tid, t_type, wallet, timestamp, buy_quantity, buy_asset, buy_value):
        super(Buy, self).__init__(tid, t_type, buy_asset, wallet, timestamp)
        self.buy_quantity = buy_quantity
        self.cost = buy_value

        self.pooled.append(copy.deepcopy(self))

    def __iadd__(self, other):
        # Pool buys
        if self.asset != other.asset:
            raise Exception
        self.buy_quantity += other.buy_quantity
        self.cost += other.cost

        if other.timestamp < self.timestamp:
            # Keep timestamp of earliest transaction
            self.timestamp = other.timestamp

        if other.wallet != self.wallet:
            self.wallet = "<pooled>"

        self.pooled.append(other)
        return self

    def is_acquisition(self):
        return self.t_type in self.ACQUISITION_TYPES

    def split_buy(self, sell_quantity):
        remainder = copy.deepcopy(self)
        remainder.tid[1] += 1

        self.cost = Decimal(self.cost * (sell_quantity /
                                         self.buy_quantity)).quantize(PRECISION)
        self.buy_quantity = sell_quantity

        remainder.cost = remainder.cost - self.cost
        remainder.buy_quantity = remainder.buy_quantity - sell_quantity

        log.debug("split: %s", self)
        log.debug("split: %s", remainder)

        return remainder

    def _format_buy_quantity(self):
        if self.buy_quantity is None:
            return '-'
        return '{:0,f}'.format(self.buy_quantity.normalize())

    def _format_cost(self):
        if self.cost is not None:
            return ' (' + config.sym() + '{:0,.2f} {})'.format(self.cost, config.CCY)
        return ''

    def __str__(self):
        return "[TID:" + self._format_tid() + "] " + \
               type(self).__name__ + " (" + \
               self.t_type + "): " + \
               self._format_buy_quantity() + " " + \
               self.asset + \
               self._format_cost() + " '" + \
               self.wallet + "' " + \
               self.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z') + \
               self._format_pooled() + \
               self._format_match_status()

class Sell(TransactionBase):
    TYPE_WITHDRAWAL = TransactionInRecord.TYPE_WITHDRAWAL
    TYPE_SPEND = TransactionInRecord.TYPE_SPEND
    TYPE_GIFT_SENT = TransactionInRecord.TYPE_GIFT_SENT
    TYPE_CHARITY_SENT = TransactionInRecord.TYPE_CHARITY_SENT
    TYPE_TRADE = TransactionInRecord.TYPE_TRADE

    DISPOSAL_TYPES = {TYPE_SPEND, TYPE_GIFT_SENT, TYPE_CHARITY_SENT, TYPE_TRADE}

    def __init__(self, tid, t_type, wallet, timestamp, sell_quantity, sell_asset, sell_value):
        super(Sell, self).__init__(tid, t_type, sell_asset, wallet, timestamp)
        self.sell_quantity = sell_quantity
        self.proceeds = sell_value

        self.pooled.append(copy.deepcopy(self))

    def __iadd__(self, other):
	# Pool sells
        if self.asset != other.asset:
            raise Exception
        self.sell_quantity += other.sell_quantity
        self.proceeds += other.proceeds

        if other.timestamp > self.timestamp:
            # Keep timestamp of latest transaction
            self.timestamp = other.timestamp

        if other.wallet != self.wallet:
            self.wallet = "<pooled>"

        self.pooled.append(other)
        return self

    def is_disposal(self):
        return self.t_type in self.DISPOSAL_TYPES

    def split_sell(self, buy_quantity):
        remainder = copy.deepcopy(self)
        remainder.tid[1] += 1

        self.proceeds = Decimal(self.proceeds * (buy_quantity /
                                                 self.sell_quantity)).quantize(PRECISION)
        self.sell_quantity = buy_quantity

        remainder.proceeds = remainder.proceeds - self.proceeds
        remainder.sell_quantity = remainder.sell_quantity - buy_quantity

        log.debug("split: %s", self)
        log.debug("split: %s", remainder)

        return remainder

    def _format_sell_quantity(self):
        if self.sell_quantity is None:
            return '-'
        return '{:0,f}'.format(self.sell_quantity.normalize())

    def _format_proceeds(self):
        if self.proceeds is not None:
            return ' (' + config.sym() + '{:0,.2f} {})'.format(self.proceeds, config.CCY)
        return ''

    def __str__(self):
        return "[TID:" + self._format_tid() + "] " + \
               type(self).__name__ + " (" + \
               self.t_type + "): " + \
               self._format_sell_quantity() + " " + \
               self.asset + \
               self._format_proceeds() + " '" + \
               self.wallet + "' " + \
               self.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z') + \
               self._format_pooled() + \
               self._format_match_status()
