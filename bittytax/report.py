# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import os
from datetime import datetime

import jinja2
from xhtml2pdf import pisa

from .version import __version__
from .config import config

log = logging.getLogger()

class ReportPdf(object):
    DEFAULT_FILENAME = 'BittyTax_Report'
    FILE_EXTENSION = 'pdf'
    TEMPLATE_FILE = 'tax_report.html'

    def __init__(self, progname, tax_report):
        self.env = jinja2.Environment(loader=jinja2.PackageLoader('bittytax', 'templates'))
        self.filename = self.get_output_filename(self.FILE_EXTENSION)

        self.env.filters['datefilter'] = self.datefilter
        self.env.filters['quantityfilter'] = self.quantityfilter
        self.env.filters['valuefilter'] = self.valuefilter
        self.env.filters['nowrapfilter'] = self.nowrapfilter

        template = self.env.get_template(self.TEMPLATE_FILE)
        html = template.render({'date': datetime.now(),
                                'author': '{} {}'.format(progname, __version__),
                                'tax_report': tax_report,
                                'config': config})

        log.info("Generating PDF report...")
        pdf_file = open(self.filename, 'w+b')
        status = pisa.CreatePDF(html, dest=pdf_file)
        pdf_file.close()

        if not status.err:
            log.info("PDF tax report file created: %s", self.filename)

    @staticmethod
    def datefilter(date):
        return date.strftime('%d/%m/%Y')

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
    def __init__(self, tax_report):
        self.tax_report = tax_report

        if config.args.taxyear:
            log.debug("==TAX YEAR %s/%s==", config.args.taxyear - 1, config.args.taxyear)
            self.capital_gains(config.args.taxyear)
            if not config.args.summary:
                self.income(config.args.taxyear)
        else:
            for tax_year in sorted(tax_report):
                log.debug("==TAX YEAR %s/%s==", tax_year - 1, tax_year)
                self.capital_gains(tax_year)
                if not config.args.summary:
                    self.income(tax_year)

    def capital_gains(self, tax_year):
        cgains = self.tax_report[tax_year]['CapitalGains']

        log.debug("--CAPITAL GAINS--")
        log.debug("%s %s %s %s %s %s %s %s",
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
                log.debug(te)

        log.debug("-TAX SUMMARY-")
        log.debug("Number of disposals=%s", cgains.summary['disposals'])
        log.debug("Disposal proceeds=%s%s",
                  config.sym(), '{:0,.2f}'.format(cgains.totals['proceeds']))

        if cgains.estimate['proceeds_warning']:
            log.warning("Assets sold are more than 4 times the annual allowance (%s%s), "
                        "this needs to be reported to HMRC",
                        config.sym(), '{:0,.2f}'.format(cgains.estimate['allowance'] * 4))

        log.debug("Allowable costs=%s%s",
                  config.sym(), '{:0,.2f}'.format(cgains.totals['cost'] + cgains.totals['fees']))
        log.debug("Gains in the year, before losses=%s%s",
                  config.sym(), '{:0,.2f}'.format(cgains.summary['total_gain']))
        log.debug("Losses in the year=%s%s",
                  config.sym(), '{:0,.2f}'.format(abs(cgains.summary['total_loss'])))

        if not config.args.summary:
            log.debug("-TAX ESTIMATE-")
            log.debug("Taxable Gain=%s%s (-%s%s tax-free allowance)",
                      config.sym(), '{:0,.2f}'.format(cgains.estimate['taxable_gain']),
                      config.sym(), '{:0,.2f}'.format(cgains.estimate['allowance']))
            log.debug("Capital Gains Tax (Basic rate)=%s%s",
                      config.sym(), '{:0,.2f}'.format(cgains.estimate['cgt_basic']))
            log.debug("Capital Gains Tax (Higher rate)=%s%s",
                      config.sym(), '{:0,.2f}'.format(cgains.estimate['cgt_higher']))

    def income(self, tax_year):
        income = self.tax_report[tax_year]['Income']

        log.debug("--INCOME--")
        log.debug("%s %s %s %s %s %s",
                  "Asset".ljust(7),
                  "Date".ljust(10),
                  "Income Type".ljust(28),
                  "Quantity".rjust(25),
                  "Amount".rjust(13),
                  "Fees".rjust(13))

        for asset in sorted(income.assets):
            for te in income.assets[asset]:
                log.debug(te)

        log.debug("Total income=%s%s", config.sym(), '{:0,.2f}'.format(income.totals['amount']))
        log.debug("Total fees=%s%s", config.sym(), '{:0,.2f}'.format(income.totals['fees']))
