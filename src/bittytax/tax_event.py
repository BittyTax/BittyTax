# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019
# pylint: disable=bad-option-value, unnecessary-dunder-call

from decimal import Decimal
from typing import List, Optional, Union

from .bt_types import AssetSymbol, Date, DisposalType, TrType
from .config import config
from .constants import ACQUISITIONS_VARIOUS
from .transactions import Buy, Sell

PRECISION = Decimal("0.00")


class TaxEvent:
    def __init__(self, date: Date, asset: AssetSymbol) -> None:
        self.date = date
        self.asset = asset

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TaxEvent):
            return NotImplemented
        return self.date == other.date

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __lt__(self, other: "TaxEvent") -> bool:
        return self.date < other.date


class TaxEventCapitalGains(TaxEvent):
    def __init__(
        self,
        disposal_type: DisposalType,
        b: List[Buy],
        s: Sell,
        cost: Decimal,
        proceeds: Decimal,
    ) -> None:
        super().__init__(s.date(), s.asset)
        self.disposal_type = disposal_type
        self.buys = b
        self.sell = s
        self.quantity = s.quantity
        self.cost = cost
        self.proceeds = proceeds
        self.gain = self.proceeds - self.cost
        self.acquisition_dates = [buy.date() for buy in self.buys]

    def format_disposal(self) -> str:
        if self.acquisition_dates:
            if self.disposal_type in (DisposalType.BED_AND_BREAKFAST, DisposalType.TEN_DAY):
                return f"{self.disposal_type.value} ({self.acquisition_dates[0]:%d/%m/%Y})"

        return self.disposal_type.value

    def a_date(self, date_format: Optional[str] = None) -> str:
        if self.acquisition_dates:
            if len(self.acquisition_dates) > 1 and not all(
                date == self.acquisition_dates[0] for date in self.acquisition_dates
            ):
                return ACQUISITIONS_VARIOUS
            if date_format:
                return f"{self.acquisition_dates[0]:{date_format}}"
            return f"{self.acquisition_dates[0]:{config.date_format}}"
        return ""

    def __str__(self) -> str:
        return (
            f"CapitalGain({self.disposal_type.value.lower()}) gain="
            f"{config.sym()}{self.gain:0,.2f} "
            f"(proceeds={config.sym()}{self.proceeds:0,.2f} - cost="
            f"{config.sym()}{self.cost:0,.2f})"
        )


class TaxEventNoGainNoLoss(TaxEvent):
    def __init__(
        self,
        disposal_type: DisposalType,
        b: List[Buy],
        s: Sell,
        cost: Decimal,
        market_value: Decimal,
    ) -> None:
        super().__init__(s.date(), s.asset)
        self.disposal_type = disposal_type
        self.buys = b
        self.sell = s
        self.t_type = s.t_type
        self.note = s.note
        self.quantity = s.quantity
        self.cost = cost
        self.market_value = market_value
        self.acquisition_dates = [buy.date() for buy in self.buys]

    def format_disposal(self) -> str:
        return self.disposal_type.value

    def __str__(self) -> str:
        return (
            f"NoGainNoLoss({self.disposal_type.value.lower()}) "
            f"market_value={config.sym()}{self.market_value:0,.2f} cost="
            f"{config.sym()}{self.cost:0,.2f}"
        )


class TaxEventIncome(TaxEvent):  # pylint: disable=too-few-public-methods
    def __init__(self, b: Buy) -> None:
        super().__init__(b.date(), b.asset)

        if b.cost is None:
            raise RuntimeError("Missing cost")

        self.buy = b
        self.type = b.t_type
        self.quantity = b.quantity
        self.amount = b.cost.quantize(PRECISION)
        self.note = b.note
        if b.fee_value:
            self.fees = b.fee_value.quantize(PRECISION)
        else:
            self.fees = Decimal(0)


class TaxEventMarginTrade(TaxEvent):  # pylint: disable=too-few-public-methods
    def __init__(self, t: Union[Buy, Sell]) -> None:
        super().__init__(t.date(), config.local_currency)
        self.wallet = t.wallet
        self.note = t.note
        self.gain = Decimal(0)
        self.loss = Decimal(0)
        self.fee = Decimal(0)
        self.fee_rebate = Decimal(0)
        self.t = t

        if isinstance(t, Buy) and t.t_type == TrType.MARGIN_GAIN:
            if t.cost is None:
                raise RuntimeError("Missing cost")

            self.gain = t.cost.quantize(PRECISION)
        elif isinstance(t, Sell) and t.t_type == TrType.MARGIN_LOSS:
            if t.proceeds is None:
                raise RuntimeError("Missing proceeds")

            self.loss = t.proceeds.quantize(PRECISION)
        elif isinstance(t, Sell) and t.t_type == TrType.MARGIN_FEE:
            if t.proceeds is None:
                raise RuntimeError("Missing proceeds")

            self.fee = t.proceeds.quantize(PRECISION)
        elif isinstance(t, Buy) and t.t_type == TrType.MARGIN_FEE_REBATE:
            if t.cost is None:
                raise RuntimeError("Missing cost")

            self.fee_rebate = t.cost.quantize(PRECISION)
