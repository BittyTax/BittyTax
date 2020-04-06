# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import os
from datetime import datetime

import jinja2
from xhtml2pdf import pisa
import dateutil.parser

from .version import __version__
from .config import config

log = logging.getLogger()

class ReportPdf(object):
    DEFAULT_FILENAME = 'BittyTax_Report'
    FILE_EXTENSION = 'pdf'
    TEMPLATE_FILE = 'tax_report.html'

    def __init__(self, progname, audit, tax_report, price_report, holdings_report):
        self.env = jinja2.Environment(loader=jinja2.PackageLoader('bittytax', 'templates'))
        self.filename = self.get_output_filename(self.FILE_EXTENSION)

        self.env.filters['datefilter'] = self.datefilter
        self.env.filters['quantityfilter'] = self.quantityfilter
        self.env.filters['valuefilter'] = self.valuefilter
        self.env.filters['nowrapfilter'] = self.nowrapfilter

        template = self.env.get_template(self.TEMPLATE_FILE)
        html = template.render({'date': datetime.now(),
                                'author': '{} {}'.format(progname, __version__),
                                'config': config,
                                'audit': audit,
                                'tax_report': tax_report,
                                'price_report': price_report,
                                'holdings_report': holdings_report})

        log.info("Generating PDF report...")
        pdf_file = open(self.filename, 'w+b')
        status = pisa.CreatePDF(html, dest=pdf_file)
        pdf_file.close()

        if not status.err:
            log.info("PDF tax report file created: %s", self.filename)

    @staticmethod
    def datefilter(date):
        if isinstance(date, datetime):
            return date.strftime('%d/%m/%Y')
        else:
            return dateutil.parser.parse(date).strftime('%d/%m/%Y')

    @staticmethod
    def quantityfilter(quantity):
        return '{:0,f}'.format(quantity.normalize())

    @staticmethod
    def valuefilter(value):
        return '&pound;{:0,.2f}'.format(value)

    @staticmethod
    def nowrapfilter(text):
        return text.replace(' ', '&nbsp;')

    @staticmethod
    def get_output_filename(extension_type):
        if config.args.output_filename:
            filepath, file_extension = os.path.splitext(config.args.output_filename)
            if file_extension != extension_type:
                filepath = filepath + '.' + extension_type
        else:
            filepath = ReportPdf.DEFAULT_FILENAME + '.' + extension_type

        if not os.path.exists(filepath):
            return filepath

        filepath, file_extension = os.path.splitext(filepath)
        i = 2
        new_fname = '{}-{}{}'.format(filepath, i, file_extension)
        while os.path.exists(new_fname):
            i += 1
            new_fname = '{}-{}{}'.format(filepath, i, file_extension)

        return new_fname

class ReportLog(object):
    MAX_SYMBOL_LEN = 8
    MAX_NAME_LEN = 32
    ASSET_WIDTH = MAX_SYMBOL_LEN + MAX_NAME_LEN + 3

    def __init__(self, audit, tax_report, price_report, holdings_report):
        self.audit_report = audit
        self.tax_report = tax_report
        self.price_report = price_report
        self.holdings_report = holdings_report

        if config.args.taxyear:
            if self.audit and not config.args.summary:
                self.audit()
            log.info("==TAX YEAR %s/%s==", config.args.taxyear - 1, config.args.taxyear)
            self.capital_gains(config.args.taxyear)
            if not config.args.summary:
                self.income(config.args.taxyear)
                self.price_data(config.args.taxyear)
        else:
            if self.audit and not config.args.summary:
                self.audit()
            for tax_year in sorted(tax_report):
                log.info("==TAX YEAR %s/%s==", tax_year - 1, tax_year)
                self.capital_gains(tax_year)
                if not config.args.summary:
                    self.income(tax_year)

            if not config.args.summary:
                log.info("==APPENDIX==")
                for tax_year in sorted(tax_report):
                    self.price_data(tax_year)
                self.holdings()

    def audit(self):
        log.info("==FINAL AUDIT BALANCES==")
        for wallet in sorted(self.audit_report.wallets):
            for asset in sorted(self.audit_report.wallets[wallet]):
                log.info("%s:%s=%s",
                         wallet,
                         asset,
                         self.format_quantity(self.audit_report.wallets[wallet][asset]))

    def capital_gains(self, tax_year):
        cgains = self.tax_report[tax_year]['CapitalGains']

        log.info("--CAPITAL GAINS--")
        header = "%s %s %s %s %s %s %s %s" % ("Asset".ljust(self.MAX_SYMBOL_LEN),
                                              "Date".ljust(10),
                                              "Disposal Type".ljust(28),
                                              "Quantity".rjust(25),
                                              "Cost".rjust(13),
                                              "Fees".rjust(13),
                                              "Proceeds".rjust(13),
                                              "Gain".rjust(13))
        log.info(header)

        for asset in sorted(cgains.assets):
            for te in cgains.assets[asset]:
                log.info("%s %s %s %s %s %s %s %s",
                         te.asset.ljust(self.MAX_SYMBOL_LEN),
                         self.format_date(te.date),
                         te.format_disposal().ljust(28),
                         self.format_quantity(te.quantity).rjust(25),
                         self.format_value(te.cost).rjust(13),
                         self.format_value(te.fees).rjust(13),
                         self.format_value(te.proceeds).rjust(13),
                         self.format_value(te.gain).rjust(13))

        log.info("%s", '-' * len(header))
        log.info("%s %s %s %s %s %s %s %s",
                 "Total".ljust(self.MAX_SYMBOL_LEN),
                 ' ' * 10,
                 ' ' * 28,
                 ' ' * 25,
                 self.format_value(cgains.totals['cost']).rjust(13),
                 self.format_value(cgains.totals['fees']).rjust(13),
                 self.format_value(cgains.totals['proceeds']).rjust(13),
                 self.format_value(cgains.totals['gain']).rjust(13))

        log.info("-TAX SUMMARY-")
        log.info("Number of disposals=%s", cgains.summary['disposals'])
        log.info("Disposal proceeds=%s",
                 self.format_value(cgains.totals['proceeds']))

        if cgains.estimate['proceeds_warning']:
            log.warning("Assets sold are more than 4 times the annual allowance (%s), "
                        "this needs to be reported to HMRC",
                        self.format_value(cgains.estimate['allowance'] * 4))

        log.info("Allowable costs=%s",
                 self.format_value(cgains.totals['cost'] + cgains.totals['fees']))
        log.info("Gains in the year, before losses=%s",
                 self.format_value(cgains.summary['total_gain']))
        log.info("Losses in the year=%s",
                 self.format_value(abs(cgains.summary['total_loss'])))

        if not config.args.summary:
            log.info("-TAX ESTIMATE-")
            if cgains.totals['gain'] > 0:
                log.info("Taxable Gain=%s (%s of the tax-fee allowance %s used)",
                         self.format_value(cgains.estimate['taxable_gain']),
                         self.format_value(cgains.estimate['allowance_used']),
                         self.format_value(cgains.estimate['allowance']))
            else:
                log.info("Taxable Gain=%s",
                         self.format_value(cgains.estimate['taxable_gain']))
            log.info("Capital Gains Tax (Basic rate)=%s",
                     self.format_value(cgains.estimate['cgt_basic']))
            log.info("Capital Gains Tax (Higher rate)=%s",
                     self.format_value(cgains.estimate['cgt_higher']))

    def income(self, tax_year):
        income = self.tax_report[tax_year]['Income']

        log.info("--INCOME--")
        header = "%s %s %s %s %s %s" % ("Asset".ljust(self.MAX_SYMBOL_LEN),
                                        "Date".ljust(10),
                                        "Income Type".ljust(28),
                                        "Quantity".rjust(25),
                                        "Amount".rjust(13),
                                        "Fees".rjust(13))
        log.info(header)

        for asset in sorted(income.assets):
            for te in income.assets[asset]:
                log.info("%s %s %s %s %s %s",
                         te.asset.ljust(self.MAX_SYMBOL_LEN),
                         self.format_date(te.date),
                         te.type.ljust(28),
                         self.format_quantity(te.quantity).rjust(25),
                         self.format_value(te.amount).rjust(13),
                         self.format_value(te.fees).rjust(13))

        log.info("%s %s %s %s %s",
                 "Income Type".ljust(self.MAX_SYMBOL_LEN + 11),
                 ' ' * 28,
                 ' ' * 25,
                 "Amount".rjust(13),
                 "Fees".rjust(13))

        for i_type in sorted(income.type_totals):
            log.info("%s %s %s %s %s",
                     i_type.ljust(self.MAX_SYMBOL_LEN + 11),
                     ' ' * 28,
                     ' ' * 25,
                     self.format_value(income.type_totals[i_type]['amount']).rjust(13),
                     self.format_value(income.type_totals[i_type]['fees']).rjust(13))

        log.info("%s", '-' * len(header))
        log.info("%s %s %s %s %s",
                 "Total".ljust(self.MAX_SYMBOL_LEN + 11),
                 ' ' * 28,
                 ' ' * 25,
                 self.format_value(income.totals['amount']).rjust(13),
                 self.format_value(income.totals['fees']).rjust(13))

    def price_data(self, tax_year):
        log.info("--PRICE DATA %s/%s--", tax_year - 1, tax_year)
        log.info("%s %s %s %s %s",
                 "Asset".ljust(self.ASSET_WIDTH),
                 "Data Source".ljust(16),
                 "Date".ljust(10),
                 "Price (GBP)".rjust(13),
                 "Price (BTC)".rjust(25))

        if tax_year not in self.price_report:
            return

        for asset in sorted(self.price_report[tax_year]):
            for date in sorted(self.price_report[tax_year][asset]):
                price_data = self.price_report[tax_year][asset][date]
                if price_data['price_ccy'] is not None:
                    log.info("1 %s %s %s %s %s",
                             self.format_asset(asset, price_data['name']).ljust(self.ASSET_WIDTH),
                             price_data['data_source'].ljust(16),
                             self.format_date(date),
                             self.format_value(price_data['price_ccy']).rjust(13),
                             self.format_quantity(price_data['price_btc']).rjust(25))
                else:
                    log.info("1 %s %s %s %s",
                             self.format_asset(asset, price_data['name']).ljust(self.ASSET_WIDTH),
                             ' ' * 16,
                             self.format_date(date),
                             self.format_value(price_data['price_ccy']).rjust(13))

    def holdings(self):
        log.info("==CURRENT HOLDINGS==")
        header = "%s %s %s %s %s" % ("Asset".ljust(self.ASSET_WIDTH),
                                     "Quantity".rjust(25),
                                     "Cost + Fees".rjust(16),
                                     "Value".rjust(16),
                                     "Gain".rjust(16))
        log.info(header)

        for h in sorted(self.holdings_report['holdings']):
            holding = self.holdings_report['holdings'][h]
            if holding['value'] is not None:
                log.info("%s %s %s %s %s",
                         self.format_asset(holding['asset'],
                                           holding['name']).ljust(self.ASSET_WIDTH),
                         self.format_quantity(holding['quantity']).rjust(25),
                         self.format_value(holding['cost']).rjust(16),
                         self.format_value(holding['value']).rjust(16),
                         self.format_value(holding['gain']).rjust(16))
            else:
                log.info("%s %s %s %s",
                         self.format_asset(holding['asset'],
                                           holding['name']).ljust(self.ASSET_WIDTH),
                         self.format_quantity(holding['quantity']).rjust(25),
                         self.format_value(holding['cost']).rjust(16),
                         self.format_value(holding['value']).rjust(16))

        log.info("%s", '-' * len(header))
        log.info("%s %s %s %s %s",
                 "Total".ljust(self.ASSET_WIDTH),
                 ' ' * 25,
                 self.format_value(self.holdings_report['totals']['cost']).rjust(16),
                 self.format_value(self.holdings_report['totals']['value']).rjust(16),
                 self.format_value(self.holdings_report['totals']['gain']).rjust(16))

    @staticmethod
    def format_date(date):
        if isinstance(date, datetime):
            return date.strftime('%d/%m/%Y')
        else:
            return dateutil.parser.parse(date).strftime('%d/%m/%Y')

    @staticmethod
    def format_quantity(quantity):
        if quantity is not None:
            return '{:0,f}'.format(quantity.normalize())
        return 'n/a'

    @staticmethod
    def format_value(value):
        if value is not None:
            return config.sym() + '{:0,.2f}'.format(value + 0)
        return 'NOT AVAILABLE'

    @staticmethod
    def format_asset(asset, name):
        if name is not None:
            return '{} ({})'.format(asset, name)
        return asset
