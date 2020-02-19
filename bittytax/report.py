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

    def __init__(self, progname, holdings_report, tax_report, price_report):
        self.env = jinja2.Environment(loader=jinja2.PackageLoader('bittytax', 'templates'))
        self.filename = self.get_output_filename(self.FILE_EXTENSION)

        self.env.filters['datefilter'] = self.datefilter
        self.env.filters['quantityfilter'] = self.quantityfilter
        self.env.filters['valuefilter'] = self.valuefilter
        self.env.filters['nowrapfilter'] = self.nowrapfilter

        template = self.env.get_template(self.TEMPLATE_FILE)
        html = template.render({'date': datetime.now(),
                                'author': '{} {}'.format(progname, __version__),
                                'holdings_report': holdings_report,
                                'tax_report': tax_report,
                                'price_report': price_report,
                                'config': config})

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
    def __init__(self, holdings_report, tax_report, price_report):
        self.holdings_report = holdings_report
        self.tax_report = tax_report
        self.price_report = price_report

        if config.args.nopdf:
            level = logging.INFO
        else:
            level = logging.DEBUG

        if config.args.taxyear:
            log.log(level, "==TAX YEAR %s/%s==", config.args.taxyear - 1, config.args.taxyear)
            self.capital_gains(config.args.taxyear, level)
            if not config.args.summary:
                self.income(config.args.taxyear, level)
        else:
            for tax_year in sorted(tax_report):
                log.log(level, "==TAX YEAR %s/%s==", tax_year - 1, tax_year)
                self.capital_gains(tax_year, level)
                if not config.args.summary:
                    self.income(tax_year, level)

            if not config.args.summary:
                self.holdings()

            if config.args.debug:
                self.price_data()

    def capital_gains(self, tax_year, level):
        cgains = self.tax_report[tax_year]['CapitalGains']

        log.log(level, "--CAPITAL GAINS--")
        log.log(level, "%s %s %s %s %s %s %s %s",
                "Asset".ljust(7),
                "Date".ljust(10),
                "Disposal Type".ljust(28),
                "Quantity".rjust(25),
                "Cost".rjust(13),
                "Fees".rjust(13),
                "Proceeds".rjust(13),
                "Gain".rjust(13))

        for asset in sorted(cgains.assets):
            for te in cgains.assets[asset]:
                log.log(level, te)

        log.log(level, "-TAX SUMMARY-")
        log.log(level, "Number of disposals=%s", cgains.summary['disposals'])
        log.log(level, "Disposal proceeds=%s%s",
                config.sym(), '{:0,.2f}'.format(cgains.totals['proceeds']))

        if cgains.estimate['proceeds_warning']:
            log.warning("Assets sold are more than 4 times the annual allowance (%s%s), "
                        "this needs to be reported to HMRC",
                        config.sym(), '{:0,.2f}'.format(cgains.estimate['allowance'] * 4))

        log.log(level, "Allowable costs=%s%s",
                config.sym(), '{:0,.2f}'.format(cgains.totals['cost'] + cgains.totals['fees']))
        log.log(level, "Gains in the year, before losses=%s%s",
                config.sym(), '{:0,.2f}'.format(cgains.summary['total_gain']))
        log.log(level, "Losses in the year=%s%s",
                config.sym(), '{:0,.2f}'.format(abs(cgains.summary['total_loss'])))

        if not config.args.summary:
            log.log(level, "-TAX ESTIMATE-")
            log.log(level, "Taxable Gain=%s%s (-%s%s tax-free allowance)",
                    config.sym(), '{:0,.2f}'.format(cgains.estimate['taxable_gain']),
                    config.sym(), '{:0,.2f}'.format(cgains.estimate['allowance']))
            log.log(level, "Capital Gains Tax (Basic rate)=%s%s",
                    config.sym(), '{:0,.2f}'.format(cgains.estimate['cgt_basic']))
            log.log(level, "Capital Gains Tax (Higher rate)=%s%s",
                    config.sym(), '{:0,.2f}'.format(cgains.estimate['cgt_higher']))

    def income(self, tax_year, level):
        income = self.tax_report[tax_year]['Income']

        log.log(level, "--INCOME--")
        log.log(level, "%s %s %s %s %s %s",
                "Asset".ljust(7),
                "Date".ljust(10),
                "Income Type".ljust(28),
                "Quantity".rjust(25),
                "Amount".rjust(13),
                "Fees".rjust(13))

        for asset in sorted(income.assets):
            for te in income.assets[asset]:
                log.log(level, te)

        log.log(level, "%s %s %s",
                "Income Type".ljust(73),
                "Amount".rjust(13),
                "Fees".rjust(13))

        for i_type in sorted(income.type_totals):
            log.log(level, "%s %s %s",
                    i_type.ljust(73),
                    self.format_value(income.type_totals[i_type]['amount']).rjust(13),
                    self.format_quantity(income.type_totals[i_type]['fees']).rjust(13))

    def price_data(self):
        for tax_year in sorted(self.price_report):
            log.debug("==PRICE DATA %s/%s==", tax_year - 1, tax_year)
            log.debug("%s %s %s %s %s",
                      "Asset".ljust(9),
                      "Date".ljust(10),
                      "Data Source".ljust(20),
                      "Price (GBP)".rjust(13),
                      "Price (BTC)".rjust(25))

            for asset in sorted(self.price_report[tax_year]):
                for date in sorted(self.price_report[tax_year][asset]):
                    log.debug("%s %s %s %s %s",
                              ("1 " + asset).ljust(9),
                              dateutil.parser.parse(date).strftime('%d/%m/%Y').ljust(10),
                              self.price_report[tax_year][asset][date]['data_source'].ljust(20),
                              self.format_value(self.price_report[tax_year][asset] \
                                      [date]['price_ccy']).rjust(13),
                              self.format_quantity(self.price_report[tax_year][asset] \
                                      [date]['price_btc']).rjust(25))

    def holdings(self):
        holdings = self.holdings_report['holdings']

        log.info("==CURRENT HOLDINGS==")
        log.info("%s %s %s %s  %s",
                 "Asset".ljust(7),
                 "Quantity".rjust(25),
                 "Cost".rjust(13),
                 "Value".rjust(13),
                 "Data Source")

        for h in sorted(holdings):
            if holdings[h]['value'] is not None:
                log.info("%s %s %s %s  %s (%s)",
                         holdings[h]['asset'].ljust(7),
                         self.format_quantity(holdings[h]['quantity']).rjust(25),
                         (config.sym() + '{:0,.2f}'.format(holdings[h]['cost'])).rjust(13),
                         (config.sym() + '{:0,.2f}'.format(holdings[h]['value'])).rjust(13),
                         holdings[h]['data_source'],
                         holdings[h]['name'])
            else:
                log.info("%s %s %s %s  -",
                         holdings[h]['asset'].ljust(7),
                         self.format_quantity(holdings[h]['quantity']).rjust(25),
                         (config.sym() + '{:0,.2f}'.format(holdings[h]['cost'])).rjust(13),
                         (config.sym() + '0.00').rjust(13))

        log.info("Total cost=%s%s",
                 config.sym(), '{:0,.2f}'.format(self.holdings_report['totals']['cost']))
        log.info("Total value=%s%s",
                 config.sym(), '{:0,.2f}'.format(self.holdings_report['totals']['value']))

    @staticmethod
    def format_quantity(quantity):
        if quantity is not None:
            return '{:0,f}'.format(quantity.normalize())
        return 'n/a'

    @staticmethod
    def format_value(value):
        if value is not None:
            return config.sym() + '{:0,.2f}'.format(value)
        return 'NOT AVAILABLE'
