# -*- coding: utf-8 -*-
# Cryptoasset accounting, auditing and UK tax calculations (Capital Gains/Income Tax)
# (c) Nano Nano Ltd 2019

import argparse
import io
import sys
import codecs
import platform

import colorama
from colorama import Fore, Back
import xlrd

from .version import __version__
from .config import config
from .import_records import ImportRecords
from .transactions import TransactionHistory
from .audit import AuditRecords
from .price.valueasset import ValueAsset
from .price.exceptions import UnexpectedDataSourceError
from .tax import TaxCalculator, CalculateCapitalGains as CCG
from .report import ReportLog, ReportPdf
from .exceptions import ImportFailureError

if sys.stdout.encoding != 'UTF-8':
    if sys.version_info[:2] >= (3, 7):
        sys.stdout.reconfigure(encoding='utf-8')
    elif sys.version_info[:2] >= (3, 1):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    else:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

def main():
    colorama.init()
    parser = argparse.ArgumentParser()
    parser.add_argument('filename',
                        type=str,
                        nargs='?',
                        help="filename of transaction records, "
                             "or can read CSV data from standard input")
    parser.add_argument('-v',
                        '--version',
                        action='version',
                        version='%s v%s' % (parser.prog, __version__))
    parser.add_argument('-d',
                        '--debug',
                        action='store_true',
                        help="enable debug logging")
    parser.add_argument('-ty',
                        '--taxyear',
                        type=validate_year,
                        help="tax year must be in the range (%s-%s)" % (
                            min(CCG.CG_DATA_INDIVIDUALS),
                            max(CCG.CG_DATA_INDIVIDUALS)))
    parser.add_argument('-s',
                        '--skipaudit',
                        action='store_true',
                        help="skip auditing of transaction records")
    parser.add_argument('--summary',
                        action='store_true',
                        help="only output the capital gains summary in the tax report")
    parser.add_argument('-o',
                        dest='output_filename',
                        type=str,
                        help="specify the output filename for the tax report")
    parser.add_argument('--nopdf',
                        action='store_true',
                        help="don't output PDF report, output report to terminal only")

    config.args = parser.parse_args()
    config.args.nocache = False

    if config.args.debug:
        print("%s%s v%s" % (Fore.YELLOW, parser.prog, __version__))
        print("%spython: v%s" % (Fore.GREEN, platform.python_version()))
        print("%ssystem: %s, release: %s" % (Fore.GREEN, platform.system(), platform.release()))
        config.output_config()

    try:
        transaction_records = do_import(config.args.filename)
    except IOError:
        parser.exit("%sERROR%s File could not be read: %s" % (
            Back.RED+Fore.BLACK, Back.RESET+Fore.RED, config.args.filename))
    except ImportFailureError:
        parser.exit()

    if not config.args.skipaudit and not config.args.summary:
        audit = AuditRecords(transaction_records)
    else:
        audit = None

    try:
        tax, value_asset = do_tax(transaction_records,
                                  config.args.taxyear,
                                  config.args.summary)
    except UnexpectedDataSourceError as e:
        parser.exit("%sERROR%s %s" % (
            Back.RED+Fore.BLACK, Back.RESET+Fore.RED, e))

    if config.args.nopdf:
        ReportLog(audit,
                  tax.tax_report,
                  value_asset.price_report,
                  tax.holdings_report)
    else:
        ReportPdf(parser.prog,
                  audit,
                  tax.tax_report,
                  value_asset.price_report,
                  tax.holdings_report)

def validate_year(value):
    year = int(value)
    if year not in CCG.CG_DATA_INDIVIDUALS:
        raise argparse.ArgumentTypeError("tax year %d is not supported, "
                                         "must be in the range (%s-%s)" % (
            year,
            min(CCG.CG_DATA_INDIVIDUALS),
            max(CCG.CG_DATA_INDIVIDUALS)))

    return year

def do_import(filename):
    import_records = ImportRecords()

    if filename:
        try:
            import_records.import_excel(filename)
        except xlrd.XLRDError:
            with io.open(filename, newline='', encoding='utf-8') as csv_file:
                import_records.import_csv(csv_file)
    else:
        if sys.version_info[0] < 3:
            import_records.import_csv(codecs.getreader('utf-8')(sys.stdin))
        else:
            import_records.import_csv(sys.stdin)

    print("%simport %s (success=%s, failure=%s)" % (
        Fore.WHITE, 'successful' if import_records.failure_cnt <= 0 else 'failure',
        import_records.success_cnt, import_records.failure_cnt))

    if import_records.failure_cnt > 0:
        raise ImportFailureError

    return import_records.get_records()

def do_tax(transaction_records, tax_year, summary):
    value_asset = ValueAsset()
    transaction_history = TransactionHistory(transaction_records, value_asset)

    tax = TaxCalculator(transaction_history.transactions)
    tax.pool_same_day()
    tax.match(tax.DISPOSAL_SAME_DAY)
    tax.match(tax.DISPOSAL_BED_AND_BREAKFAST)

    if config.args.debug:
        tax.output_transactions()

    tax.process_unmatched()

    if not summary:
        tax.process_income()

    if tax_year:
        print("%scalculating tax year %d/%d" % (
            Fore.CYAN, tax_year - 1, tax_year))
        tax.calculate_capital_gains(tax_year)
        if not summary:
            tax.calculate_income(tax_year)
    else:
        # Calculate for all years
        for year in sorted(tax.tax_events):
            print("%scalculating tax year %d/%d" % (
                Fore.CYAN, year - 1, year))
            if year in CCG.CG_DATA_INDIVIDUALS:
                tax.calculate_capital_gains(year)
                if not summary:
                    tax.calculate_income(year)
            else:
                print("%sWARNING%s Tax year %s is not supported" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, year))

        if not summary:
            tax.calculate_holdings(value_asset)

    return tax, value_asset
