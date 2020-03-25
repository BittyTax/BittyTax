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

class TaxCalculator(object):
    DISPOSAL_SAME_DAY = 'Same Day'
    DISPOSAL_BED_AND_BREAKFAST = 'Bed & Breakfast'
    DISPOSAL_SECTION_104 = 'Section 104'

    INCOME_TYPES = (Buy.TYPE_MINING, Buy.TYPE_INCOME)
    TRANSFER_TYPES = (Buy.TYPE_DEPOSIT, Sell.TYPE_WITHDRAWAL)

    CGT_RATE = 20
    ANNUAL_ALLOWANCE = {2010: 10100, 2011: 10100, 2012: 10600, 2013: 10600, 2014: 10900,
                        2015: 11000, 2016: 11100, 2017: 11100, 2018: 11300, 2019: 11700,
                        2020: 12000}

    def __init__(self, transactions):
        self.transactions = transactions
        self.buys_ordered = []
        self.sells_ordered = []
        self.other_transactions = []

        self.tax_events = {}
        self.holdings = {}

    def pool_same_day(self):
        transactions = copy.deepcopy(self.transactions)
        buy_transactions = {}
        sell_transactions = {}

        log.debug("==POOL SAME DAY TRANSACTIONS==")
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
        log.debug("==MATCH %s TRANSACTIONS==", rule.upper())
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
                tax_event = TaxCapitalGains(rule, b, s, b.cost,
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
        log.debug("==PROCESS UNMATCHED TRANSACTIONS==")
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
            tax_event = TaxCapitalGains(self.DISPOSAL_SECTION_104,
                                        None, t, cost, fees + (t.fee_value or Decimal(0)))
            self.tax_events[self._which_tax_year(tax_event.date)].append(tax_event)

    def process_income(self):
        for t in self.transactions:
            if t.t_type in self.INCOME_TYPES:
                tax_event = TaxIncome(t)
                self.tax_events[self._which_tax_year(tax_event.date)].append(tax_event)

    def report_capital_gains(self, tax_year):
        log.info("==TAX SUMMARY %s/%s==", tax_year - 1, tax_year)
        log.info("--CAPITAL GAINS--")
        allowance = Decimal(self.ANNUAL_ALLOWANCE[tax_year])
        disposals = total_cost = total_proceeds = total_gain = total_loss = Decimal(0)

        log.info("%s %s %s %s %s %s %s %s",
                 "Asset".ljust(7),
                 "Date".ljust(10),
                 "Disposal Type".ljust(28),
                 "Quantity".rjust(25),
                 "Cost".rjust(13),
                 "Fees".rjust(13),
                 "Proceeds".rjust(13),
                 "Gain".rjust(13))

        if tax_year in self.tax_events:
            for t in sorted(self.tax_events[tax_year]):
                if isinstance(t, TaxCapitalGains):
                    log.info(t)
                    disposals += 1
                    total_cost += t.cost + t.fees
                    total_proceeds += t.proceeds
                    if t.gain >= 0:
                        total_gain += t.gain
                    else:
                        total_loss += abs(t.gain)

        log.info("Number of disposals=%s", disposals)
        log.info("Disposal proceeds=%s%s",
                 config.sym(), '{:0,.2f}'.format(total_proceeds))
        if total_proceeds >= allowance * 4:
            log.warning("Assets sold are more than 4 times the annual allowance (%s%s), "
                        "this needs to be reported to HMRC",
                        config.sym(), '{:0,.2f}'.format(allowance * 4))
        log.info("Allowable costs=%s%s",
                 config.sym(), '{:0,.2f}'.format(total_cost))
        log.info("Gains in the year, before losses=%s%s",
                 config.sym(), '{:0,.2f}'.format(total_gain))
        log.info("Losses in the year=%s%s",
                 config.sym(), '{:0,.2f}'.format(total_loss))

        taxable_gain = Decimal(0)
        total_cg_tax = Decimal(0)
        if total_gain - total_loss > allowance:
            taxable_gain = total_gain - total_loss - allowance
            total_cg_tax = taxable_gain * self.CGT_RATE / 100

        log.info("--TAX ESTIMATE--")
        log.info("Taxable Gain=%s%s (-%s%s tax-free allowance)",
                 config.sym(), '{:0,.2f}'.format(taxable_gain),
                 config.sym(), '{:0,.2f}'.format(allowance))
        log.info("Capital Gains Tax=%s%s (%s%%)",
                 config.sym(), '{:0,.2f}'.format(total_cg_tax),
                 self.CGT_RATE)

    def report_income(self, tax_year):
        log.info("--INCOME--")

        total_income = total_fees = Decimal(0)

        log.info("%s %s %s %s %s %s",
                 "Asset".ljust(7),
                 "Date".ljust(10),
                 "Income Type".ljust(28),
                 "Quantity".rjust(25),
                 "Amount".rjust(13),
                 "Fees".rjust(13))

        if tax_year in self.tax_events:
            for t in sorted(self.tax_events[tax_year]):
                if isinstance(t, TaxIncome):
                    log.info(t)
                    total_income += t.amount
                    total_fees += t.fees

        log.info("Total income=%s%s", config.sym(), '{:0,.2f}'.format(total_income))
        log.info("Total fees=%s%s", config.sym(), '{:0,.2f}'.format(total_fees))

    def report_holdings(self, value_asset):
        log.info("==CURRENT HOLDINGS==")

        total_cost = total_value = Decimal(0)

        log.info("%s %s %s %s  %s",
                 "Asset".ljust(7),
                 "Quantity".rjust(25),
                 "Cost".rjust(13),
                 "Value".rjust(13),
                 "Data Source")

        for h in sorted(self.holdings):
            if self.holdings[h].quantity > 0 or config.show_empty_wallets:
                cost = self.holdings[h].cost + self.holdings[h].fees
                value, name, data_source = value_asset.get_current_value(self.holdings[h].asset,
                                                                         self.holdings[h].quantity)
                value = value.quantize(PRECISION)

                if data_source:
                    log.info("%s %s %s %s  %s (%s)",
                             self.holdings[h].asset.ljust(7),
                             self.holdings[h].format_quantity().rjust(25),
                             (config.sym() + '{:0,.2f}'.format(cost + 0)).rjust(13),
                             (config.sym() + '{:0,.2f}'.format(value)).rjust(13),
                             data_source,
                             name)
                else:
                    log.info("%s %s %s %s  -",
                             self.holdings[h].asset.ljust(7),
                             self.holdings[h].format_quantity().rjust(25),
                             (config.sym() + '{:0,.2f}'.format(cost + 0)).rjust(13),
                             (config.sym() + '{:0,.2f}'.format(value)).rjust(13))

                total_cost += cost
                total_value += value

        log.info("Total cost=%s%s", config.sym(), '{:0,.2f}'.format(total_cost))
        log.info("Total value=%s%s", config.sym(), '{:0,.2f}'.format(total_value))

    def _which_tax_year(self, timestamp):
        if timestamp > datetime(timestamp.year, 4, 5, tzinfo=config.TZ_LOCAL):
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
        return (self.asset, self.date) == (other.asset, other.date)

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return (self.asset, self.date) < (other.asset, other.date)

class TaxCapitalGains(TaxEvent):
    def __init__(self, disposal_type, b, s, cost, fees):
        super(TaxCapitalGains, self).__init__(s.timestamp, s.asset)
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

    @staticmethod
    def format_disposal(disposal_type, date):
        if disposal_type == TaxCalculator.DISPOSAL_BED_AND_BREAKFAST:
            return disposal_type + " (" + date.strftime('%d/%m/%Y') + ")"

        return disposal_type

    def __str__(self):
        return self.asset.ljust(7) + " " + \
               self.date.strftime('%d/%m/%Y') + " " + \
               self.format_disposal(self.disposal_type, self.acquisition_date).ljust(28) + " " + \
               '{:0,f}'.format(self.quantity.normalize()).rjust(25) + " " + \
               (config.sym() + '{:0,.2f}'.format(self.cost + 0)).rjust(13) + " " + \
               (config.sym() + '{:0,.2f}'.format(self.fees + 0)).rjust(13) + " " + \
               (config.sym() + '{:0,.2f}'.format(self.proceeds + 0)).rjust(13) + " " + \
               (config.sym() + '{:0,.2f}'.format(self.gain + 0)).rjust(13)

class TaxIncome(TaxEvent):
    def __init__(self, b):
        super(TaxIncome, self).__init__(b.timestamp, b.asset)
        self.type = b.t_type
        self.quantity = b.quantity
        self.amount = b.cost.quantize(PRECISION)
        if b.fee_value:
            self.fees = b.fee_value.quantize(PRECISION)
        else:
            self.fees = Decimal(0)

    def __str__(self):
        return self.asset.ljust(7) + " " + \
               self.date.strftime('%d/%m/%Y') + " " + \
               self.type.ljust(28) + " " + \
               '{:0,f}'.format(self.quantity.normalize()).rjust(25) + " " + \
               (config.sym() + '{:0,.2f}'.format(self.amount + 0)).rjust(13) + " " + \
               (config.sym() + '{:0,.2f}'.format(self.fees + 0)).rjust(13)
