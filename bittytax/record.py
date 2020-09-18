# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from .config import config

class TransactionRecord(object):
    TYPE_DEPOSIT = 'Deposit'
    TYPE_MINING = 'Mining'
    TYPE_STAKING = 'Staking'
    TYPE_INCOME = 'Income'
    TYPE_INTEREST = 'Interest'
    TYPE_DIVIDEND = 'Dividend'
    TYPE_GIFT_RECEIVED = 'Gift-Received'
    TYPE_WITHDRAWAL = 'Withdrawal'
    TYPE_SPEND = 'Spend'
    TYPE_GIFT_SENT = 'Gift-Sent'
    TYPE_CHARITY_SENT = 'Charity-Sent'
    TYPE_TRADE = 'Trade'

    ALL_TYPES = (TYPE_DEPOSIT,
                 TYPE_MINING,
                 TYPE_STAKING,
                 TYPE_INCOME,
                 TYPE_INTEREST,
                 TYPE_DIVIDEND,
                 TYPE_GIFT_RECEIVED,
                 TYPE_WITHDRAWAL,
                 TYPE_SPEND,
                 TYPE_GIFT_SENT,
                 TYPE_CHARITY_SENT,
                 TYPE_TRADE)

    cnt = 0

    def __init__(self, t_type, buy, sell, fee, wallet, timestamp):
        self.tid = None
        self.t_type = t_type
        self.buy = buy
        self.sell = sell
        self.fee = fee
        self.wallet = wallet
        self.timestamp = timestamp

        if self.buy:
            self.buy.t_record = self
            self.buy.timestamp = self.timestamp.astimezone(config.TZ_LOCAL)
            self.buy.wallet = self.wallet
        if self.sell:
            self.sell.t_record = self
            self.sell.timestamp = self.timestamp.astimezone(config.TZ_LOCAL)
            self.sell.wallet = self.wallet
        if self.fee:
            self.fee.t_record = self
            self.fee.timestamp = self.timestamp.astimezone(config.TZ_LOCAL)
            self.fee.wallet = self.wallet

    def set_tid(self):
        if self.tid is None:
            TransactionRecord.cnt += 1
            self.tid = [TransactionRecord.cnt, 0]
        else:
            self.tid[1] += 1

        return list(self.tid)

    def _format_fee(self):
        if self.fee:
            return " + fee=%s %s%s" % (
                self._format_quantity(self.fee.quantity),
                self.fee.asset,
                self._format_value(self.fee.proceeds))
        return ''

    @staticmethod
    def _format_quantity(quantity):
        if quantity is None:
            return ''
        return '{:0,f}'.format(quantity.normalize())

    @staticmethod
    def _format_value(value):
        if value is not None:
            return " (%s %s)" % (
                config.sym() + '{:0,.2f}'.format(value),
                config.CCY)
        return ''

    def __eq__(self, other):
        return self.timestamp == other.timestamp

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def __str__(self):
        if self.buy and self.sell:
            return "%s %s %s%s <- %s %s%s%s '%s' %s [TID:%s]" % (
                self.t_type,
                self._format_quantity(self.buy.quantity),
                self.buy.asset,
                self._format_value(self.buy.cost),
                self._format_quantity(self.sell.quantity),
                self.sell.asset,
                self._format_value(self.sell.proceeds),
                self._format_fee(),
                self.wallet,
                self.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z'),
                self.tid[0])
        elif self.buy:
            return "%s %s %s%s%s '%s' %s [TID:%s]" % (
                self.t_type,
                self._format_quantity(self.buy.quantity),
                self.buy.asset,
                self._format_value(self.buy.cost),
                self._format_fee(),
                self.wallet,
                self.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z'),
                self.tid[0])
        elif self.sell:
            return "%s %s %s%s%s '%s' %s [TID:%s]" % (
                self.t_type,
                self._format_quantity(self.sell.quantity),
                self.sell.asset,
                self._format_value(self.sell.proceeds),
                self._format_fee(),
                self.wallet,
                self.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z'),
                self.tid[0])

        return ''
