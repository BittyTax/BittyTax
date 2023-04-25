# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from .config import config


# pylint: disable=too-few-public-methods, too-many-instance-attributes
class TransactionRecord:
    TYPE_DEPOSIT = "Deposit"
    TYPE_MINING = "Mining"
    TYPE_STAKING = "Staking"
    TYPE_INTEREST = "Interest"
    TYPE_DIVIDEND = "Dividend"
    TYPE_INCOME = "Income"
    TYPE_GIFT_RECEIVED = "Gift-Received"
    TYPE_AIRDROP = "Airdrop"
    TYPE_WITHDRAWAL = "Withdrawal"
    TYPE_SPEND = "Spend"
    TYPE_GIFT_SENT = "Gift-Sent"
    TYPE_GIFT_SPOUSE = "Gift-Spouse"
    TYPE_CHARITY_SENT = "Charity-Sent"
    TYPE_LOST = "Lost"
    TYPE_TRADE = "Trade"

    ALL_TYPES = (
        TYPE_DEPOSIT,
        TYPE_MINING,
        TYPE_STAKING,
        TYPE_INCOME,
        TYPE_INTEREST,
        TYPE_DIVIDEND,
        TYPE_GIFT_RECEIVED,
        TYPE_AIRDROP,
        TYPE_WITHDRAWAL,
        TYPE_SPEND,
        TYPE_GIFT_SENT,
        TYPE_GIFT_SPOUSE,
        TYPE_CHARITY_SENT,
        TYPE_LOST,
        TYPE_TRADE,
    )

    cnt = 0

    def __init__(self, t_type, buy, sell, fee, wallet, timestamp, note):
        self.tid = None
        self.t_type = t_type
        self.buy = buy
        self.sell = sell
        self.fee = fee
        self.wallet = wallet
        self.timestamp = timestamp
        self.note = note

        if self.buy:
            self.buy.t_record = self
            self.buy.timestamp = self.timestamp.astimezone(config.TZ_LOCAL)
            self.buy.wallet = self.wallet
            self.buy.note = self.note
        if self.sell:
            self.sell.t_record = self
            self.sell.timestamp = self.timestamp.astimezone(config.TZ_LOCAL)
            self.sell.wallet = self.wallet
            self.sell.note = self.note
        if self.fee:
            self.fee.t_record = self
            self.fee.timestamp = self.timestamp.astimezone(config.TZ_LOCAL)
            self.fee.wallet = self.wallet
            self.fee.note = self.note

    def set_tid(self):
        if self.tid is None:
            TransactionRecord.cnt += 1
            self.tid = [TransactionRecord.cnt, 0]
        else:
            self.tid[1] += 1

        return list(self.tid)

    def _format_fee(self):
        if self.fee:
            return (
                f" + fee={self._format_quantity(self.fee.quantity)} "
                f"{self.fee.asset}{self._format_value(self.fee.proceeds)}"
            )
        return ""

    @staticmethod
    def _format_quantity(quantity):
        if quantity is None:
            return ""
        return f"{quantity.normalize():0,f}"

    @staticmethod
    def _format_value(value):
        if value is not None:
            return f" ({config.sym()}{value:0,.2f} {config.ccy})"
        return ""

    @staticmethod
    def _format_note(note):
        if note:
            return f"'{note}' "
        return ""

    @staticmethod
    def _format_timestamp(timestamp):
        if timestamp.microsecond:
            return f"{timestamp:%Y-%m-%dT%H:%M:%S.%f %Z}"
        return f"{timestamp:%Y-%m-%dT%H:%M:%S %Z}"

    @staticmethod
    def _format_decimal(decimal):
        if decimal is None:
            return ""
        return f"{decimal.normalize():0f}"

    def __eq__(self, other):
        return self.timestamp == other.timestamp

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def __str__(self):
        if self.buy and self.sell:
            return (
                f"{self.t_type} "
                f"{self._format_quantity(self.buy.quantity)} "
                f"{self.buy.asset}"
                f"{self._format_value(self.buy.cost)} <- "
                f"{self._format_quantity(self.sell.quantity)} "
                f"{self.sell.asset}"
                f"{self._format_value(self.sell.proceeds)}"
                f"{self._format_fee()} "
                f"'{self.wallet}' "
                f"{self._format_timestamp(self.timestamp)} "
                f"{self._format_note(self.note)}"
                f"[TID:{self.tid[0]}]"
            )
        if self.buy:
            return (
                f"{self.t_type} "
                f"{self._format_quantity(self.buy.quantity)} "
                f"{self.buy.asset}"
                f"{self._format_value(self.buy.cost)}"
                f"{self._format_fee()} "
                f"'{self.wallet}' "
                f"{self._format_timestamp(self.timestamp)} "
                f"{self._format_note(self.note)}"
                f"[TID:{self.tid[0]}]"
            )
        if self.sell:
            return (
                f"{self.t_type} "
                f"{self._format_quantity(self.sell.quantity)} "
                f"{self.sell.asset}"
                f"{self._format_value(self.sell.proceeds)}"
                f"{self._format_fee()} "
                f"'{self.wallet}' "
                f"{self._format_timestamp(self.timestamp)} "
                f"{self._format_note(self.note)}"
                f"[TID:{self.tid[0]}]"
            )
        return []

    def to_csv(self):
        if self.buy and self.sell:
            return [
                self.t_type,
                self._format_decimal(self.buy.quantity),
                self.buy.asset,
                self._format_decimal(self.buy.cost),
                self._format_decimal(self.sell.quantity),
                self.sell.asset,
                self._format_decimal(self.sell.proceeds),
                self._format_decimal(self.fee.quantity) if self.fee else "",
                self.fee.asset if self.fee else "",
                self._format_decimal(self.fee.proceeds) if self.fee else "",
                self.wallet,
                self._format_timestamp(self.timestamp),
                self.note,
            ]
        if self.buy:
            return [
                self.t_type,
                self._format_decimal(self.buy.quantity),
                self.buy.asset,
                self._format_decimal(self.buy.cost),
                "",
                "",
                "",
                self._format_decimal(self.fee.quantity) if self.fee else "",
                self.fee.asset if self.fee else "",
                self._format_decimal(self.fee.proceeds) if self.fee else "",
                self.wallet,
                self._format_timestamp(self.timestamp),
                self.note,
            ]
        if self.sell:
            return [
                self.t_type,
                "",
                "",
                "",
                self._format_decimal(self.sell.quantity),
                self.sell.asset,
                self._format_decimal(self.sell.proceeds),
                self._format_decimal(self.fee.quantity) if self.fee else "",
                self.fee.asset if self.fee else "",
                self._format_decimal(self.fee.proceeds) if self.fee else "",
                self.wallet,
                self._format_timestamp(self.timestamp),
                self.note,
            ]
        return []
