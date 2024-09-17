# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019
# pylint: disable=bad-option-value, unnecessary-dunder-call

import copy
import datetime
import itertools
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Iterator, List, Optional, Tuple, Union

import requests
from colorama import Fore
from dateutil.relativedelta import relativedelta
from tqdm import tqdm
from typing_extensions import NotRequired, TypedDict

from .bt_types import (
    TRANSFER_TYPES,
    AssetName,
    AssetSymbol,
    Date,
    DisposalType,
    Note,
    TrType,
    Wallet,
    Year,
)
from .config import config
from .constants import TAX_RULES_UK_COMPANY, WARNING
from .holdings import Holdings
from .price.valueasset import ValueAsset
from .tax_event import (
    TaxEvent,
    TaxEventCapitalGains,
    TaxEventIncome,
    TaxEventMarginTrade,
    TaxEventNoGainNoLoss,
)
from .transactions import Buy, Sell

PRECISION = Decimal("0.00")


class TaxReportRecord(TypedDict):  # pylint: disable=too-few-public-methods
    CapitalGains: "CalculateCapitalGains"
    Income: NotRequired["CalculateIncome"]
    MarginTrading: NotRequired["CalculateMarginTrading"]


class HoldingsReportAsset(TypedDict):  # pylint: disable=too-few-public-methods
    name: AssetName
    quantity: Decimal
    cost: Decimal
    value: Optional[Decimal]
    gain: NotRequired[Decimal]


class HoldingsReportTotal(TypedDict):  # pylint: disable=too-few-public-methods
    cost: Decimal
    value: Decimal
    gain: Decimal


class HoldingsReportRecord(TypedDict):  # pylint: disable=too-few-public-methods
    holdings: Dict[AssetSymbol, HoldingsReportAsset]
    totals: HoldingsReportTotal


class CapitalGainsIndividual(TypedDict):  # pylint: disable=too-few-public-methods
    allowance: Decimal
    basic_rate: Decimal
    higher_rate: Decimal
    proceeds_limit: NotRequired[Decimal]


class ChargableGainsCompany(TypedDict):  # pylint: disable=too-few-public-methods
    small_rate: Optional[Decimal]
    main_rate: Decimal


class CapitalGainsReportTotal(TypedDict):  # pylint: disable=too-few-public-methods
    cost: Decimal
    fees: Decimal
    proceeds: Decimal
    gain: Decimal


class CapitalGainsReportSummary(TypedDict):  # pylint: disable=too-few-public-methods
    disposals: Decimal
    total_gain: Decimal
    total_loss: Decimal


class CapitalGainsReportEstimate(TypedDict):  # pylint: disable=too-few-public-methods
    allowance: Decimal
    cgt_basic_rate: Decimal
    cgt_higher_rate: Decimal
    allowance_used: Decimal
    taxable_gain: Decimal
    cgt_basic: Decimal
    cgt_higher: Decimal
    proceeds_limit: Decimal
    proceeds_warning: bool


class ChargableGainsReportEstimate(TypedDict):  # pylint: disable=too-few-public-methods
    ct_small_rates: List[Optional[Decimal]]
    ct_main_rates: List[Decimal]
    taxable_gain: Decimal
    ct_small: NotRequired[Decimal]
    ct_main: Decimal


class IncomeReportTotal(TypedDict):  # pylint: disable=too-few-public-methods
    amount: Decimal
    fees: Decimal


@dataclass
class BuyAccumulator:
    quantity: Decimal = Decimal(0)
    cost: Decimal = Decimal(0)
    fee_value: Decimal = Decimal(0)
    dates: List[Date] = field(default_factory=list)


class MarginReportTotal(TypedDict):  # pylint: disable=too-few-public-methods
    gains: Decimal
    losses: Decimal
    fees: Decimal


class TaxCalculator:  # pylint: disable=too-many-instance-attributes
    INCOME_TYPES = (
        TrType.MINING,
        TrType.STAKING_REWARD,
        TrType.STAKING,
        TrType.DIVIDEND,
        TrType.INTEREST,
        TrType.INCOME,
        TrType.FORK,
        TrType.AIRDROP,
        TrType.REFERRAL,
        TrType.CASHBACK,
        TrType.FEE_REBATE,
    )

    NO_GAIN_NO_LOSS_TYPES = (
        TrType.GIFT_SENT,
        TrType.GIFT_SPOUSE,
        TrType.CHARITY_SENT,
        TrType.LOST,
        TrType.SWAP,
        TrType.CRYPTO_CRYPTO,
    )

    MARGIN_TYPES = (TrType.MARGIN_GAIN, TrType.MARGIN_LOSS, TrType.MARGIN_FEE)

    def __init__(self, transactions: List[Union[Buy, Sell]], tax_rules: str) -> None:
        self.transactions = transactions
        self.tax_rules = tax_rules
        self.buys_ordered: Dict[AssetSymbol, List[Buy]] = {}
        self.sells_ordered: List[Sell] = []
        self.other_transactions: List[Union[Buy, Sell]] = []

        self.match_missing = False
        self.tax_events: Dict[Year, List[TaxEvent]] = {}
        self.holdings: Dict[AssetSymbol, Holdings] = {}

        self.tax_report: Dict[Year, TaxReportRecord] = {}
        self.holdings_report: Optional[HoldingsReportRecord] = None

    def order_transactions(self) -> None:
        if config.debug:
            print(f"{Fore.CYAN}order transactions")

        for t in tqdm(
            self.transactions,
            unit="t",
            desc=f"{Fore.CYAN}order transactions{Fore.GREEN}",
            disable=bool(config.debug or not sys.stdout.isatty()),
        ):
            if isinstance(t, Buy) and t.is_crypto() and t.acquisition:
                if t.asset not in self.buys_ordered:
                    self.buys_ordered[t.asset] = []

                self.buys_ordered[t.asset].append(t)
            elif isinstance(t, Sell) and t.is_crypto() and t.disposal:
                self.sells_ordered.append(t)
            else:
                self.other_transactions.append(t)

        if config.debug:
            for a in sorted(self.buys_ordered):
                for t in self.buys_ordered[a]:
                    print(f"{Fore.GREEN}buys: {t}")

            for t in self.sells_ordered:
                print(f"{Fore.GREEN}sells: {t}")

    def fifo_match(self) -> None:
        # Keep copy for income tax processing
        self.transactions = copy.deepcopy(self.transactions)

        if config.debug:
            print(f"{Fore.CYAN}fifo match transactions")

        buy_index = {}

        for s in tqdm(
            self.sells_ordered,
            unit="t",
            desc=f"{Fore.CYAN}fifo match transactions{Fore.GREEN}",
            disable=bool(config.debug or not sys.stdout.isatty()),
        ):
            matches = []
            s_quantity_remaining = s.quantity

            if config.debug:
                print(f"{Fore.GREEN}fifo: {s}")

            if s.asset not in buy_index:
                buy_index[s.asset] = 0

            while (
                s.asset in self.buys_ordered
                and buy_index[s.asset] < len(self.buys_ordered[s.asset])
                and s_quantity_remaining > 0
            ):
                b = self.buys_ordered[s.asset][buy_index[s.asset]]

                if b.date() > s.date():
                    break

                if b.quantity > s_quantity_remaining:
                    b_remainder = b.split_buy(s_quantity_remaining)
                    self.buys_ordered[s.asset].insert(buy_index[s.asset] + 1, b_remainder)

                    if config.debug:
                        print(f"{Fore.GREEN}fifo: {b} <-- split")
                        print(f"{Fore.YELLOW}fifo:   {b_remainder} <-- split")
                else:
                    if config.debug:
                        print(f"{Fore.GREEN}fifo: {b}")

                b.matched = True
                matches.append(b)
                s_quantity_remaining -= b.quantity

                buy_index[s.asset] += 1

            if s_quantity_remaining > 0:
                tqdm.write(
                    f"{WARNING} No matching Buy of {s_quantity_remaining.normalize():0,f} "
                    f"{s.asset} for Sell of {s.format_quantity()} {s.asset}"
                )
                if config.cost_basis_zero_if_missing:
                    buy_match = Buy(TrType.TRADE, s_quantity_remaining, s.asset, Decimal(0))
                    buy_match.wallet = s.wallet
                    buy_match.timestamp = s.timestamp
                    buy_match.note = Note("Added as cost basis zero")
                    tqdm.write(f"{Fore.GREEN}fifo: {buy_match}")
                    matches.append(buy_match)
                    s.matched = True
                    self._create_disposal(s, matches)
                else:
                    self.match_missing = True
            else:
                s.matched = True
                self._create_disposal(s, matches)

    def lifo_match(self) -> None:
        # Keep copy for income tax processing
        self.transactions = copy.deepcopy(self.transactions)

        if config.debug:
            print(f"{Fore.CYAN}lifo match transactions")

        buy_index = {}

        for s in tqdm(
            self.sells_ordered,
            unit="t",
            desc=f"{Fore.CYAN}lifo match transactions{Fore.GREEN}",
            disable=bool(config.debug or not sys.stdout.isatty()),
        ):
            matches = []
            s_quantity_remaining = s.quantity

            if config.debug:
                print(f"{Fore.GREEN}lifo: {s}")

            if s.asset in self.buys_ordered:
                for i in reversed(range(len(self.buys_ordered[s.asset]))):
                    if self.buys_ordered[s.asset][i].date() <= s.date() and not self.buys_ordered[s.asset][i].matched:
                        buy_index[s.asset] = i
                        break
                else:
                    buy_index[s.asset] = -1

            while (
                s.asset in self.buys_ordered
                and buy_index[s.asset] >= 0
                and s_quantity_remaining > 0
            ):
                b = self.buys_ordered[s.asset][buy_index[s.asset]]

                if b.date() > s.date():
                    break

                if b.matched:
                    buy_index[s.asset] -= 1
                    continue

                if b.quantity > s_quantity_remaining:
                    b_remainder = b.split_buy(s_quantity_remaining)
                    self.buys_ordered[s.asset].insert(buy_index[s.asset] + 1, b_remainder)

                    if config.debug:
                        print(f"{Fore.GREEN}lifo: {b} <-- split")
                        print(f"{Fore.YELLOW}lifo:   {b_remainder} <-- split")
                else:
                    if config.debug:
                        print(f"{Fore.GREEN}lifo: {b}")

                b.matched = True
                matches.append(b)
                s_quantity_remaining -= b.quantity

                buy_index[s.asset] -= 1

            if s_quantity_remaining > 0:
                tqdm.write(
                    f"{WARNING} No matching Buy of {s_quantity_remaining.normalize():0,f} "
                    f"{s.asset} for Sell of {s.format_quantity()} {s.asset}"
                )
                if config.cost_basis_zero_if_missing:
                    buy_match = Buy(TrType.TRADE, s_quantity_remaining, s.asset, Decimal(0))
                    buy_match.wallet = s.wallet
                    buy_match.timestamp = s.timestamp
                    buy_match.note =  Note("Added as cost basis zero")
                    tqdm.write(f"{Fore.GREEN}lifo: {buy_match}")
                    matches.append(buy_match)
                    s.matched = True
                    self._create_disposal(s, matches)
                else:
                    self.match_missing = True
            else:
                s.matched = True
                self._create_disposal(s, matches)

    def _create_disposal(self, sell: Sell, matches: List[Buy]) -> None:
        short_term = BuyAccumulator()
        long_term = BuyAccumulator()

        for buy in matches:
            if buy.cost is None:
                raise RuntimeError("Missing cost")

            if sell.date() <= buy.date() + relativedelta(years=1):
                short_term.quantity += buy.quantity
                short_term.cost += buy.cost
                if buy.fee_value:
                    short_term.fee_value += buy.fee_value
                short_term.dates.append(buy.date())
            else:
                long_term.quantity += buy.quantity
                long_term.cost += buy.cost
                if buy.fee_value:
                    long_term.fee_value += buy.fee_value
                long_term.dates.append(buy.date())

        if short_term.dates:
            sell_adjusted = copy.deepcopy(sell)
            if sell.proceeds is None:
                raise RuntimeError("Missing sell.proceeds")

            if sell.fee_value:
                sell_adjusted.proceeds = sell.proceeds.quantize(
                    PRECISION
                ) - sell.fee_value.quantize(PRECISION)

                if sell_adjusted.proceeds < 0:
                    sell_adjusted.proceeds = Decimal(0)

            if sell_adjusted.proceeds is None:
                raise RuntimeError("Missing sell_adjusted.proceeds")

            sell_adjusted.proceeds = sell_adjusted.proceeds * (short_term.quantity / sell.quantity)

            if sell.t_type in self.NO_GAIN_NO_LOSS_TYPES:
                tax_event: Union[TaxEventCapitalGains, TaxEventNoGainNoLoss] = TaxEventNoGainNoLoss(
                    DisposalType.SHORT_TERM,
                    sell_adjusted,
                    short_term.cost.quantize(PRECISION) + short_term.fee_value.quantize(PRECISION),
                    Decimal(0),
                    short_term.dates,
                )
            else:
                tax_event = TaxEventCapitalGains(
                    DisposalType.SHORT_TERM,
                    sell_adjusted,
                    short_term.cost.quantize(PRECISION) + short_term.fee_value.quantize(PRECISION),
                    Decimal(0),
                    short_term.dates,
                )
            self.tax_events[self._which_tax_year(tax_event.date)].append(tax_event)

            if config.debug:
                print(f"{Fore.CYAN}fifo: {tax_event}")

        if long_term.dates:
            sell_adjusted = copy.deepcopy(sell)
            if sell.proceeds is None:
                raise RuntimeError("Missing sell.proceeds")

            if sell.fee_value:
                sell_adjusted.proceeds = sell.proceeds.quantize(
                    PRECISION
                ) - sell.fee_value.quantize(PRECISION)

                if sell_adjusted.proceeds < 0:
                    sell_adjusted.proceeds = Decimal(0)

            if sell_adjusted.proceeds is None:
                raise RuntimeError("Missing sell_adjusted.proceeds")

            sell_adjusted.proceeds = sell_adjusted.proceeds * (long_term.quantity / sell.quantity)

            if sell.t_type in self.NO_GAIN_NO_LOSS_TYPES:
                tax_event = TaxEventNoGainNoLoss(
                    DisposalType.LONG_TERM,
                    sell_adjusted,
                    long_term.cost.quantize(PRECISION) + long_term.fee_value.quantize(PRECISION),
                    Decimal(0),
                    long_term.dates,
                )
            else:
                tax_event = TaxEventCapitalGains(
                    DisposalType.LONG_TERM,
                    sell_adjusted,
                    long_term.cost.quantize(PRECISION) + long_term.fee_value.quantize(PRECISION),
                    Decimal(0),
                    long_term.dates,
                )
            self.tax_events[self._which_tax_year(tax_event.date)].append(tax_event)

            if config.debug:
                print(f"{Fore.CYAN}fifo: {tax_event}")

        if sell.t_type in (TrType.SWAP, TrType.CRYPTO_CRYPTO):
            # Cost basis copied to "Buy" asset
            if sell.t_record and sell.t_record.buy:
                sell.t_record.buy.cost = short_term.cost + long_term.cost
                if short_term.fee_value + long_term.fee_value:
                    sell.t_record.buy.fee_value = short_term.fee_value + long_term.fee_value
            else:
                raise RuntimeError("Missing t_record.buy for SWAP/CRYPTO_CRYPTO")

    def process_holdings(self) -> None:
        if config.debug:
            print(f"{Fore.CYAN}process holdings")

        for t in tqdm(
            sorted(self._all_transactions()),
            unit="t",
            desc=f"{Fore.CYAN}process holdings{Fore.GREEN}",
            disable=bool(config.debug or not sys.stdout.isatty()),
        ):
            if t.is_crypto() and t.asset not in self.holdings:
                self.holdings[t.asset] = Holdings(t.asset)

            if t.matched:
                if config.debug:
                    print(f"{Fore.BLUE}holdings: //{t} <- matched")
                continue

            if not config.transfers_include and t.t_type in TRANSFER_TYPES:
                if config.debug:
                    print(f"{Fore.BLUE}holdings: //{t} <- transfer")
                continue

            if not t.is_crypto():
                if config.debug:
                    print(f"{Fore.BLUE}holdings: //{t} <- fiat")
                continue

            if config.debug:
                print(f"{Fore.GREEN}holdings: {t}")

            if isinstance(t, Buy):
                self._add_tokens(t)
            elif isinstance(t, Sell):
                self._subtract_tokens(t)

    def _add_tokens(self, t: Buy) -> None:
        if not t.acquisition:
            cost = fees = Decimal(0)
        else:
            if t.cost is None:
                raise RuntimeError("Missing cost")

            cost = t.cost
            fees = t.fee_value or Decimal(0)

        self.holdings[t.asset].add_tokens(t.quantity, cost, fees, t.t_type is TrType.DEPOSIT)

    def _subtract_tokens(self, t: Sell) -> None:
        if not t.disposal:
            self.holdings[t.asset].subtract_tokens(
                t.quantity, Decimal(0), Decimal(0), t.t_type is TrType.WITHDRAWAL
            )
        else:
            raise RuntimeError("Unmatched disposal in holdings")

    def process_income(self) -> None:
        if config.debug:
            print(f"{Fore.CYAN}process income")

        for t in tqdm(
            self.transactions,
            unit="t",
            desc=f"{Fore.CYAN}process income{Fore.GREEN}",
            disable=bool(config.debug or not sys.stdout.isatty()),
        ):
            if t.t_type in self.INCOME_TYPES and (t.is_crypto() or config.fiat_income):
                tax_event = TaxEventIncome(t)
                self.tax_events[self._which_tax_year(tax_event.date)].append(tax_event)

    def _all_transactions(self) -> Iterator[Union[Buy, Sell]]:
        return itertools.chain(
            *self.buys_ordered.values(), self.sells_ordered, self.other_transactions
        )

    def process_margin_trades(self) -> None:
        if config.debug:
            print(f"{Fore.CYAN}process margin trades")

        for t in tqdm(
            self.transactions,
            unit="t",
            desc=f"{Fore.CYAN}process margin trades{Fore.GREEN}",
            disable=bool(config.debug or not sys.stdout.isatty()),
        ):

            if t.t_type in self.MARGIN_TYPES:
                tax_event = TaxEventMarginTrade(t)
                self.tax_events[self._which_tax_year(tax_event.date)].append(tax_event)

    def calculate_capital_gains(self, tax_year: Year) -> "CalculateCapitalGains":
        calc_cgt = CalculateCapitalGains(tax_year)

        if tax_year in self.tax_events:
            for te in sorted(self.tax_events[tax_year]):
                if isinstance(te, TaxEventCapitalGains):
                    calc_cgt.tax_summary(te)
                elif isinstance(te, TaxEventNoGainNoLoss):
                    calc_cgt.non_tax_summary(te)

        if self.tax_rules in TAX_RULES_UK_COMPANY:
            calc_cgt.tax_estimate_ct(tax_year)
        else:
            calc_cgt.tax_estimate_cgt(tax_year)

        return calc_cgt

    def calculate_income(self, tax_year: Year) -> "CalculateIncome":
        calc_income = CalculateIncome()

        if tax_year in self.tax_events:
            for te in sorted(self.tax_events[tax_year]):
                if isinstance(te, TaxEventIncome):
                    calc_income.totalise(te)

        calc_income.totals_by_type()
        return calc_income

    def calculate_margin_trading(self, tax_year: Year) -> "CalculateMarginTrading":
        calc_margin_trading = CalculateMarginTrading()

        if tax_year in self.tax_events:
            for te in sorted(self.tax_events[tax_year]):
                if isinstance(te, TaxEventMarginTrade):
                    calc_margin_trading.totalise(te)

        calc_margin_trading.totals_by_contract()
        return calc_margin_trading

    def calculate_holdings(self, value_asset: ValueAsset) -> None:
        holdings: Dict[AssetSymbol, HoldingsReportAsset] = {}
        totals: HoldingsReportTotal = {"cost": Decimal(0), "value": Decimal(0), "gain": Decimal(0)}

        if config.debug:
            print(f"{Fore.CYAN}calculating holdings")

        for h in tqdm(
            self.holdings,
            unit="h",
            desc=f"{Fore.CYAN}calculating holdings{Fore.GREEN}",
            disable=bool(config.debug or not sys.stdout.isatty()),
        ):
            if self.holdings[h].quantity > 0 or config.show_empty_wallets:
                try:
                    value, name, _ = value_asset.get_current_value(
                        self.holdings[h].asset, self.holdings[h].quantity
                    )
                except requests.exceptions.HTTPError as e:
                    tqdm.write(
                        f"{WARNING} Skipping valuation of {self.holdings[h].asset} "
                        f"due to API failure ({e.response.status_code})"
                    )
                    value = None
                    name = AssetName("")

                value = value.quantize(PRECISION) if value is not None else None
                cost = (self.holdings[h].cost + self.holdings[h].fees).quantize(PRECISION)

                if value is not None:
                    holdings[h] = {
                        "name": name,
                        "quantity": self.holdings[h].quantity,
                        "cost": cost,
                        "value": value,
                        "gain": value - cost,
                    }

                    totals["value"] += value
                    totals["gain"] += value - cost
                else:
                    holdings[h] = {
                        "name": name,
                        "quantity": self.holdings[h].quantity,
                        "cost": cost,
                        "value": None,
                    }

                totals["cost"] += holdings[h]["cost"]

        self.holdings_report = {"holdings": holdings, "totals": totals}

    def _which_tax_year(self, date: Date) -> Year:
        if date > config.get_tax_year_end(date.year):
            tax_year = Year(date.year + 1)
        else:
            tax_year = Year(date.year)

        if tax_year not in self.tax_events:
            self.tax_events[tax_year] = []

        return tax_year


class CalculateCapitalGains:
    # Rate changes start from 6th April in previous year, i.e. 2022 is for tax year 2021/22
    CG_DATA_INDIVIDUAL: Dict[Year, CapitalGainsIndividual] = {
        Year(2009): {
            "allowance": Decimal(9600),
            "basic_rate": Decimal(18),
            "higher_rate": Decimal(18),
        },
        Year(2010): {
            "allowance": Decimal(10100),
            "basic_rate": Decimal(18),
            "higher_rate": Decimal(18),
        },
        Year(2011): {
            "allowance": Decimal(10100),
            "basic_rate": Decimal(18),
            "higher_rate": Decimal(28),
        },
        Year(2012): {
            "allowance": Decimal(10600),
            "basic_rate": Decimal(18),
            "higher_rate": Decimal(28),
        },
        Year(2013): {
            "allowance": Decimal(10600),
            "basic_rate": Decimal(18),
            "higher_rate": Decimal(28),
        },
        Year(2014): {
            "allowance": Decimal(10900),
            "basic_rate": Decimal(18),
            "higher_rate": Decimal(28),
        },
        Year(2015): {
            "allowance": Decimal(11000),
            "basic_rate": Decimal(18),
            "higher_rate": Decimal(28),
        },
        Year(2016): {
            "allowance": Decimal(11100),
            "basic_rate": Decimal(18),
            "higher_rate": Decimal(28),
        },
        Year(2017): {
            "allowance": Decimal(11100),
            "basic_rate": Decimal(10),
            "higher_rate": Decimal(20),
        },
        Year(2018): {
            "allowance": Decimal(11300),
            "basic_rate": Decimal(10),
            "higher_rate": Decimal(20),
        },
        Year(2019): {
            "allowance": Decimal(11700),
            "basic_rate": Decimal(10),
            "higher_rate": Decimal(20),
        },
        Year(2020): {
            "allowance": Decimal(12000),
            "basic_rate": Decimal(10),
            "higher_rate": Decimal(20),
        },
        Year(2021): {
            "allowance": Decimal(12300),
            "basic_rate": Decimal(10),
            "higher_rate": Decimal(20),
        },
        Year(2022): {
            "allowance": Decimal(12300),
            "basic_rate": Decimal(10),
            "higher_rate": Decimal(20),
        },
        Year(2023): {
            "allowance": Decimal(12300),
            "basic_rate": Decimal(10),
            "higher_rate": Decimal(20),
        },
        Year(2024): {
            "allowance": Decimal(6000),
            "basic_rate": Decimal(10),
            "higher_rate": Decimal(20),
            "proceeds_limit": Decimal(50000),
        },
        Year(2025): {
            "allowance": Decimal(3000),
            "basic_rate": Decimal(10),
            "higher_rate": Decimal(20),
            "proceeds_limit": Decimal(50000),
        },
    }

    # Rate changes start from 1st April
    CG_DATA_COMPANY: Dict[Year, ChargableGainsCompany] = {
        Year(2009): {"small_rate": Decimal(21), "main_rate": Decimal(28)},
        Year(2010): {"small_rate": Decimal(21), "main_rate": Decimal(28)},
        Year(2011): {"small_rate": Decimal(20), "main_rate": Decimal(23)},
        Year(2012): {"small_rate": Decimal(20), "main_rate": Decimal(24)},
        Year(2013): {"small_rate": Decimal(20), "main_rate": Decimal(23)},
        Year(2014): {"small_rate": Decimal(20), "main_rate": Decimal(21)},
        Year(2015): {"small_rate": None, "main_rate": Decimal(20)},
        Year(2016): {"small_rate": None, "main_rate": Decimal(20)},
        Year(2017): {"small_rate": None, "main_rate": Decimal(19)},
        Year(2018): {"small_rate": None, "main_rate": Decimal(19)},
        Year(2019): {"small_rate": None, "main_rate": Decimal(19)},
        Year(2020): {"small_rate": None, "main_rate": Decimal(19)},
        Year(2021): {"small_rate": None, "main_rate": Decimal(19)},
        Year(2022): {"small_rate": None, "main_rate": Decimal(19)},
        Year(2023): {"small_rate": Decimal(19), "main_rate": Decimal(25)},
        Year(2024): {"small_rate": Decimal(19), "main_rate": Decimal(25)},
    }

    def __init__(self, tax_year: Year) -> None:
        self.totals: CapitalGainsReportTotal = {
            "cost": Decimal(0),
            "fees": Decimal(0),
            "proceeds": Decimal(0),
            "gain": Decimal(0),
        }
        self.summary: CapitalGainsReportSummary = {
            "disposals": Decimal(0),
            "total_gain": Decimal(0),
            "total_loss": Decimal(0),
        }

        self.cgt_estimate: CapitalGainsReportEstimate = {
            "allowance": Decimal(self.CG_DATA_INDIVIDUAL[tax_year]["allowance"]),
            "cgt_basic_rate": self.CG_DATA_INDIVIDUAL[tax_year]["basic_rate"],
            "cgt_higher_rate": self.CG_DATA_INDIVIDUAL[tax_year]["higher_rate"],
            "allowance_used": Decimal(0),
            "taxable_gain": Decimal(0),
            "cgt_basic": Decimal(0),
            "cgt_higher": Decimal(0),
            "proceeds_limit": self.get_proceeds_limit(tax_year),
            "proceeds_warning": False,
        }

        self.ct_estimate: ChargableGainsReportEstimate = {
            "ct_small_rates": [],
            "ct_main_rates": [],
            "taxable_gain": Decimal(0),
            "ct_small": Decimal(0),
            "ct_main": Decimal(0),
        }

        self.short_term: Dict[AssetSymbol, List[TaxEventCapitalGains]] = {}
        self.short_term_totals: CapitalGainsReportTotal = {
            "cost": Decimal(0),
            "fees": Decimal(0),
            "proceeds": Decimal(0),
            "gain": Decimal(0),
        }
        self.long_term: Dict[AssetSymbol, List[TaxEventCapitalGains]] = {}
        self.long_term_totals: CapitalGainsReportTotal = {
            "cost": Decimal(0),
            "fees": Decimal(0),
            "proceeds": Decimal(0),
            "gain": Decimal(0),
        }
        self.non_tax_by_type: Dict[str, List[TaxEventNoGainNoLoss]] = {}
        self.non_tax_by_type_total: Dict[str, CapitalGainsReportTotal] = {}

    def get_proceeds_limit(self, tax_year: Year) -> Decimal:
        if "proceeds_limit" in self.CG_DATA_INDIVIDUAL[tax_year]:
            # For 2023 HMRC has introduced a fixed CGT reporting proceeds limit
            return Decimal(self.CG_DATA_INDIVIDUAL[tax_year]["proceeds_limit"])
        return Decimal(self.CG_DATA_INDIVIDUAL[tax_year]["allowance"]) * 4

    def get_ct_rate(self, date: Date) -> Tuple[Optional[Decimal], Decimal]:
        if date < datetime.date(date.year, 4, 1):
            # Use rate from previous year
            year = Year(date.year - 1)
            return (
                self.CG_DATA_COMPANY[year]["small_rate"],
                self.CG_DATA_COMPANY[year]["main_rate"],
            )
        year = Year(date.year)
        return (
            self.CG_DATA_COMPANY[year]["small_rate"],
            self.CG_DATA_COMPANY[year]["main_rate"],
        )

    def tax_summary(self, te: TaxEventCapitalGains) -> None:
        if te.disposal_type is DisposalType.SHORT_TERM:
            if te.asset not in self.short_term:
                self.short_term[te.asset] = []

            self.short_term[te.asset].append(te)

            self.short_term_totals["cost"] += te.cost
            self.short_term_totals["fees"] += te.fees
            self.short_term_totals["proceeds"] += te.proceeds
            self.short_term_totals["gain"] += te.gain
        elif te.disposal_type is DisposalType.LONG_TERM:
            if te.asset not in self.long_term:
                self.long_term[te.asset] = []

            self.long_term[te.asset].append(te)

            self.long_term_totals["cost"] += te.cost
            self.long_term_totals["fees"] += te.fees
            self.long_term_totals["proceeds"] += te.proceeds
            self.long_term_totals["gain"] += te.gain
        else:
            raise RuntimeError("Unexpected disposal_type")

    def non_tax_summary(self, te: TaxEventNoGainNoLoss) -> None:
        if te.t_type.value not in self.non_tax_by_type:
            self.non_tax_by_type[te.t_type.value] = []

        self.non_tax_by_type[te.t_type.value].append(te)

        if te.t_type.value not in self.non_tax_by_type_total:
            self.non_tax_by_type_total[te.t_type.value] = {
                "cost": te.cost,
                "fees": te.fees,
                "proceeds": te.market_value,
                "gain": Decimal(),
            }
        else:
            self.non_tax_by_type_total[te.t_type.value]["cost"] += te.cost
            self.non_tax_by_type_total[te.t_type.value]["fees"] += te.fees
            self.non_tax_by_type_total[te.t_type.value]["proceeds"] += te.market_value

    def tax_estimate_cgt(self, tax_year: Year) -> None:
        if self.totals["gain"] > self.cgt_estimate["allowance"]:
            self.cgt_estimate["allowance_used"] = self.cgt_estimate["allowance"]
            self.cgt_estimate["taxable_gain"] = self.totals["gain"] - self.cgt_estimate["allowance"]
            self.cgt_estimate["cgt_basic"] = (
                self.cgt_estimate["taxable_gain"]
                * self.CG_DATA_INDIVIDUAL[tax_year]["basic_rate"]
                / 100
            )
            self.cgt_estimate["cgt_higher"] = (
                self.cgt_estimate["taxable_gain"]
                * self.CG_DATA_INDIVIDUAL[tax_year]["higher_rate"]
                / 100
            )
        elif self.totals["gain"] > 0:
            self.cgt_estimate["allowance_used"] = self.totals["gain"]

        if self.totals["proceeds"] >= self.cgt_estimate["proceeds_limit"]:
            self.cgt_estimate["proceeds_warning"] = True

    def tax_estimate_ct(self, tax_year: Year) -> None:
        if self.totals["gain"] > 0:
            self.ct_estimate["taxable_gain"] = self.totals["gain"]

        start_date = config.get_tax_year_start(tax_year)
        end_date = config.get_tax_year_end(tax_year)
        day_count = (end_date - start_date).days + 1

        for date in (start_date + datetime.timedelta(n) for n in range(day_count)):
            small_rate, main_rate = self.get_ct_rate(Date(date))

            if small_rate not in self.ct_estimate["ct_small_rates"]:
                self.ct_estimate["ct_small_rates"].append(small_rate)

            if main_rate not in self.ct_estimate["ct_main_rates"]:
                self.ct_estimate["ct_main_rates"].append(main_rate)

            if self.ct_estimate["taxable_gain"] > 0:
                if small_rate is None:
                    # Use main rate if there isn't a small rate
                    self.ct_estimate["ct_small"] += (
                        self.ct_estimate["taxable_gain"] / day_count * main_rate / 100
                    )
                else:
                    self.ct_estimate["ct_small"] += (
                        self.ct_estimate["taxable_gain"] / day_count * small_rate / 100
                    )

                self.ct_estimate["ct_main"] += (
                    self.ct_estimate["taxable_gain"] / day_count * main_rate / 100
                )

        if self.ct_estimate["ct_small_rates"] == [None]:
            # No small rate so remove estimate
            self.ct_estimate.pop("ct_small")
            self.ct_estimate["ct_small_rates"] = []


class CalculateIncome:
    def __init__(self) -> None:
        self.totals: IncomeReportTotal = {"amount": Decimal(0), "fees": Decimal(0)}
        self.assets: Dict[AssetSymbol, List[TaxEventIncome]] = {}
        self.types: Dict[str, List[TaxEventIncome]] = {}
        self.type_totals: Dict[str, IncomeReportTotal] = {}

    def totalise(self, te: TaxEventIncome) -> None:
        self.totals["amount"] += te.amount
        self.totals["fees"] += te.fees

        if te.asset not in self.assets:
            self.assets[te.asset] = []

        self.assets[te.asset].append(te)

        if te.type.value not in self.types:
            self.types[te.type.value] = []

        self.types[te.type.value].append(te)

    def totals_by_type(self) -> None:
        for income_type, te_list in self.types.items():
            for te in te_list:
                if income_type not in self.type_totals:
                    self.type_totals[income_type] = {"amount": te.amount, "fees": te.fees}
                else:
                    self.type_totals[income_type]["amount"] += te.amount
                    self.type_totals[income_type]["fees"] += te.fees


class CalculateMarginTrading:
    def __init__(self) -> None:
        self.totals: MarginReportTotal = {
            "gains": Decimal(0),
            "losses": Decimal(0),
            "fees": Decimal(0),
        }
        self.contracts: Dict[Tuple[Wallet, Note], List[TaxEventMarginTrade]] = {}
        self.contract_totals: Dict[Tuple[Wallet, Note], MarginReportTotal] = {}

    def totalise(self, te: TaxEventMarginTrade) -> None:
        self.totals["gains"] += te.gain
        self.totals["losses"] += te.loss
        self.totals["fees"] += te.fee

        if (te.wallet, te.note) not in self.contracts:
            self.contracts[(te.wallet, te.note)] = []

        self.contracts[(te.wallet, te.note)].append(te)

    def totals_by_contract(self) -> None:
        for (wallet, note), te_list in self.contracts.items():
            for te in te_list:
                if (wallet, note) not in self.contract_totals:
                    self.contract_totals[(wallet, note)] = {
                        "gains": te.gain,
                        "losses": te.loss,
                        "fees": te.fee,
                    }
                else:
                    self.contract_totals[(wallet, note)]["gains"] += te.gain
                    self.contract_totals[(wallet, note)]["losses"] += te.loss
                    self.contract_totals[(wallet, note)]["fees"] += te.fee

                if config.debug:
                    print(f"{Fore.GREEN}margin: {te.t}")
                    print(f"{Fore.YELLOW}margin:   {self.totals_str(wallet, note)}")

    def totals_str(self, wallet: Wallet, note: Note) -> str:
        return (
            f'{wallet} {note}: gains={config.sym()}{self.contract_totals[(wallet, note)]["gains"]} '
            f'losses={config.sym()}{self.contract_totals[(wallet, note)]["losses"]} '
            f'fess={config.sym()}{self.contract_totals[(wallet, note)]["fees"]} '
        )
