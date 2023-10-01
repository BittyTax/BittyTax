# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from datetime import datetime
from decimal import Decimal
from typing import Optional, Union

from ..config import config
from ..types import BUY_TYPES, SELL_TYPES, TrType, UnmappedType


class TransactionOutRecord:  # pylint: disable=too-many-instance-attributes
    WALLET_ADDR_LEN = 10

    def __init__(
        self,
        t_type: Union[TrType, UnmappedType],
        timestamp: datetime,
        buy_quantity: Optional[Decimal] = None,
        buy_asset: str = "",
        buy_value: Optional[Decimal] = None,
        sell_quantity: Optional[Decimal] = None,
        sell_asset: str = "",
        sell_value: Optional[Decimal] = None,
        fee_quantity: Optional[Decimal] = None,
        fee_asset: str = "",
        fee_value: Optional[Decimal] = None,
        wallet: str = "",
        note: str = "",
    ) -> None:
        self.t_type = t_type
        self.buy_quantity = buy_quantity
        self.buy_asset = buy_asset
        self.buy_value = buy_value
        self.sell_quantity = sell_quantity
        self.sell_asset = sell_asset
        self.sell_value = sell_value
        self.fee_quantity = fee_quantity
        self.fee_asset = fee_asset
        self.fee_value = fee_value
        self.wallet = wallet
        self.timestamp = timestamp
        self.note = note

    def __str__(self) -> str:
        if self.t_type is TrType.TRADE:
            return (
                f"{self.format_type()} "
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
        if self.t_type in BUY_TYPES:
            return (
                f"{self.format_type()} "
                f"{self.format_quantity(self.buy_quantity)} "
                f"{self.buy_asset}"
                f"{self.format_value(self.buy_value)}"
                f"{self.format_fee()} "
                f"'{self.wallet}' "
                f"{self.format_timestamp(self.timestamp)} "
                f"{self.format_note(self.note)}"
            )
        if self.t_type in SELL_TYPES:
            return (
                f"{self.format_type()} "
                f"{self.format_quantity(self.sell_quantity)} "
                f"{self.sell_asset}"
                f"{self.format_value(self.sell_value)}"
                f"{self.format_fee()} "
                f"'{self.wallet}' "
                f"{self.format_timestamp(self.timestamp)} "
                f"{self.format_note(self.note)}"
            )
        return ""

    # Used for consolidation in merge parsers
    def get_asset(self) -> str:
        if self.t_type is TrType.TRADE:
            raise RuntimeError("Unexpected TRADE")

        if self.t_type in BUY_TYPES:
            return self.buy_asset
        if self.t_type in SELL_TYPES:
            return self.sell_asset
        return ""

    def get_quantity(self) -> Decimal:
        if self.t_type is TrType.TRADE:
            raise RuntimeError("Unexpected TRADE")

        if self.t_type in BUY_TYPES and self.buy_quantity is not None:
            return self.buy_quantity
        if self.t_type in SELL_TYPES and self.sell_quantity is not None:
            return -abs(self.sell_quantity)
        return Decimal(0)

    def format_type(self) -> str:
        if isinstance(self.t_type, TrType):
            return self.t_type.value
        return self.t_type

    @staticmethod
    def format_quantity(quantity: Optional[Decimal]) -> str:
        if quantity is None:
            return ""
        return f"{quantity.normalize():0,f}"

    def format_fee(self) -> str:
        if self.fee_quantity:
            return (
                f" + fee={self.format_quantity(self.fee_quantity)} "
                f"{self.fee_asset}{self.format_value(self.fee_value)}"
            )
        return ""

    @staticmethod
    def format_value(value: Optional[Decimal]) -> str:
        if value is not None:
            return f" ({config.sym()}{value:0,.2f} {config.ccy})"
        return ""

    @staticmethod
    def format_note(note: str) -> str:
        if note:
            return f"'{note}'"
        return ""

    @staticmethod
    def format_timestamp(timestamp: datetime) -> str:
        if timestamp.microsecond:
            return f"{timestamp:%Y-%m-%dT%H:%M:%S.%f %Z}"
        return f"{timestamp:%Y-%m-%dT%H:%M:%S %Z}"
