# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from .config import config

class TransactionRecordBase(object):
    TYPE_DEPOSIT = 'Deposit'
    TYPE_MINING = 'Mining'
    TYPE_INCOME = 'Income'
    TYPE_GIFT_RECEIVED = 'Gift-Received'
    TYPE_WITHDRAWAL = 'Withdrawal'
    TYPE_SPEND = 'Spend'
    TYPE_GIFT_SENT = 'Gift-Sent'
    TYPE_CHARITY_SENT = 'Charity-Sent'
    TYPE_TRADE = 'Trade'

    BUY_TYPES = (TYPE_DEPOSIT, TYPE_MINING, TYPE_INCOME, TYPE_GIFT_RECEIVED)
    SELL_TYPES = (TYPE_WITHDRAWAL, TYPE_SPEND, TYPE_GIFT_SENT, TYPE_CHARITY_SENT)

    BUY_VALUE_TYPES = (TYPE_MINING, TYPE_INCOME, TYPE_GIFT_RECEIVED)
    SELL_VALUE_TYPES = (TYPE_SPEND, TYPE_GIFT_SENT, TYPE_CHARITY_SENT)

    cnt = 0

    def __init__(self, t_type, timestamp,
                 buy_quantity=None, buy_asset="", buy_value=None,
                 sell_quantity=None, sell_asset="", sell_value=None,
                 fee_quantity=None, fee_asset="", fee_value=None,
                 wallet=""):

        self.tid = None
        self.t_type = t_type
        self.buy_quantity = Decimal(buy_quantity) if buy_quantity is not None else None
        self.buy_asset = buy_asset
        self.buy_value = Decimal(buy_value) if buy_value is not None else None
        self.sell_quantity = Decimal(sell_quantity) if sell_quantity is not None else None
        self.sell_asset = sell_asset
        self.sell_value = Decimal(sell_value) if sell_value is not None else None
        self.fee_quantity = Decimal(fee_quantity) if fee_quantity is not None else None
        self.fee_asset = fee_asset
        self.fee_value = Decimal(fee_value) if fee_value is not None else None
        self.wallet = wallet
        self.timestamp = timestamp

    def set_tid(self):
        TransactionRecordBase.cnt += 1
        self.tid = TransactionRecordBase.cnt

    @staticmethod
    def format_quantity(quantity):
        if quantity is None:
            return '-'

        return '{:0,f}'.format(quantity.normalize())

    @staticmethod
    def format_value(value):
        if value is not None:
            return ' (' + config.sym() + '{:0,.2f} {})'.format(value, config.CCY)

        return ''

    def __eq__(self, other):
        return self.timestamp == other.timestamp

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def __str__(self):
        if self.t_type in self.BUY_TYPES:
            return "[TID:" + str(self.tid) + "] " + \
                   self.t_type + ": " + \
                   self.format_quantity(self.buy_quantity) + " " + \
                   self.buy_asset + \
                   self.format_value(self.buy_value) + " '" + \
                   self.wallet + "' " + \
                   self.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z')
        elif self.t_type in self.SELL_TYPES:
            return "[TID:" + str(self.tid) + "] " + \
                   self.t_type + ": " + \
                   self.format_quantity(self.sell_quantity) + " " + \
                   self.sell_asset + \
                   self.format_value(self.sell_value) + " '" + \
                   self.wallet + "' " + \
                   self.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z')
        else:
            return "[TID:" + str(self.tid) + "] " + \
                   self.t_type + ": " + \
                   self.format_quantity(self.buy_quantity) + " " + \
                   self.buy_asset + \
                   self.format_value(self.buy_value) + " <- " + \
                   self.format_quantity(self.sell_quantity) + " " + \
                   self.sell_asset + \
                   self.format_value(self.sell_value) + " '" + \
                   self.wallet + "' " + \
                   self.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z')

class TransactionInRecord(TransactionRecordBase):
    def include_fees(self):
        # Include fees within buy/sell portion
        if self.buy_asset == self.fee_asset:
            self.buy_quantity -= self.fee_quantity
            if self.fee_value:
                self.buy_value -= self.fee_value

            self.fee_quantity = None
            self.fee_asset = ""
            self.fee_value = None
        elif self.sell_asset == self.fee_asset:
            self.sell_quantity += self.fee_quantity
            if self.fee_value:
                self.sell_value += self.fee_value

            self.fee_quantity = None
            self.fee_asset = ""
            self.fee_value = None
