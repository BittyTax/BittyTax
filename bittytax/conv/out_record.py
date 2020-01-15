# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..record import TransactionRecord

class TransactionOutRecord(object):
    TYPE_DEPOSIT = TransactionRecord.TYPE_DEPOSIT
    TYPE_MINING = TransactionRecord.TYPE_MINING
    TYPE_INCOME = TransactionRecord.TYPE_INCOME
    TYPE_GIFT_RECEIVED = TransactionRecord.TYPE_GIFT_RECEIVED
    TYPE_WITHDRAWAL = TransactionRecord.TYPE_WITHDRAWAL
    TYPE_SPEND = TransactionRecord.TYPE_SPEND
    TYPE_GIFT_SENT = TransactionRecord.TYPE_GIFT_SENT
    TYPE_CHARITY_SENT = TransactionRecord.TYPE_CHARITY_SENT
    TYPE_TRADE = TransactionRecord.TYPE_TRADE

    def __init__(self, t_type, timestamp,
                 buy_quantity=None, buy_asset="", buy_value=None,
                 sell_quantity=None, sell_asset="", sell_value=None,
                 fee_quantity=None, fee_asset="", fee_value=None,
                 wallet=""):

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

    @staticmethod
    def format_quantity(quantity):
        if quantity is None:
            return '-'

        return '{:0,f}'.format(quantity.normalize())
