# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import copy
from decimal import Decimal
from datetime import datetime, timedelta

from .config import config
from .transactions import Buy, Sell
from .holdings import Holdings

log = logging.getLogger()

PRECISION = Decimal('0.00')

def which_tax_year(timestamp):
    if timestamp > datetime(timestamp.year, 4, 5, tzinfo=config.TZ_LOCAL):
        tax_year = timestamp.year + 1
    else:
        tax_year = timestamp.year

    return tax_year

class TaxCalculator(object):
    DISPOSAL_SAME_DAY = 'Same Day'
    DISPOSAL_BED_AND_BREAKFAST = 'Bed & Breakfast'
    DISPOSAL_SECTION_104 = 'Section 104'

    INCOME_TYPES = (Buy.TYPE_MINING, Buy.TYPE_INCOME)

    def __init__(self, transactions):
        self.transactions = transactions
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

        log.info("==POOL SAME DAY TRANSACTIONS==")
        for t in transactions:
            if isinstance(t, Buy) and t.acquisition:
                if (t.asset, t.timestamp.date()) not in buy_transactions:
                    buy_transactions[(t.asset, t.timestamp.date())] = t
                else:
                    buy_transactions[(t.asset, t.timestamp.date())] += t
            elif isinstance(t, Sell) and t.disposal:
                if (t.asset, t.timestamp.date()) not in sell_transactions:
                    sell_transactions[(t.asset, t.timestamp.date())] = t
                else:
                    sell_transactions[(t.asset, t.timestamp.date())] += t
            else:
                self.other_transactions.append(t)

        self.buys_ordered = sorted(buy_transactions.values())
        self.sells_ordered = sorted(sell_transactions.values())

        if config.args.debug:
            for t in sorted(self.buys_ordered + self.sells_ordered + self.other_transactions):
                log.debug(t)
                if len(t.pooled) > 1:
                    for tp in t.pooled:
                        log.debug("  %s", tp)

        log.debug("Total Transactions(Pooled)=%s",
                  len(self.buys_ordered + self.sells_ordered + self.other_transactions))

    def match(self, rule):
        log.info("==MATCH %s TRANSACTIONS==", rule.upper())
        sell_index = buy_index = 0

        if not self.buys_ordered:
            return

        while sell_index < len(self.sells_ordered):
            s = self.sells_ordered[sell_index]
            b = self.buys_ordered[buy_index]

            if (not s.matched and not b.matched and s.asset == b.asset and
                    self._rule_match(s.timestamp, b.timestamp, rule)):
                if config.args.debug:
                    log.debug(s)
                    if rule == self.DISPOSAL_BED_AND_BREAKFAST:
                        log.debug("%s (%s, %s days)",
                                  b, rule, (b.timestamp.date() - s.timestamp.date()).days)
                    else:
                        log.debug("%s (%s)", b, rule)

                if b.quantity > s.quantity:
                    b_remainder = b.split_buy(s.quantity)
                    self.buys_ordered.insert(buy_index + 1, b_remainder)
                elif s.quantity > b.quantity:
                    s_remainder = s.split_sell(b.quantity)
                    self.sells_ordered.insert(sell_index + 1, s_remainder)

                s.matched = b.matched = True
                tax_event = TaxEventCapitalGains(rule, b, s, b.cost,
                                            (b.fee_value or Decimal(0)) +
                                            (s.fee_value or Decimal(0)))
                self.tax_events[self._which_tax_year(tax_event.date)].append(tax_event)

                # Find next sell
                sell_index += 1
                buy_index = 0
            else:
                buy_index += 1
                if buy_index >= len(self.buys_ordered):
                    sell_index += 1
                    buy_index = 0

    def output_transactions(self):
        log.debug("==UPDATED TRANSACTIONS==")
        for t in sorted(self.buys_ordered +
                        self.sells_ordered +
                        self.other_transactions):
            log.debug(t)

        log.debug("Total Transactions=%s",
                  len(self.sells_ordered + self.buys_ordered + self.other_transactions))

    def _rule_match(self, s_timestamp, b_timestamp, rule):
        if rule == self.DISPOSAL_SAME_DAY:
            return b_timestamp.date() == s_timestamp.date()
        elif rule == self.DISPOSAL_BED_AND_BREAKFAST:
            return (s_timestamp.date() < b_timestamp.date() and
                    b_timestamp.date() <= s_timestamp.date() + timedelta(days=30))
        else:
            raise Exception

    def process_unmatched(self):
        log.info("==PROCESS UNMATCHED TRANSACTIONS==")
        unmatched_transactions = sorted([t for t in self.buys_ordered +
                                         self.sells_ordered +
                                         self.other_transactions if t.matched is False])

        for t in unmatched_transactions:
            if config.args.debug:
                if isinstance(t, Sell) and t.disposal:
                    log.debug("%s (Disposal)", t)
                else:
                    log.debug(t)

            if isinstance(t, Buy):
                self._add_tokens(t)
            elif isinstance(t, Sell):
                self._subtract_tokens(t)

    def _add_tokens(self, t):
        if t.asset not in self.holdings:
            self.holdings[t.asset] = Holdings(t.asset)

        if not t.acquisition:
            if config.transfers_include:
                # !IMPORTANT! - Make sure no disposal event occurs between a Withdrawal and a
                #   Deposit (of the same asset) otherwise the average cost basis would be incorrect
                cost = fees = Decimal(0)
            else:
                return
        else:
            cost = t.cost
            fees = t.fee_value or Decimal(0)

        self.holdings[t.asset].add_tokens(t.quantity, cost, fees)

    def _subtract_tokens(self, t):
        if t.asset not in self.holdings:
            self.holdings[t.asset] = Holdings(t.asset)

        if not t.disposal:
            if config.transfers_include:
                cost = fees = Decimal(0)
            else:
                return
        else:
            if self.holdings[t.asset].quantity:
                cost = self.holdings[t.asset].cost * (t.quantity /
                                                      self.holdings[t.asset].quantity)
                fees = self.holdings[t.asset].fees * (t.quantity /
                                                      self.holdings[t.asset].quantity)
            else:
                # Should never happen, only if incorrect transaction records
                cost = fees = Decimal(0)

        self.holdings[t.asset].subtract_tokens(t.quantity, cost, fees)

        if t.disposal:
            tax_event = TaxEventCapitalGains(self.DISPOSAL_SECTION_104,
                                        None, t, cost, fees + (t.fee_value or Decimal(0)))
            self.tax_events[self._which_tax_year(tax_event.date)].append(tax_event)

    def process_income(self):
        log.info("==PROCESS INCOME==")
        for t in self.transactions:
            if t.t_type in self.INCOME_TYPES:
                tax_event = TaxEventIncome(t)
                self.tax_events[self._which_tax_year(tax_event.date)].append(tax_event)

    def calculate_capital_gains(self, tax_year):
        log.info("==CALCULATE CAPITAL GAINS %s/%s==", tax_year - 1, tax_year)
        self.tax_report[tax_year] = {}
        self.tax_report[tax_year]['CapitalGains'] = CalculateCapitalGains(tax_year)

        if tax_year in self.tax_events:
            for te in sorted(self.tax_events[tax_year]):
                if isinstance(te, TaxEventCapitalGains):
                    self.tax_report[tax_year]['CapitalGains'].tax_summary(te)

        self.tax_report[tax_year]['CapitalGains'].tax_estimate(tax_year)

    def calculate_income(self, tax_year):
        log.info("==CALCULATE INCOME %s/%s==", tax_year - 1, tax_year)
        self.tax_report[tax_year]['Income'] = CalculateIncome()

        if tax_year in self.tax_events:
            for te in sorted(self.tax_events[tax_year]):
                if isinstance(te, TaxEventIncome):
                    self.tax_report[tax_year]['Income'].totalise(te)

        self.tax_report[tax_year]['Income'].totals_by_type()

    def calculate_holdings(self, value_asset):
        log.info("==CALCULATE HOLDINGS==")
        holdings = {}
        totals = {'cost': Decimal(0),
                  'value': Decimal(0),
                  'gain': Decimal(0)}

        for h in self.holdings:
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
                    holdings[h]['gain'] = value - holdings[h]['cost']
                    totals['value'] += holdings[h]['value']
                    totals['gain'] += holdings[h]['gain']

                totals['cost'] += holdings[h]['cost']

        self.holdings_report['holdings'] = holdings
        self.holdings_report['totals'] = totals

    def _which_tax_year(self, timestamp):
        tax_year = which_tax_year(timestamp)
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

        log.debug(" Gain=%s%s (proceeds=%s%s - cost=%s%s - fees=%s%s)",
                  config.sym(), '{:0,.2f}'.format(self.gain),
                  config.sym(), '{:0,.2f}'.format(self.proceeds),
                  config.sym(), '{:0,.2f}'.format(self.cost),
                  config.sym(), '{:0,.2f}'.format(self.fees))

    def format_disposal(self):
        if self.disposal_type == TaxCalculator.DISPOSAL_BED_AND_BREAKFAST:
            return self.disposal_type + " (" + self.acquisition_date.strftime('%d/%m/%Y') + ")"

        return self.disposal_type

class TaxEventIncome(TaxEvent):
    def __init__(self, b):
        super(TaxEventIncome, self).__init__(b.timestamp, b.asset)
        self.type = b.t_type
        self.quantity = b.quantity
        self.amount = b.cost.quantize(PRECISION)
        if b.fee_value:
            self.fees = b.fee_value.quantize(PRECISION)
        else:
            self.fees = Decimal(0)

class CalculateCapitalGains(object):
    CG_DATA_INDIVIDUALS = {2010: {'allowance': 10100, 'basic_rate': 18, 'higher_rate': 18},
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
                           2021: {'allowance': 12300, 'basic_rate': 10, 'higher_rate': 20}}

    def __init__(self, tax_year):
        self.totals = {'cost': Decimal(0),
                       'fees': Decimal(0),
                       'proceeds': Decimal(0),
                       'gain': Decimal(0)}
        self.summary = {'disposals': Decimal(0),
                        'total_gain': Decimal(0),
                        'total_loss': Decimal(0)}
        self.estimate = {'allowance': Decimal(self.CG_DATA_INDIVIDUALS[tax_year]['allowance']),
                         'allowance_used': Decimal(0),
                         'taxable_gain': Decimal(0),
                         'cgt_basic': Decimal(0),
                         'cgt_higher': Decimal(0),
                         'proceeds_warning': False}
        self.assets = {}

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

    def tax_estimate(self, tax_year):
        if self.totals['gain'] > self.estimate['allowance']:
            self.estimate['allowance_used'] = self.estimate['allowance']
            self.estimate['taxable_gain'] = self.totals['gain'] - self.estimate['allowance']
            self.estimate['cgt_basic'] = self.estimate['taxable_gain'] * \
                                         self.CG_DATA_INDIVIDUALS[tax_year]['basic_rate'] / 100
            self.estimate['cgt_higher'] = self.estimate['taxable_gain'] * \
                                          self.CG_DATA_INDIVIDUALS[tax_year]['higher_rate'] /100
        elif self.totals['gain'] > 0:
            self.estimate['allowance_used'] = self.totals['gain']

        if self.totals['proceeds'] >= self.estimate['allowance'] * 4:
            self.estimate['proceeds_warning'] = True

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
