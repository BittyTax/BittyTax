# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019
# pylint: disable=bad-option-value, unnecessary-dunder-call

import copy
import datetime
import sys
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union

from colorama import Fore
from tqdm import tqdm
from typing_extensions import NotRequired, TypedDict

from .bt_types import AssetName, AssetSymbol, Date, DisposalType, FixedValue, TrType, Wallet, Year
from .config import config
from .constants import TAX_RULES_UK_COMPANY
from .holdings import Holdings
from .price.valueasset import ValueAsset
from .tax_event import TaxEvent, TaxEventCapitalGains, TaxEventIncome, TaxEventMarginTrade
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


class MarginReportTotal(TypedDict):  # pylint: disable=too-few-public-methods
    gains: Decimal
    losses: Decimal
    fees: Decimal


class TaxCalculator:  # pylint: disable=too-many-instance-attributes
    TRANSFER_TYPES = (TrType.DEPOSIT, TrType.WITHDRAWAL)

    INCOME_TYPES = (
        TrType.MINING,
        TrType.STAKING,
        TrType.DIVIDEND,
        TrType.INTEREST,
        TrType.INCOME,
    )

    MARGIN_TYPES = (TrType.MARGIN_GAIN, TrType.MARGIN_LOSS, TrType.MARGIN_FEE)

    NO_GAIN_NO_LOSS_TYPES = (TrType.GIFT_SPOUSE, TrType.CHARITY_SENT)

    # These transactions are except from the "same day" & "b&b" rule
    NO_MATCH_TYPES = (TrType.GIFT_SPOUSE, TrType.CHARITY_SENT, TrType.LOST)

    def __init__(self, transactions: List[Union[Buy, Sell]], tax_rules: str) -> None:
        self.transactions = transactions
        self.tax_rules = tax_rules
        self.buys_ordered: List[Buy] = []
        self.sells_ordered: List[Sell] = []
        self.other_transactions: List[Union[Buy, Sell]] = []

        self.tax_events: Dict[Year, List[TaxEvent]] = {}
        self.holdings: Dict[AssetSymbol, Holdings] = {}

        self.tax_report: Dict[Year, TaxReportRecord] = {}
        self.holdings_report: Optional[HoldingsReportRecord] = None

    def pool_same_day(self) -> None:
        transactions = copy.deepcopy(self.transactions)
        buy_transactions: Dict[Tuple[AssetSymbol, Date], Buy] = {}
        sell_transactions: Dict[Tuple[AssetSymbol, Date], Sell] = {}

        if config.debug:
            print(f"{Fore.CYAN}pool same day transactions")

        for t in tqdm(
            transactions,
            unit="t",
            desc=f"{Fore.CYAN}pool same day{Fore.GREEN}",
            disable=bool(config.debug or not sys.stdout.isatty()),
        ):
            if (
                isinstance(t, Buy)
                and t.is_crypto()
                and not t.is_nft()
                and t.acquisition
                and t.t_type not in self.NO_MATCH_TYPES
            ):
                if (t.asset, t.date()) not in buy_transactions:
                    buy_transactions[(t.asset, t.date())] = t
                else:
                    buy_transactions[(t.asset, t.date())] += t
            elif (
                isinstance(t, Sell)
                and t.is_crypto()
                and not t.is_nft()
                and t.disposal
                and t.t_type not in self.NO_MATCH_TYPES
            ):
                if (t.asset, t.date()) not in sell_transactions:
                    sell_transactions[(t.asset, t.date())] = t
                else:
                    sell_transactions[(t.asset, t.date())] += t
            else:
                self.other_transactions.append(t)

        self.buys_ordered = sorted(buy_transactions.values())
        self.sells_ordered = sorted(sell_transactions.values())

        if config.debug:
            for t in sorted(self._all_transactions()):
                if len(t.pooled) > 1:
                    print(f"{Fore.GREEN}pool: {t}")
                    for tp in t.pooled:
                        print(f"{Fore.BLUE}pool:   ({tp})")

        if config.debug:
            print(f"{Fore.CYAN}pool: total transactions={len(self._all_transactions())}")

    def match_buyback(self, rule: DisposalType) -> None:
        sell_index = buy_index = 0

        if not self.buys_ordered:
            return

        if config.debug:
            print(f"{Fore.CYAN}match {rule.value.lower()} transactions")

        pbar = tqdm(
            total=len(self.sells_ordered),
            unit="t",
            desc=f"{Fore.CYAN}match {rule.value.lower()} transactions{Fore.GREEN}",
            disable=bool(config.debug or not sys.stdout.isatty()),
        )

        while sell_index < len(self.sells_ordered):
            s = self.sells_ordered[sell_index]
            b = self.buys_ordered[buy_index]

            if b.cost is None:
                raise RuntimeError("Missing cost")

            if (
                not s.matched
                and not b.matched
                and s.asset == b.asset
                and self._rule_match(b.date(), s.date(), rule)
            ):
                if config.debug:
                    if b.quantity > s.quantity:
                        print(f"{Fore.GREEN}match: {s.format_str(quantity_bold=True)}")
                        print(f"{Fore.GREEN}match: {b}")
                    elif s.quantity > b.quantity:
                        print(f"{Fore.GREEN}match: {s}")
                        print(f"{Fore.GREEN}match: {b.format_str(quantity_bold=True)}")
                    else:
                        print(f"{Fore.GREEN}match: {s.format_str(quantity_bold=True)}")
                        print(f"{Fore.GREEN}match: {b.format_str(quantity_bold=True)}")

                if b.quantity > s.quantity:
                    b_remainder = b.split_buy(s.quantity)
                    self.buys_ordered.insert(buy_index + 1, b_remainder)
                    if config.debug:
                        print(f"{Fore.YELLOW}match:   split: {b.format_str(quantity_bold=True)}")
                        print(f"{Fore.YELLOW}match:   split: {b_remainder}")
                elif s.quantity > b.quantity:
                    s_remainder = s.split_sell(b.quantity)
                    self.sells_ordered.insert(sell_index + 1, s_remainder)
                    if config.debug:
                        print(f"{Fore.YELLOW}match:   split: {s.format_str(quantity_bold=True)}")
                        print(f"{Fore.YELLOW}match:   split: {s_remainder}")
                    pbar.total += 1

                s.matched = b.matched = True
                tax_event = TaxEventCapitalGains(
                    rule,
                    b,
                    s,
                    b.cost,
                    (b.fee_value or Decimal(0)) + (s.fee_value or Decimal(0)),
                )
                self.tax_events[self._which_tax_year(tax_event.date)].append(tax_event)
                if config.debug:
                    print(f"{Fore.CYAN}match:   {tax_event}")

                # Find next sell
                sell_index += 1
                pbar.update(1)
                buy_index = 0
            else:
                buy_index += 1
                if buy_index >= len(self.buys_ordered):
                    sell_index += 1
                    pbar.update(1)
                    buy_index = 0

        pbar.close()

        if config.debug:
            print(f"{Fore.CYAN}match: total transactions={len(self._all_transactions())}")

    def match_sell(self, rule: DisposalType) -> None:
        buy_index = sell_index = 0

        if not self.sells_ordered:
            return

        if config.debug:
            print(f"{Fore.CYAN}match {rule.value.lower()} transactions")

        pbar = tqdm(
            total=len(self.buys_ordered),
            unit="t",
            desc=f"{Fore.CYAN}match {rule.value.lower()} transactions{Fore.GREEN}",
            disable=bool(config.debug or not sys.stdout.isatty()),
        )

        while buy_index < len(self.buys_ordered):
            b = self.buys_ordered[buy_index]
            s = self.sells_ordered[sell_index]

            if b.cost is None:
                raise RuntimeError("Missing cost")

            if (
                not b.matched
                and not s.matched
                and b.asset == s.asset
                and self._rule_match(b.date(), s.date(), rule)
            ):
                if config.debug:
                    if b.quantity > s.quantity:
                        print(f"{Fore.GREEN}match: {b}")
                        print(f"{Fore.GREEN}match: {s.format_str(quantity_bold=True)}")
                    elif s.quantity > b.quantity:
                        print(f"{Fore.GREEN}match: {b.format_str(quantity_bold=True)}")
                        print(f"{Fore.GREEN}match: {s}")
                    else:
                        print(f"{Fore.GREEN}match: {b.format_str(quantity_bold=True)}")
                        print(f"{Fore.GREEN}match: {s.format_str(quantity_bold=True)}")

                if b.quantity > s.quantity:
                    b_remainder = b.split_buy(s.quantity)
                    self.buys_ordered.insert(buy_index + 1, b_remainder)
                    if config.debug:
                        print(f"{Fore.YELLOW}match:   split: {b.format_str(quantity_bold=True)}")
                        print(f"{Fore.YELLOW}match:   split: {b_remainder}")
                    pbar.total += 1
                elif s.quantity > b.quantity:
                    s_remainder = s.split_sell(b.quantity)
                    self.sells_ordered.insert(sell_index + 1, s_remainder)
                    if config.debug:
                        print(f"{Fore.YELLOW}match:   split: {s.format_str(quantity_bold=True)}")
                        print(f"{Fore.YELLOW}match:   split: {s_remainder}")

                b.matched = s.matched = True
                tax_event = TaxEventCapitalGains(
                    rule,
                    b,
                    s,
                    b.cost,
                    (b.fee_value or Decimal(0)) + (s.fee_value or Decimal(0)),
                )
                self.tax_events[self._which_tax_year(tax_event.date)].append(tax_event)
                if config.debug:
                    print(f"{Fore.CYAN}match:   {tax_event}")

                # Find next buy
                buy_index += 1
                pbar.update(1)
                sell_index = 0
            else:
                sell_index += 1
                if sell_index >= len(self.sells_ordered):
                    buy_index += 1
                    pbar.update(1)
                    sell_index = 0

        pbar.close()

        if config.debug:
            print(f"{Fore.CYAN}match: total transactions={len(self._all_transactions())}")

    def _rule_match(self, b_date: Date, s_date: Date, rule: DisposalType) -> bool:
        if rule == DisposalType.SAME_DAY:
            return b_date == s_date
        if rule == DisposalType.TEN_DAY:
            # 10 days between buy and sell
            return b_date < s_date <= b_date + datetime.timedelta(days=10)
        if rule == DisposalType.BED_AND_BREAKFAST:
            # 30 days between sell and buy-back
            return s_date < b_date <= s_date + datetime.timedelta(days=30)

        raise RuntimeError("Unexpected rule")

    def process_section104(self, skip_integrity_check: bool) -> None:
        if config.debug:
            print(f"{Fore.CYAN}process section 104")

        for t in tqdm(
            sorted(self._all_transactions()),
            unit="t",
            desc=f"{Fore.CYAN}process section 104{Fore.GREEN}",
            disable=bool(config.debug or not sys.stdout.isatty()),
        ):
            if t.is_crypto() and t.asset not in self.holdings:
                self.holdings[t.asset] = Holdings(t.asset)

            if t.matched:
                if config.debug:
                    print(f"{Fore.BLUE}section104: //{t} <- matched")
                continue

            if not config.transfers_include and t.t_type in self.TRANSFER_TYPES:
                if config.debug:
                    print(f"{Fore.BLUE}section104: //{t} <- transfer")
                continue

            if not t.is_crypto():
                if config.debug:
                    print(f"{Fore.BLUE}section104: //{t} <- fiat")
                continue

            if config.debug:
                print(f"{Fore.GREEN}section104: {t}")

            if isinstance(t, Buy):
                self._add_tokens(t)
            elif isinstance(t, Sell):
                self._subtract_tokens(t, skip_integrity_check)

    def _add_tokens(self, t: Buy) -> None:
        if not t.acquisition:
            cost = fees = Decimal(0)
        else:
            if t.cost is None:
                raise RuntimeError("Missing cost")

            cost = t.cost
            fees = t.fee_value or Decimal(0)

        self.holdings[t.asset].add_tokens(t.quantity, cost, fees, t.t_type is TrType.DEPOSIT)

    def _subtract_tokens(self, t: Sell, skip_integrity_check: bool) -> None:
        if not t.disposal:
            cost = fees = Decimal(0)
        else:
            if self.holdings[t.asset].quantity:
                cost = self.holdings[t.asset].cost * (t.quantity / self.holdings[t.asset].quantity)
                fees = self.holdings[t.asset].fees * (t.quantity / self.holdings[t.asset].quantity)
            else:
                # Should never happen, only if incorrect transaction records
                cost = fees = Decimal(0)

        self.holdings[t.asset].subtract_tokens(
            t.quantity, cost, fees, t.t_type is TrType.WITHDRAWAL
        )

        if t.disposal:
            if t.t_type in self.NO_GAIN_NO_LOSS_TYPES:
                # Change proceeds to make sure it balances
                t.proceeds = cost.quantize(PRECISION) + (
                    fees + (t.fee_value or Decimal(0))
                ).quantize(PRECISION)
                t.proceeds_fixed = FixedValue(True)
                disposal_type = DisposalType.NO_GAIN_NO_LOSS
            elif t.is_nft():
                disposal_type = DisposalType.UNPOOLED
            else:
                disposal_type = DisposalType.SECTION_104

            tax_event = TaxEventCapitalGains(
                disposal_type,
                None,
                t,
                cost,
                fees + (t.fee_value or Decimal(0)),
            )

            self.tax_events[self._which_tax_year(tax_event.date)].append(tax_event)
            if config.debug:
                print(f"{Fore.CYAN}section104:   {tax_event}")

            if config.transfers_include and not skip_integrity_check:
                self.holdings[t.asset].check_transfer_mismatch()

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

    def _all_transactions(self) -> List[Union[Buy, Sell]]:
        if not config.transfers_include:
            # Ordered so transfers appear before the fee spend in the log
            return self.other_transactions + list(self.buys_ordered) + list(self.sells_ordered)
        return self.buys_ordered + self.sells_ordered + self.other_transactions

    def calculate_capital_gains(self, tax_year: Year) -> "CalculateCapitalGains":
        calc_cgt = CalculateCapitalGains(tax_year)

        if tax_year in self.tax_events:
            for te in sorted(self.tax_events[tax_year]):
                if isinstance(te, TaxEventCapitalGains):
                    calc_cgt.tax_summary(te)

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

        calc_margin_trading.totals_by_wallet()
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
                value, name, _ = value_asset.get_current_value(
                    self.holdings[h].asset, self.holdings[h].quantity
                )
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

        self.assets: Dict[AssetSymbol, List[TaxEventCapitalGains]] = {}

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
        self.summary["disposals"] += 1
        self.totals["cost"] += te.cost
        self.totals["fees"] += te.fees
        self.totals["proceeds"] += te.proceeds
        self.totals["gain"] += te.gain
        if te.gain >= 0:
            self.summary["total_gain"] += te.gain
        else:
            self.summary["total_loss"] += te.gain

        if te.asset not in self.assets:
            self.assets[te.asset] = []

        self.assets[te.asset].append(te)

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
        self.wallets: Dict[Wallet, List[TaxEventMarginTrade]] = {}
        self.wallet_totals: Dict[Wallet, MarginReportTotal] = {}

    def totalise(self, te: TaxEventMarginTrade) -> None:
        self.totals["gains"] += te.gain
        self.totals["losses"] += te.loss
        self.totals["fees"] += te.fee

        if te.wallet not in self.wallets:
            self.wallets[te.wallet] = []

        self.wallets[te.wallet].append(te)

    def totals_by_wallet(self) -> None:
        for wallet, te_list in self.wallets.items():
            for te in te_list:
                if wallet not in self.wallet_totals:
                    self.wallet_totals[wallet] = {
                        "gains": te.gain,
                        "losses": te.loss,
                        "fees": te.fee,
                    }
                else:
                    self.wallet_totals[wallet]["gains"] += te.gain
                    self.wallet_totals[wallet]["losses"] += te.loss
                    self.wallet_totals[wallet]["fees"] += te.fee

                if config.debug:
                    print(f"{Fore.GREEN}margin: {te.t}")
                    print(f"{Fore.YELLOW}margin:   {self.totals_str(wallet)}")

    def totals_str(self, wallet: Wallet) -> str:
        return (
            f'{wallet}: gains={config.sym()}{self.wallet_totals[wallet]["gains"]} '
            f'losses={config.sym()}{self.wallet_totals[wallet]["losses"]} '
            f'fess={config.sym()}{self.wallet_totals[wallet]["fees"]} '
        )
