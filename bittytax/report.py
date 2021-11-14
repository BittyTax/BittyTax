# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import os
import threading
import time
import itertools
import sys
from datetime import datetime

from colorama import Fore, Back, Style
import jinja2
from xhtml2pdf import pisa
import dateutil.parser

from .version import __version__
from .config import config

STR_PRECISION = '{:0,.5f}'

class ReportPdf(object):
    DEFAULT_FILENAME = 'BittyTax_Report'
    FILE_EXTENSION = 'pdf'
    TEMPLATE_FILE = 'tax_report.html'

    def __init__(self, progname, audit, tax_report, price_report, holdings_report, args):
        self.env = jinja2.Environment(loader=jinja2.PackageLoader('bittytax', 'templates'))
        self.filename = self.get_output_filename(args.output_filename, self.FILE_EXTENSION)

        self.env.filters['datefilter'] = self.datefilter
        self.env.filters['datefilter2'] = self.datefilter2
        self.env.filters['quantityfilter'] = self.quantityfilter
        self.env.filters['valuefilter'] = self.valuefilter
        self.env.filters['ratefilter'] = self.ratefilter
        self.env.filters['ratesfilter'] = self.ratesfilter
        self.env.filters['nowrapfilter'] = self.nowrapfilter

        template = self.env.get_template(self.TEMPLATE_FILE)
        html = template.render({'date': datetime.now(),
                                'author': '{} v{}'.format(progname, __version__),
                                'config': config,
                                'audit': audit,
                                'tax_report': tax_report,
                                'price_report': price_report,
                                'holdings_report': holdings_report,
                                'args': args})

        with ProgressSpinner():
            pdf_file = open(self.filename, 'w+b')
            status = pisa.CreatePDF(html, dest=pdf_file)
            pdf_file.close()

        if not status.err:
            print("%sPDF tax report created: %s%s" % (Fore.WHITE, Fore.YELLOW, self.filename))
        else:
            print("%sERROR%s Failed to create PDF tax report", (
                Back.RED+Fore.BLACK, Back.RESET+Fore.RED))

    @staticmethod
    def datefilter(date):
        if isinstance(date, datetime):
            return date.strftime('%d/%m/%Y')
        return dateutil.parser.parse(date).strftime('%d/%m/%Y')

    @staticmethod
    def datefilter2(date):
        return '{} {}{} {}'.format(date.strftime('%b'),
                                   date.day, ReportLog.format_day(date.day), date.strftime('%Y'))

    @staticmethod
    def quantityfilter(quantity):
        return '{:0,f}'.format(quantity.normalize())

    @staticmethod
    def valuefilter(value):
        if config.ccy == 'GBP':
            return '&pound;{:0,.2f}'.format(value)
        if config.ccy == 'EUR':
            return '&euro;{:0,.2f}'.format(value)
        if config.ccy in ('USD', 'AUD', 'NZD'):
            return '&dollar;{:0,.5f}'.format(value)
        if config.ccy in ('DKK', 'NOK', 'SEK'):
            return 'kr.{:0,.2f}'.format(value)
        raise ValueError("Currency not supported")

    @staticmethod
    def ratefilter(rate):
        if rate is None:
            return '*'
        return '{}%'.format(rate)

    @staticmethod
    def ratesfilter(rates):
        return '/'.join(map(ReportPdf.ratefilter, rates))

    @staticmethod
    def nowrapfilter(text):
        return text.replace(' ', '&nbsp;')

    @staticmethod
    def get_output_filename(filename, extension_type):
        if filename:
            filepath, file_extension = os.path.splitext(filename)
            if file_extension != extension_type:
                filepath = filepath + '.' + extension_type
        else:
            filepath = ReportPdf.DEFAULT_FILENAME + '.' + extension_type

        if not os.path.exists(filepath):
            return filepath

        filepath, file_extension = os.path.splitext(filepath)
        i = 2
        new_fname = '%s-%s%s' % (filepath, i, file_extension)
        while os.path.exists(new_fname):
            i += 1
            new_fname = '%s-%s%s' % (filepath, i, file_extension)

        return new_fname

class ReportLog(object):
    MAX_SYMBOL_LEN = 8
    MAX_NAME_LEN = 32
    ASSET_WIDTH = MAX_SYMBOL_LEN + MAX_NAME_LEN + 3

    def __init__(self, audit, tax_report, price_report, holdings_report, args):
        self.audit_report = audit
        self.tax_report = tax_report
        self.price_report = price_report
        self.holdings_report = holdings_report

        print("%stax report output:" % Fore.WHITE)
        if args.taxyear:
            if not args.summary:
                self.audit()

            print("\n%sTax Year - %s (%s to %s)%s" % (
                Fore.CYAN+Style.BRIGHT,
                config.format_tax_year(args.taxyear),
                self.format_date2(config.get_tax_year_start(args.taxyear)),
                self.format_date2(config.get_tax_year_end(args.taxyear)),
                Style.NORMAL))
            self.capital_gains(args.taxyear, args.tax_rules, args.summary)
            if not args.summary:
                self.income(args.taxyear)
                print("\n%sAppendix%s" % (Fore.CYAN+Style.BRIGHT, Style.NORMAL))
                self.price_data(args.taxyear)
        else:
            if not args.summary:
                self.audit()

            for tax_year in sorted(tax_report):
                print("\n%sTax Year - %s (%s to %s)%s" % (
                    Fore.CYAN+Style.BRIGHT,
                    config.format_tax_year(tax_year),
                    self.format_date2(config.get_tax_year_start(tax_year)),
                    self.format_date2(config.get_tax_year_end(tax_year)),
                    Style.NORMAL))
                self.capital_gains(tax_year, args.tax_rules, args.summary)
                if not args.summary:
                    self.income(tax_year)

            if not args.summary:
                print("\n%sAppendix%s" % (Fore.CYAN+Style.BRIGHT, Style.NORMAL))
                for tax_year in sorted(tax_report):
                    self.price_data(tax_year)
                    print('')
                self.holdings()

    def audit(self):
        print("\n%sAudit%s" % (Fore.CYAN+Style.BRIGHT, Style.NORMAL))
        print("%sFinal Balances" % Fore.CYAN)
        for wallet in sorted(self.audit_report.wallets, key=str.lower):
            print("\n%s%-30s %s %25s" % (
                Fore.YELLOW,
                'Wallet',
                'Asset'.ljust(self.MAX_SYMBOL_LEN),
                'Balance'))

            for asset in sorted(self.audit_report.wallets[wallet]):
                print("%s%-30s %s %25s" % (
                    Fore.WHITE,
                    wallet,
                    asset.ljust(self.MAX_SYMBOL_LEN),
                    self.format_quantity(self.audit_report.wallets[wallet][asset])))

    def capital_gains(self, tax_year, tax_rules, summary):
        cgains = self.tax_report[tax_year]['CapitalGains']

        if tax_rules in config.TAX_RULES_UK_COMPANY:
            print("%sChargeable Gains" % Fore.CYAN)
        else:
            print("%sCapital Gains" % Fore.CYAN)

        header = "%s %-10s %-28s %25s %13s %13s %13s %13s" % ('Asset'.ljust(self.MAX_SYMBOL_LEN),
                                                              'Date',
                                                              'Disposal Type',
                                                              'Quantity',
                                                              'Cost',
                                                              'Fees',
                                                              'Proceeds',
                                                              'Gain')
        for asset in sorted(cgains.assets):
            disposals = quantity = cost = fees = proceeds = gain = 0
            print('\n%s%s' % (Fore.YELLOW, header))
            for te in cgains.assets[asset]:
                disposals += 1
                quantity += te.quantity
                cost += te.cost
                fees += te.fees
                proceeds += te.proceeds
                gain += te.gain
                print("%s%s %-10s %-28s %25s %13s %13s %13s %s%13s" % (
                    Fore.WHITE,
                    te.asset.ljust(self.MAX_SYMBOL_LEN),
                    self.format_date(te.date),
                    te.format_disposal(),
                    self.format_quantity(te.quantity),
                    self.format_value(te.cost),
                    self.format_value(te.fees),
                    self.format_value(te.proceeds),
                    Fore.RED if te.gain < 0 else Fore.WHITE,
                    self.format_value(te.gain)))

            if disposals > 1:
                print("%s%s %-10s %-28s %25s %13s %13s %13s %s%13s" % (
                    Fore.YELLOW,
                    'Total'.ljust(self.MAX_SYMBOL_LEN),
                    '',
                    '',
                    self.format_quantity(quantity),
                    self.format_value(cost),
                    self.format_value(fees),
                    self.format_value(proceeds),
                    Fore.RED if gain < 0 else Fore.YELLOW,
                    self.format_value(gain)))

        print("%s%s" % (Fore.YELLOW, '_' * len(header)))
        print("%s%s %-10s %-28s %25s %13s %13s %13s %s%13s%s" % (
            Fore.YELLOW+Style.BRIGHT,
            'Total'.ljust(self.MAX_SYMBOL_LEN),
            '',
            '',
            '',
            self.format_value(cgains.totals['cost']),
            self.format_value(cgains.totals['fees']),
            self.format_value(cgains.totals['proceeds']),
            Fore.RED if cgains.totals['gain'] < 0 else Fore.YELLOW,
            self.format_value(cgains.totals['gain']),
            Style.NORMAL))

        print("\n%sSummary\n" % Fore.CYAN)
        print("%s%-40s %13d" % (Fore.WHITE, "Number of disposals:", cgains.summary['disposals']))
        if cgains.estimate['proceeds_warning']:
            print("%s%-40s %s" % (
                Fore.WHITE, "Disposal proceeds:",
                ('*' + self.format_value(cgains.totals['proceeds'])).rjust(13). \
                        replace('*', Fore.YELLOW + '*' + Fore.WHITE)))
        else:
            print("%s%-40s %13s" % (
                Fore.WHITE, "Disposal proceeds:",
                self.format_value(cgains.totals['proceeds'])))

        print("%s%-40s %13s" % (
            Fore.WHITE, "Allowable costs (including the",
            self.format_value(cgains.totals['cost'] + cgains.totals['fees'])))
        print("%spurchase price):" % Fore.WHITE)
        print("%s%-40s %13s" % (
            Fore.WHITE, "Gains in the year, before losses:",
            self.format_value(cgains.summary['total_gain'])))
        print("%s%-40s %13s" % (
            Fore.WHITE, "Losses in the year:",
            self.format_value(abs(cgains.summary['total_loss']))))

        if cgains.estimate['proceeds_warning']:
            print("%s*Assets sold are more than 4 times the annual allowance (%s), "
                  "this needs to be reported to HMRC" % (
                      Fore.YELLOW, self.format_value(cgains.estimate['allowance'] * 4)))

        if not summary:
            if tax_rules in config.TAX_RULES_UK_COMPANY:
                self.ct_estimate(tax_year)
            else:
                self.cgt_estimate(tax_year)

    def cgt_estimate(self, tax_year):
        cgains = self.tax_report[tax_year]['CapitalGains']
        print("\n%sTax Estimate\n" % Fore.CYAN)
        print("%sThe figures below are only an estimate, they do not take into consideration "
              "other gains and losses in the same tax year, always consult with a professional "
              "accountant before filing.\n" % Fore.CYAN)
        if cgains.totals['gain'] > 0:
            print("%s%s %13s" % (
                Fore.WHITE,
                "Taxable Gain*:".ljust(40).replace('*', Fore.YELLOW + '*' + Fore.WHITE),
                self.format_value(cgains.estimate['taxable_gain'])))
        else:
            print("%s%-40s %13s" % (
                Fore.WHITE,
                "Taxable Gain:",
                self.format_value(cgains.estimate['taxable_gain'])))

        print("%s%-40s %13s (%s)" % (
            Fore.WHITE, "Capital Gains Tax (Basic rate):",
            self.format_value(cgains.estimate['cgt_basic']),
            self.format_rate(cgains.estimate['cgt_basic_rate'])))
        print("%s%-40s %13s (%s)" % (
            Fore.WHITE, "Capital Gains Tax (Higher rate):",
            self.format_value(cgains.estimate['cgt_higher']),
            self.format_rate(cgains.estimate['cgt_higher_rate'])))

        if cgains.estimate['allowance_used']:
            print("%s*%s of the tax-free allowance (%s) used" % (
                Fore.YELLOW,
                self.format_value(cgains.estimate['allowance_used']),
                self.format_value(cgains.estimate['allowance'])))

    def ct_estimate(self, tax_year):
        cgains = self.tax_report[tax_year]['CapitalGains']
        print("\n%sTax Estimate\n" % Fore.CYAN)
        print("%sThe figures below are only an estimate, they do not take into consideration "
              "other gains and losses in the same tax year, always consult with a professional "
              "accountant before filing.\n" % Fore.CYAN)
        print("%s%-40s %13s" % (
              Fore.WHITE,
              "Taxable Gain:",
              self.format_value(cgains.estimate['taxable_gain'])))
        if 'ct_small' in cgains.estimate:
            print("%s%-40s %13s (%s)" % (
                Fore.WHITE, "Corporation Tax (Small profits rate):",
                self.format_value(cgains.estimate['ct_small']),
                '/'.join(map(self.format_rate, cgains.estimate['ct_small_rates']))))

        print("%s%-40s %13s (%s)" % (
            Fore.WHITE, "Corporation Tax (Main rate):",
            self.format_value(cgains.estimate['ct_main']),
            '/'.join(map(self.format_rate, cgains.estimate['ct_main_rates']))))

        if None in cgains.estimate['ct_small_rates']:
            print("%s* Main rate used" % Fore.YELLOW)

    def income(self, tax_year):
        income = self.tax_report[tax_year]['Income']

        print("\n%sIncome\n" % Fore.CYAN)
        header = "%s %-10s %-10s %-40s %-25s %13s %13s" % ('Asset'.ljust(self.MAX_SYMBOL_LEN),
                                                           'Date',
                                                           'Type',
                                                           'Description',
                                                           'Quantity',
                                                           'Amount',
                                                           'Fees')
        print("%s%s" % (Fore.YELLOW, header))

        for asset in sorted(income.assets):
            events = quantity = amount = fees = 0
            for te in income.assets[asset]:
                events += 1
                quantity += te.quantity
                amount += te.amount
                fees += te.fees
                print("%s%s %-10s %-10s %-40s %-25s %13s %13s" % (
                    Fore.WHITE,
                    te.asset.ljust(self.MAX_SYMBOL_LEN),
                    self.format_date(te.date),
                    te.type,
                    te.note,
                    self.format_quantity(te.quantity),
                    self.format_value(te.amount),
                    self.format_value(te.fees)))

            if events > 1:
                print("%s%s %-10s %-10s %-40s %-25s %13s %13s\n" % (
                    Fore.YELLOW,
                    'Total'.ljust(self.MAX_SYMBOL_LEN),
                    '',
                    '',
                    '',
                    self.format_quantity(quantity),
                    self.format_value(amount),
                    self.format_value(fees)))

        print("%s%s %-10s %-40s %-25s %13s %13s" % (
            Fore.YELLOW,
            'Income Type'.ljust(self.MAX_SYMBOL_LEN + 11),
            '',
            '',
            '',
            'Amount',
            'Fees'))

        for i_type in sorted(income.type_totals):
            print("%s%s %-10s %-40s %-25s %13s %13s" % (
                Fore.WHITE,
                i_type.ljust(self.MAX_SYMBOL_LEN + 11),
                '',
                '',
                '',
                self.format_value(income.type_totals[i_type]['amount']),
                self.format_value(income.type_totals[i_type]['fees'])))

        print("%s%s" % (Fore.YELLOW, '_' * len(header)))
        print("%s%s %-10s %-40s %-25s %13s %13s%s" % (
            Fore.YELLOW+Style.BRIGHT,
            'Total'.ljust(self.MAX_SYMBOL_LEN + 11),
            '',
            '',
            '',
            self.format_value(income.totals['amount']),
            self.format_value(income.totals['fees']),
            Style.NORMAL))

    def price_data(self, tax_year):
        print("%sPrice Data - %s\n" % (Fore.CYAN, config.format_tax_year(tax_year)))
        print("%s%s %-16s %-10s  %13s %25s" % (
            Fore.YELLOW,
            'Asset'.ljust(self.ASSET_WIDTH+2),
            'Data Source',
            'Date',
            'Price (%s)' % config.ccy,
            'Price (BTC)'))

        if tax_year not in self.price_report:
            return

        price_missing_flag = False
        for asset in sorted(self.price_report[tax_year]):
            for date in sorted(self.price_report[tax_year][asset]):
                price_data = self.price_report[tax_year][asset][date]
                if price_data['price_ccy'] is not None:
                    print("%s1 %s %-16s %-10s  %13s %25s" % (
                        Fore.WHITE,
                        self.format_asset(asset, price_data['name']).ljust(self.ASSET_WIDTH),
                        price_data['data_source'],
                        self.format_date(date),
                        self.format_value(price_data['price_ccy']),
                        self.format_quantity(price_data['price_btc'])))
                else:
                    price_missing_flag = True
                    print("%s1 %s %-16s %-10s %s%13s %25s" % (
                        Fore.WHITE,
                        self.format_asset(asset, price_data['name']).ljust(self.ASSET_WIDTH),
                        '',
                        self.format_date(date),
                        Fore.BLUE,
                        'Not available*',
                        ''))

        if price_missing_flag:
            print("%s*Price of %s used" % (Fore.BLUE, self.format_value(0)))

    def holdings(self):
        print("%sCurrent Holdings\n" % Fore.CYAN)
        header = "%s %25s %16s %16s %16s" % ('Asset'.ljust(self.ASSET_WIDTH),
                                             'Quantity',
                                             'Cost + Fees',
                                             'Value',
                                             'Gain')
        print("%s%s" % (Fore.YELLOW, header))
        for h in sorted(self.holdings_report['holdings']):
            holding = self.holdings_report['holdings'][h]
            if holding['value'] is not None:
                print("%s%s %25s %16s %16s %s%16s" % (
                    Fore.WHITE,
                    self.format_asset(holding['asset'],
                                      holding['name']).ljust(self.ASSET_WIDTH),
                    self.format_quantity(holding['quantity']),
                    self.format_value(holding['cost']),
                    self.format_value(holding['value']),
                    Fore.RED if holding['gain'] < 0 else Fore.WHITE,
                    self.format_value(holding['gain'])))
            else:
                print("%s%s %25s %16s %s%16s %16s" % (
                    Fore.WHITE,
                    self.format_asset(holding['asset'],
                                      holding['name']).ljust(self.ASSET_WIDTH),
                    self.format_quantity(holding['quantity']),
                    self.format_value(holding['cost']),
                    Fore.BLUE,
                    'Not available',
                    ''))

        print("%s%s" % (Fore.YELLOW, '_' * len(header)))
        print("%s%s %25s %16s %16s %s%16s" % (
            Fore.YELLOW+Style.BRIGHT,
            'Total'.ljust(self.ASSET_WIDTH),
            '',
            self.format_value(self.holdings_report['totals']['cost']),
            self.format_value(self.holdings_report['totals']['value']),
            Fore.RED if self.holdings_report['totals']['gain'] < 0 else Fore.YELLOW,
            self.format_value(self.holdings_report['totals']['gain'])))

    @staticmethod
    def format_date(date):
        if isinstance(date, datetime):
            return date.strftime('%d/%m/%Y')
        return dateutil.parser.parse(date).strftime('%d/%m/%Y')

    @staticmethod
    def format_date2(date):
        return '{} {}{} {}'.format(date.strftime('%b'),
                                   date.day, ReportLog.format_day(date.day), date.strftime('%Y'))

    @staticmethod
    def format_day(day):
        return 'th' if 11<=day<=13 else {1:'st',2:'nd',3:'rd'}.get(day%10, 'th')

    @staticmethod
    def format_quantity(quantity):
        if quantity is not None:
            return '{:0,f}'.format(quantity.normalize())
        return 'n/a'

    @staticmethod
    def format_value(value):
        return config.sym() + '{:0,.5f}'.format(value + 0)

    @staticmethod
    def format_asset(asset, name):
        if name is not None:
            return "%s (%s)" % (asset, name)
        return asset

    @staticmethod
    def format_rate(rate):
        if rate is None:
            return Fore.YELLOW + '*' + Fore.WHITE
        return '{}%'.format(rate)

class ProgressSpinner:
    def __init__(self):
        self.spinner = itertools.cycle(['-', '\\', '|', '/'])
        self.busy = False

    def do_spinner(self):
        while self.busy:
            sys.stdout.write(next(self.spinner))
            sys.stdout.flush()
            time.sleep(0.1)
            sys.stdout.write('\b')
            sys.stdout.flush()

    def __enter__(self):
        if sys.stdout.isatty():
            self.busy = True
            sys.stdout.write("%sgenerating PDF report%s: " % (Fore.CYAN, Fore.GREEN))
            threading.Thread(target=self.do_spinner).start()

    def __exit__(self, exc_type, exc_val, exc_traceback):
        if sys.stdout.isatty():
            self.busy = False
            sys.stdout.write('\r')
