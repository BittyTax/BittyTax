# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

import dateutil.tz

from .bt_types import Note, Timestamp, TrType, Wallet
from .config import config

if TYPE_CHECKING:
    from .transactions import Buy, Sell

TZ_LOCAL = dateutil.tz.gettz(config.local_timezone)


# pylint: disable=too-few-public-methods, too-many-instance-attributes
class TransactionRecord:
    cnt = 0

    def __init__(
        self,
        t_type: TrType,
        buy: Optional["Buy"],
        sell: Optional["Sell"],
        fee: Optional["Sell"],
        wallet: Wallet,
        timestamp: Timestamp,
        note: Note,
    ) -> None:
        self.tid: Optional[List[int]] = None
        self.t_type = t_type
        self.buy = buy
        self.sell = sell
        self.fee = fee
        self.wallet = wallet
        self.timestamp = timestamp
        self.note = note

        if self.buy:
            self.buy.t_record = self
            self.buy.timestamp = Timestamp(self.timestamp.astimezone(TZ_LOCAL))
            self.buy.wallet = self.wallet
            self.buy.note = self.note
        if self.sell:
            self.sell.t_record = self
            self.sell.timestamp = Timestamp(self.timestamp.astimezone(TZ_LOCAL))
            self.sell.wallet = self.wallet
            self.sell.note = self.note
        if self.fee:
            self.fee.t_record = self
            self.fee.timestamp = Timestamp(self.timestamp.astimezone(TZ_LOCAL))
            self.fee.wallet = self.wallet
            self.fee.note = self.note

    def set_tid(self) -> List[int]:
        if self.tid is None:
            TransactionRecord.cnt += 1
            self.tid = [TransactionRecord.cnt, 0]
        else:
            self.tid[1] += 1

        return list(self.tid)

    def _format_tid(self) -> str:
        if self.tid:
            return f"[TID:{self.tid[0]}]"
        return ""

    def _format_fee(self) -> str:
        if self.fee:
            return (
                f" + fee={self._format_quantity(self.fee.quantity)} "
                f"{self.fee.asset}{self._format_value(self.fee.proceeds)}"
            )
        return ""

    def _format_note(self) -> str:
        if self.note:
            return f"'{self.note}' "
        return ""

    def _format_timestamp(self) -> str:
        if self.timestamp.microsecond:
            return f"{self.timestamp:%Y-%m-%dT%H:%M:%S.%f %Z}"
        return f"{self.timestamp:%Y-%m-%dT%H:%M:%S %Z}"

    @staticmethod
    def _format_quantity(quantity: Optional[Decimal]) -> str:
        if quantity is None:
            return ""
        return f"{quantity.normalize():0,f}"

    @staticmethod
    def _format_value(value: Optional[Decimal]) -> str:
        if value is not None:
            return f" ({config.sym()}{value:0,.2f} {config.ccy})"
        return ""

    @staticmethod
    def _format_decimal(decimal: Optional[Decimal]) -> str:
        if decimal is None:
            return ""
        return f"{decimal.normalize():0f}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TransactionRecord):
            return NotImplemented
        return self.timestamp == other.timestamp

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __lt__(self, other: "TransactionRecord") -> bool:
        return self.timestamp < other.timestamp

    def __str__(self) -> str:
        if self.buy and self.sell:
            return (
                f"{self.t_type.value} "
                f"{self._format_quantity(self.buy.quantity)} "
                f"{self.buy.asset}"
                f"{self._format_value(self.buy.cost)} <- "
                f"{self._format_quantity(self.sell.quantity)} "
                f"{self.sell.asset}"
                f"{self._format_value(self.sell.proceeds)}"
                f"{self._format_fee()} "
                f"'{self.wallet}' "
                f"{self._format_timestamp()} "
                f"{self._format_note()}"
                f"{self._format_tid()}"
            )
        if self.buy:
            return (
                f"{self.t_type.value} "
                f"{self._format_quantity(self.buy.quantity)} "
                f"{self.buy.asset}"
                f"{self._format_value(self.buy.cost)}"
                f"{self._format_fee()} "
                f"'{self.wallet}' "
                f"{self._format_timestamp()} "
                f"{self._format_note()}"
                f"{self._format_tid()}"
            )
        if self.sell:
            return (
                f"{self.t_type.value} "
                f"{self._format_quantity(self.sell.quantity)} "
                f"{self.sell.asset}"
                f"{self._format_value(self.sell.proceeds)}"
                f"{self._format_fee()} "
                f"'{self.wallet}' "
                f"{self._format_timestamp()} "
                f"{self._format_note()}"
                f"{self._format_tid()}"
            )
        return ""

    def to_csv(self) -> List[str]:
        if self.buy and self.sell:
            return [
                self.t_type.value,
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
                self._format_timestamp(),
                self.note,
            ]
        if self.buy:
            return [
                self.t_type.value,
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
                self._format_timestamp(),
                self.note,
            ]
        if self.sell:
            return [
                self.t_type.value,
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
                self._format_timestamp(),
                self.note,
            ]
        return []
