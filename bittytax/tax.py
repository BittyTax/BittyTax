# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
import copy
from decimal import Decimal
from datetime import datetime, timedelta

from colorama import Fore
from tqdm import tqdm

from .config import config
from .transactions import Buy, Sell
from .holdings import Holdings

PRECISION = Decimal('0.00')

class TaxCalculator(object):
    DISPOSAL_SAME_DAY = 'Same Day'
    DISPOSAL_TEN_DAY = 'Ten Day'
    DISPOSAL_BED_AND_BREAKFAST = 'Bed & Breakfast'
    DISPOSAL_SECTION_104 = 'Section 104'
    DISPOSAL_NO_GAIN_NO_LOSS = 'No Gain/No Loss'

    TRANSFER_TYPES = (Buy.TYPE_DEPOSIT, Sell.TYPE_WITHDRAWAL)

    INCOME_TYPES = (Buy.TYPE_MINING, Buy.TYPE_STAKING, Buy.TYPE_DIVIDEND, Buy.TYPE_INTEREST,
                    Buy.TYPE_INCOME)

    NO_GAIN_NO_LOSS_TYPES = (Sell.TYPE_GIFT_SPOUSE, Sell.TYPE_CHARITY_SENT)

    # These transactions are except from the "same day" & "bnb" rule
    NO_MATCH_TYPES = (Sell.TYPE_GIFT_SPOUSE, Sell.TYPE_CHARITY_SENT, Sell.TYPE_LOST)

    def __init__(self, transactions, tax_rules):
        self.transactions = transactions
        self.tax_rules = tax_rules
        self.buys_ordered = []
        self.sells_ordered = []
        self.other_transactions = []

        self.tax_events = {}
        self.holdings = {}

        self.tax_report = {}
        self.holdings_report = {}

    def pool_same_day(self):
        transactions = copy.deepcopy(self.transactions)
        buy_transactions = {}
        sell_transactions = {}

        if config.debug:
            print("%spool same day transactions" % Fore.CYAN)

        for t in tqdm(transactions,
                      unit='t',
                      desc="%spool same day%s" % (Fore.CYAN, Fore.GREEN),
                      disable=bool(config.debug or not sys.stdout.isatty())):
            if isinstance(t, Buy) and t.is_crypto() and t.acquisition and \
                    t.t_type not in self.NO_MATCH_TYPES:
                if (t.asset, t.timestamp.date()) not in buy_transactions:
                    buy_transactions[(t.asset, t.timestamp.date())] = t
                else:
                    buy_transactions[(t.asset, t.timestamp.date())] += t
            elif isinstance(t, Sell) and t.is_crypto() and t.disposal and \
                    t.t_type not in self.NO_MATCH_TYPES:
                if (t.asset, t.timestamp.date()) not in sell_transactions:
                    sell_transactions[(t.asset, t.timestamp.date())] = t
                else:
                    sell_transactions[(t.asset, t.timestamp.date())] += t
            else:
                self.other_transactions.append(t)

        self.buys_ordered = sorted(buy_transactions.values())
        self.sells_ordered = sorted(sell_transactions.values())

        if config.debug:
            for t in sorted(self.all_transactions()):
                if len(t.pooled) > 1:
                    print("%spool: %s" % (Fore.GREEN, t.__str__(pooled_bold=True)))
                    for tp in t.pooled:
                        print("%spool:   (%s)" % (Fore.BLUE, tp))

        if config.debug:
            print("%spool: total transactions=%d" % (Fore.CYAN, len(self.all_transactions())))

    def match_buyback(self, rule):
        sell_index = buy_index = 0

        if not self.buys_ordered:
            return

        if config.debug:
            print("%smatch %s transactions" % (Fore.CYAN, rule.lower()))

        pbar = tqdm(total=len(self.sells_ordered),
                    unit='t',
                    desc="%smatch %s transactions%s" % (Fore.CYAN, rule.lower(), Fore.GREEN),
                    disable=bool(config.debug or not sys.stdout.isatty()))

        while sell_index < len(self.sells_ordered):
            s = self.sells_ordered[sell_index]
            b = self.buys_ordered[buy_index]

            if (not s.matched and not b.matched and s.asset == b.asset and
                    self._rule_match(b.timestamp, s.timestamp, rule)):
                if config.debug:
                    if b.quantity > s.quantity:
                        print("%smatch: %s" % (Fore.GREEN, s.__str__(quantity_bold=True)))
                        print("%smatch: %s" % (Fore.GREEN, b))
                    elif s.quantity > b.quantity:
                        print("%smatch: %s" % (Fore.GREEN, s))
                        print("%smatch: %s" % (Fore.GREEN, b.__str__(quantity_bold=True)))
                    else:
                        print("%smatch: %s" % (Fore.GREEN, s.__str__(quantity_bold=True)))
                        print("%smatch: %s" % (Fore.GREEN, b.__str__(quantity_bold=True)))

                if b.quantity > s.quantity:
                    b_remainder = b.split_buy(s.quantity)
                    self.buys_ordered.insert(buy_index + 1, b_remainder)
                    if config.debug:
                        print("%smatch:   split: %s" % (Fore.YELLOW, b.__str__(quantity_bold=True)))
                        print("%smatch:   split: %s" % (Fore.YELLOW, b_remainder))
                elif s.quantity > b.quantity:
                    s_remainder = s.split_sell(b.quantity)
                    self.sells_ordered.insert(sell_index + 1, s_remainder)
                    if config.debug:
                        print("%smatch:   split: %s" % (Fore.YELLOW, s.__str__(quantity_bold=True)))
                        print("%smatch:   split: %s" % (Fore.YELLOW, s_remainder))
                    pbar.total += 1

                s.matched = b.matched = True
                tax_event = TaxEventCapitalGains(rule, b, s, b.cost,
                                                 (b.fee_value or Decimal(0)) +
                                                 (s.fee_value or Decimal(0)))
                self.tax_events[self.which_tax_year(tax_event.date)].append(tax_event)
                if config.debug:
                    print("%smatch:   %s" % (Fore.CYAN, tax_event))

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
            print("%smatch: total transactions=%d" % (Fore.CYAN, len(self.all_transactions())))

    def match_sell(self, rule):
        buy_index = sell_index = 0

        if not self.sells_ordered:
            return

        if config.debug:
            print("%smatch %s transactions" % (Fore.CYAN, rule.lower()))

        pbar = tqdm(total=len(self.buys_ordered),
                    unit='t',
                    desc="%smatch %s transactions%s" % (Fore.CYAN, rule.lower(), Fore.GREEN),
                    disable=bool(config.debug or not sys.stdout.isatty()))

        while buy_index < len(self.buys_ordered):
            b = self.buys_ordered[buy_index]
            s = self.sells_ordered[sell_index]

            if (not b.matched and not s.matched and b.asset == s.asset and
                    self._rule_match(b.timestamp, s.timestamp, rule)):
                if config.debug:
                    if b.quantity > s.quantity:
                        print("%smatch: %s" % (Fore.GREEN, b))
                        print("%smatch: %s" % (Fore.GREEN, s.__str__(quantity_bold=True)))
                    elif s.quantity > b.quantity:
                        print("%smatch: %s" % (Fore.GREEN, b.__str__(quantity_bold=True)))
                        print("%smatch: %s" % (Fore.GREEN, s))
                    else:
                        print("%smatch: %s" % (Fore.GREEN, b.__str__(quantity_bold=True)))
                        print("%smatch: %s" % (Fore.GREEN, s.__str__(quantity_bold=True)))

                if b.quantity > s.quantity:
                    b_remainder = b.split_buy(s.quantity)
                    self.buys_ordered.insert(buy_index + 1, b_remainder)
                    if config.debug:
                        print("%smatch:   split: %s" % (Fore.YELLOW, b.__str__(quantity_bold=True)))
                        print("%smatch:   split: %s" % (Fore.YELLOW, b_remainder))
                    pbar.total += 1
                elif s.quantity > b.quantity:
                    s_remainder = s.split_sell(b.quantity)
                    self.sells_ordered.insert(sell_index + 1, s_remainder)
                    if config.debug:
                        print("%smatch:   split: %s" % (Fore.YELLOW, s.__str__(quantity_bold=True)))
                        print("%smatch:   split: %s" % (Fore.YELLOW, s_remainder))

                b.matched = s.matched = True
                tax_event = TaxEventCapitalGains(rule, b, s, b.cost,
                                                 (b.fee_value or Decimal(0)) +
                                                 (s.fee_value or Decimal(0)))
                self.tax_events[self.which_tax_year(tax_event.date)].append(tax_event)
                if config.debug:
                    print("%smatch:   %s" % (Fore.CYAN, tax_event))

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
            print("%smatch: total transactions=%d" % (Fore.CYAN, len(self.all_transactions())))

    def _rule_match(self, b_timestamp, s_timestamp, rule):
        if rule == self.DISPOSAL_SAME_DAY:
            return b_timestamp.date() == s_timestamp.date()
        if rule == self.DISPOSAL_TEN_DAY:
            # 10 days between buy and sell
            return (b_timestamp.date() < s_timestamp.date() and
                    s_timestamp.date() <= b_timestamp.date() + timedelta(days=10))
        if rule == self.DISPOSAL_BED_AND_BREAKFAST:
            # 30 days between sell and buy-back
            return (s_timestamp.date() < b_timestamp.date() and
                    b_timestamp.date() <= s_timestamp.date() + timedelta(days=30))
        if not rule:
            return True

        raise Exception

    def process_section104(self, skip_integrity_check):
        if config.debug:
            print("%sprocess section 104" % Fore.CYAN)

        for t in tqdm(sorted(self.all_transactions()),
                      unit='t',
                      desc="%sprocess section 104%s" % (Fore.CYAN, Fore.GREEN),
                      disable=bool(config.debug or not sys.stdout.isatty())):
            if t.is_crypto() and t.asset not in self.holdings:
                self.holdings[t.asset] = Holdings(t.asset)

            if t.matched:
                if config.debug:
                    print("%ssection104: //%s <- matched" % (Fore.BLUE, t))
                continue

            if not config.transfers_include and t.t_type in self.TRANSFER_TYPES:
                if config.debug:
                    print("%ssection104: //%s <- transfer" % (Fore.BLUE, t))
                continue

            if config.debug:
                print("%ssection104: %s" % (Fore.GREEN, t))

            if isinstance(t, Buy) and t.is_crypto():
                self._add_tokens(t)
            elif isinstance(t, Sell) and t.is_crypto():
                self._subtract_tokens(t, skip_integrity_check)

    def _add_tokens(self, t):
        if not t.acquisition:
            cost = fees = Decimal(0)
        else:
            cost = t.cost
            fees = t.fee_value or Decimal(0)

        self.holdings[t.asset].add_tokens(t.quantity, cost, fees,
                                          t.t_type == Buy.TYPE_DEPOSIT)

    def _subtract_tokens(self, t, skip_integrity_check):
        if not t.disposal:
            cost = fees = Decimal(0)
        else:
            if self.holdings[t.asset].quantity:
                cost = self.holdings[t.asset].cost * (t.quantity /
                                                      self.holdings[t.asset].quantity)
                fees = self.holdings[t.asset].fees * (t.quantity /
                                                      self.holdings[t.asset].quantity)
            else:
                # Should never happen, only if incorrect transaction records
                cost = fees = Decimal(0)

        self.holdings[t.asset].subtract_tokens(t.quantity, cost, fees,
                                               t.t_type == Sell.TYPE_WITHDRAWAL)

        if t.disposal:
            if t.t_type in self.NO_GAIN_NO_LOSS_TYPES:
                # Change proceeds to make sure it balances
                t.proceeds = cost.quantize(PRECISION) + (fees + (t.fee_value or
                                                                 Decimal(0))).quantize(PRECISION)
                t.proceeds_fixed = True
                tax_event = TaxEventCapitalGains(self.DISPOSAL_NO_GAIN_NO_LOSS,
                                                 None, t, cost, fees + (t.fee_value or Decimal(0)))
            else:
                tax_event = TaxEventCapitalGains(self.DISPOSAL_SECTION_104,
                                                 None, t, cost, fees + (t.fee_value or Decimal(0)))

            self.tax_events[self.which_tax_year(tax_event.date)].append(tax_event)
            if config.debug:
                print("%ssection104:   %s" % (Fore.CYAN, tax_event))

            if config.transfers_include and not skip_integrity_check:
                self.holdings[t.asset].check_transfer_mismatch()

    def process_income(self):
        if config.debug:
            print("%sprocess income" % Fore.CYAN)

        for t in tqdm(self.transactions,
                      unit='t',
                      desc="%sprocess income%s" % (Fore.CYAN, Fore.GREEN),
                      disable=bool(config.debug or not sys.stdout.isatty())):
            if t.t_type in self.INCOME_TYPES and (t.is_crypto() or config.fiat_income):
                tax_event = TaxEventIncome(t)
                self.tax_events[self.which_tax_year(tax_event.date)].append(tax_event)

    def all_transactions(self):
        if not config.transfers_include:
            # Ordered so transfers appear before the fee spend in the log
            return self.other_transactions + self.buys_ordered + self.sells_ordered
        return self.buys_ordered + self.sells_ordered + self.other_transactions

    def calculate_capital_gains(self, tax_year):
        self.tax_report[tax_year] = {}
        self.tax_report[tax_year]['CapitalGains'] = CalculateCapitalGains(tax_year, self.tax_rules)

        if tax_year in self.tax_events:
            for te in sorted(self.tax_events[tax_year]):
                if isinstance(te, TaxEventCapitalGains):
                    self.tax_report[tax_year]['CapitalGains'].tax_summary(te)

        if self.tax_rules in config.TAX_RULES_UK_COMPANY:
            self.tax_report[tax_year]['CapitalGains'].tax_estimate_ct(tax_year)
        else:
            self.tax_report[tax_year]['CapitalGains'].tax_estimate_cgt(tax_year)

    def calculate_income(self, tax_year):
        self.tax_report[tax_year]['Income'] = CalculateIncome()

        if tax_year in self.tax_events:
            for te in sorted(self.tax_events[tax_year]):
                if isinstance(te, TaxEventIncome):
                    self.tax_report[tax_year]['Income'].totalise(te)

        self.tax_report[tax_year]['Income'].totals_by_type()

    def calculate_holdings(self, value_asset):
        holdings = {}
        totals = {'cost': Decimal(0),
                  'value': Decimal(0),
                  'gain': Decimal(0)}

        if config.debug:
            print("%scalculating holdings" % Fore.CYAN)

        for h in tqdm(self.holdings,
                      unit='h',
                      desc="%scalculating holdings%s" % (Fore.CYAN, Fore.GREEN),
                      disable=bool(config.debug or not sys.stdout.isatty())):
            if self.holdings[h].quantity > 0 or config.show_empty_wallets:
                holdings[h] = {}
                holdings[h]['asset'] = self.holdings[h].asset
                holdings[h]['quantity'] = self.holdings[h].quantity
                holdings[h]['cost'] = (self.holdings[h].cost +
                                       self.holdings[h].fees).quantize(PRECISION)

                value, name, data_source = value_asset.get_current_value(self.holdings[h].asset,
                                                                         self.holdings[h].quantity)
                holdings[h]['value'] = value.quantize(PRECISION) if value is not None else None
                holdings[h]['name'] = name
                holdings[h]['data_source'] = data_source

                if holdings[h]['value'] is not None:
                    holdings[h]['gain'] = holdings[h]['value'] - holdings[h]['cost']
                    totals['value'] += holdings[h]['value']
                    totals['gain'] += holdings[h]['gain']

                totals['cost'] += holdings[h]['cost']

        self.holdings_report['holdings'] = holdings
        self.holdings_report['totals'] = totals

    def which_tax_year(self, timestamp):
        if timestamp > config.get_tax_year_end(timestamp.year):
            tax_year = timestamp.year + 1
        else:
            tax_year = timestamp.year

        if tax_year not in self.tax_events:
            self.tax_events[tax_year] = []

        return tax_year

class TaxEvent(object):
    def __init__(self, date, asset):
        self.date = date
        self.asset = asset

    def __eq__(self, other):
        return self.date == other.date

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return self.date < other.date

class TaxEventCapitalGains(TaxEvent):
    def __init__(self, disposal_type, b, s, cost, fees):
        super(TaxEventCapitalGains, self).__init__(s.timestamp, s.asset)
        self.disposal_type = disposal_type
        self.quantity = s.quantity
        self.cost = cost.quantize(PRECISION)
        self.fees = fees.quantize(PRECISION)
        self.proceeds = s.proceeds.quantize(PRECISION)
        self.gain = self.proceeds - self.cost - self.fees
        self.acquisition_date = b.timestamp if b else None

    def format_disposal(self):
        if self.disposal_type in (TaxCalculator.DISPOSAL_BED_AND_BREAKFAST,
                                  TaxCalculator.DISPOSAL_TEN_DAY):
            return "%s (%s)" % (self.disposal_type, self.acquisition_date.strftime('%d/%m/%Y'))

        return self.disposal_type

    def __str__(self):
        return "Disposal(%s) gain=%s (proceeds=%s - cost=%s - fees=%s)" % (
            self.disposal_type.lower(),
            config.sym() + '{:0,.2f}'.format(self.gain),
            config.sym() + '{:0,.2f}'.format(self.proceeds),
            config.sym() + '{:0,.2f}'.format(self.cost),
            config.sym() + '{:0,.2f}'.format(self.fees))

class TaxEventIncome(TaxEvent):
    def __init__(self, b):
        super(TaxEventIncome, self).__init__(b.timestamp, b.asset)
        self.type = b.t_type
        self.quantity = b.quantity
        self.amount = b.cost.quantize(PRECISION)
        self.note = b.note
        if b.fee_value:
            self.fees = b.fee_value.quantize(PRECISION)
        else:
            self.fees = Decimal(0)

class CalculateCapitalGains(object):
    # Rate changes start from 6th April in previous year, i.e. 2022 is for tax year 2021/22
    CG_DATA_INDIVIDUAL = {2009: {'allowance': 9600, 'basic_rate': 18, 'higher_rate': 18},
                          2010: {'allowance': 10100, 'basic_rate': 18, 'higher_rate': 18},
                          2011: {'allowance': 10100, 'basic_rate': 18, 'higher_rate': 28},
                          2012: {'allowance': 10600, 'basic_rate': 18, 'higher_rate': 28},
                          2013: {'allowance': 10600, 'basic_rate': 18, 'higher_rate': 28},
                          2014: {'allowance': 10900, 'basic_rate': 18, 'higher_rate': 28},
                          2015: {'allowance': 11000, 'basic_rate': 18, 'higher_rate': 28},
                          2016: {'allowance': 11100, 'basic_rate': 18, 'higher_rate': 28},
                          2017: {'allowance': 11100, 'basic_rate': 10, 'higher_rate': 20},
                          2018: {'allowance': 11300, 'basic_rate': 10, 'higher_rate': 20},
                          2019: {'allowance': 11700, 'basic_rate': 10, 'higher_rate': 20},
                          2020: {'allowance': 12000, 'basic_rate': 10, 'higher_rate': 20},
                          2021: {'allowance': 12300, 'basic_rate': 10, 'higher_rate': 20},
                          2022: {'allowance': 12300, 'basic_rate': 10, 'higher_rate': 20},
                          2023: {'allowance': 12300, 'basic_rate': 10, 'higher_rate': 20}}

    # Rate changes start from 1st April
    CG_DATA_COMPANY = {2009: {'small_rate': 21, 'main_rate': 28},
                       2010: {'small_rate': 21, 'main_rate': 28},
                       2011: {'small_rate': 20, 'main_rate': 23},
                       2012: {'small_rate': 20, 'main_rate': 24},
                       2013: {'small_rate': 20, 'main_rate': 23},
                       2014: {'small_rate': 20, 'main_rate': 21},
                       2015: {'small_rate': None, 'main_rate': 20},
                       2016: {'small_rate': None, 'main_rate': 20},
                       2017: {'small_rate': None, 'main_rate': 19},
                       2018: {'small_rate': None, 'main_rate': 19},
                       2019: {'small_rate': None, 'main_rate': 19},
                       2020: {'small_rate': None, 'main_rate': 19},
                       2021: {'small_rate': None, 'main_rate': 19}}

    def __init__(self, tax_year, tax_rules):
        self.totals = {'cost': Decimal(0),
                       'fees': Decimal(0),
                       'proceeds': Decimal(0),
                       'gain': Decimal(0)}
        self.summary = {'disposals': Decimal(0),
                        'total_gain': Decimal(0),
                        'total_loss': Decimal(0)}

        if tax_rules in config.TAX_RULES_UK_COMPANY:
            self.estimate = {'proceeds_warning': False,
                             'ct_small_rates': [],
                             'ct_main_rates': [],
                             'taxable_gain': Decimal(0),
                             'ct_small': Decimal(0),
                             'ct_main': Decimal(0)}
        else:
            self.estimate = {'allowance': Decimal(self.CG_DATA_INDIVIDUAL[tax_year]['allowance']),
                             'cgt_basic_rate': self.CG_DATA_INDIVIDUAL[tax_year]['basic_rate'],
                             'cgt_higher_rate': self.CG_DATA_INDIVIDUAL[tax_year]['higher_rate'],
                             'allowance_used': Decimal(0),
                             'taxable_gain': Decimal(0),
                             'cgt_basic': Decimal(0),
                             'cgt_higher': Decimal(0),
                             'proceeds_warning': False}
        self.assets = {}

    def get_ct_rate(self, date):
        if date < datetime(date.year, 4, 1, tzinfo=config.TZ_LOCAL):
            # Use rate from previous year
            return self.CG_DATA_COMPANY[date.year-1]['small_rate'], \
                   self.CG_DATA_COMPANY[date.year-1]['main_rate']
        return self.CG_DATA_COMPANY[date.year]['small_rate'], \
               self.CG_DATA_COMPANY[date.year]['main_rate']

    def tax_summary(self, te):
        self.summary['disposals'] += 1
        self.totals['cost'] += te.cost
        self.totals['fees'] += te.fees
        self.totals['proceeds'] += te.proceeds
        self.totals['gain'] += te.gain
        if te.gain >= 0:
            self.summary['total_gain'] += te.gain
        else:
            self.summary['total_loss'] += te.gain

        if te.asset not in self.assets:
            self.assets[te.asset] = []

        self.assets[te.asset].append(te)

    def tax_estimate_cgt(self, tax_year):
        if self.totals['gain'] > self.estimate['allowance']:
            self.estimate['allowance_used'] = self.estimate['allowance']
            self.estimate['taxable_gain'] = self.totals['gain'] - self.estimate['allowance']
            self.estimate['cgt_basic'] = self.estimate['taxable_gain'] * \
                                         self.CG_DATA_INDIVIDUAL[tax_year]['basic_rate'] / 100
            self.estimate['cgt_higher'] = self.estimate['taxable_gain'] * \
                                          self.CG_DATA_INDIVIDUAL[tax_year]['higher_rate'] /100
        elif self.totals['gain'] > 0:
            self.estimate['allowance_used'] = self.totals['gain']

        if self.totals['proceeds'] >= self.estimate['allowance'] * 4:
            self.estimate['proceeds_warning'] = True

    def tax_estimate_ct(self, tax_year):
        if self.totals['gain'] > 0:
            self.estimate['taxable_gain'] = self.totals['gain']

        start_date = config.get_tax_year_start(tax_year)
        end_date = config.get_tax_year_end(tax_year)
        day_count = (end_date - start_date).days + 1

        for date in (start_date + timedelta(n) for n in range(day_count)):
            small_rate, main_rate = self.get_ct_rate(date)

            if small_rate not in self.estimate['ct_small_rates']:
                self.estimate['ct_small_rates'].append(small_rate)

            if main_rate not in self.estimate['ct_main_rates']:
                self.estimate['ct_main_rates'].append(main_rate)

            if self.estimate['taxable_gain'] > 0:
                if small_rate is None:
                    # Use main rate if there isn't a small rate
                    self.estimate['ct_small'] += self.estimate['taxable_gain'] / day_count * \
                                                 main_rate / 100
                else:
                    self.estimate['ct_small'] += self.estimate['taxable_gain'] / day_count * \
                                                 small_rate / 100

                self.estimate['ct_main'] += self.estimate['taxable_gain'] / day_count * \
                                            main_rate / 100

        if self.estimate['ct_small_rates'] == [None]:
            # No small rate so remove estimate
            self.estimate.pop('ct_small')
            self.estimate['ct_small_rates'] = []

class CalculateIncome(object):
    def __init__(self):
        self.totals = {'amount': Decimal(0),
                       'fees': Decimal(0)}
        self.assets = {}
        self.types = {}
        self.type_totals = {}

    def totalise(self, te):
        self.totals['amount'] += te.amount
        self.totals['fees'] += te.fees

        if te.asset not in self.assets:
            self.assets[te.asset] = []

        self.assets[te.asset].append(te)

        if te.type not in self.types:
            self.types[te.type] = []

        self.types[te.type].append(te)

    def totals_by_type(self):
        for income_type in self.types:
            for te in self.types[income_type]:
                if income_type not in self.type_totals:
                    self.type_totals[income_type] = {}
                    self.type_totals[income_type]['amount'] = te.amount
                    self.type_totals[income_type]['fees'] = te.fees
                else:
                    self.type_totals[income_type]['amount'] += te.amount
                    self.type_totals[income_type]['fees'] += te.fees
