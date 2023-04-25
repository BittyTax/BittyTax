# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..config import config
from ..record import TransactionRecord


class TransactionOutRecord:  # pylint: disable=too-many-instance-attributes
    TYPE_DEPOSIT = TransactionRecord.TYPE_DEPOSIT
    TYPE_MINING = TransactionRecord.TYPE_MINING
    TYPE_STAKING = TransactionRecord.TYPE_STAKING
    TYPE_INTEREST = TransactionRecord.TYPE_INTEREST
    TYPE_DIVIDEND = TransactionRecord.TYPE_DIVIDEND
    TYPE_INCOME = TransactionRecord.TYPE_INCOME
    TYPE_GIFT_RECEIVED = TransactionRecord.TYPE_GIFT_RECEIVED
    TYPE_AIRDROP = TransactionRecord.TYPE_AIRDROP
    TYPE_WITHDRAWAL = TransactionRecord.TYPE_WITHDRAWAL
    TYPE_SPEND = TransactionRecord.TYPE_SPEND
    TYPE_GIFT_SENT = TransactionRecord.TYPE_GIFT_SENT
    TYPE_GIFT_SPOUSE = TransactionRecord.TYPE_GIFT_SPOUSE
    TYPE_CHARITY_SENT = TransactionRecord.TYPE_CHARITY_SENT
    TYPE_LOST = TransactionRecord.TYPE_LOST
    TYPE_TRADE = TransactionRecord.TYPE_TRADE

    ALL_TYPES = TransactionRecord.ALL_TYPES

    BUY_TYPES = (
        TYPE_DEPOSIT,
        TYPE_MINING,
        TYPE_STAKING,
        TYPE_INTEREST,
        TYPE_DIVIDEND,
        TYPE_INCOME,
        TYPE_GIFT_RECEIVED,
        TYPE_AIRDROP,
    )

    SELL_TYPES = (
        TYPE_WITHDRAWAL,
        TYPE_SPEND,
        TYPE_GIFT_SENT,
        TYPE_GIFT_SPOUSE,
        TYPE_CHARITY_SENT,
        TYPE_LOST,
    )

    WALLET_ADDR_LEN = 10

    def __init__(
        self,
        t_type,
        timestamp,
        buy_quantity=None,
        buy_asset="",
        buy_value=None,
        sell_quantity=None,
        sell_asset="",
        sell_value=None,
        fee_quantity=None,
        fee_asset="",
        fee_value=None,
        wallet="",
        note="",
    ):
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
        self.note = note

    def __str__(self):
        if self.t_type == self.TYPE_TRADE:
            return (
                f"{self.t_type} "
                f"{self.format_quantity(self.buy_quantity)} "
                f"{self.buy_asset}"
                f"{self.format_value(self.buy_value)} <- "
                f"{self.format_quantity(self.sell_quantity)} "
                f"{self.sell_asset}"
                f"{self.format_value(self.sell_value)}"
                f"{self.format_fee()} "
                f"'{self.wallet}' "
                f"{self.format_timestamp(self.timestamp)} "
                f"{self.format_note(self.note)}"
            )
        if self.t_type in self.BUY_TYPES:
            return (
                f"{self.t_type} "
                f"{self.format_quantity(self.buy_quantity)} "
                f"{self.buy_asset}"
                f"{self.format_value(self.buy_value)}"
                f"{self.format_fee()} "
                f"'{self.wallet}' "
                f"{self.format_timestamp(self.timestamp)} "
                f"{self.format_note(self.note)}"
            )
        if self.t_type in self.SELL_TYPES:
            return (
                f"{self.t_type} "
                f"{self.format_quantity(self.sell_quantity)} "
                f"{self.sell_asset}"
                f"{self.format_value(self.sell_value)}"
                f"{self.format_fee()} "
                f"'{self.wallet}' "
                f"{self.format_timestamp(self.timestamp)} "
                f"{self.format_note(self.note)}"
            )
        return []

    # Used for consolidation in merge parsers
    def get_asset(self):
        if self.t_type in self.BUY_TYPES:
            return self.buy_asset
        if self.t_type in self.SELL_TYPES:
            return self.sell_asset
        return ""

    def get_quantity(self):
        if self.t_type in self.BUY_TYPES:
            return self.buy_quantity
        if self.t_type in self.SELL_TYPES:
            return -abs(self.sell_quantity)
        return Decimal(0)

    @staticmethod
    def format_quantity(quantity):
        if quantity is None:
            return ""
        return f"{quantity.normalize():0,f}"

    def format_fee(self):
        if self.fee_quantity:
            return (
                f" + fee={self.format_quantity(self.fee_quantity)} "
                f"{self.fee_asset}{self.format_value(self.fee_value)}"
            )
        return ""

    @staticmethod
    def format_value(value):
        if value is not None:
            return f" ({config.sym()}{value:0,.2f} {config.ccy})"
        return ""

    @staticmethod
    def format_note(note):
        if note:
            return f"'{note}' "
        return ""

    @staticmethod
    def format_timestamp(timestamp):
        if timestamp.microsecond:
            return f"{timestamp:%Y-%m-%dT%H:%M:%S.%f %Z}"
        return f"{timestamp:%Y-%m-%dT%H:%M:%S %Z}"
