# -*- coding: utf-8 -*-
# Cryptoasset accounting, auditing and UK tax calculations (Capital Gains/Income Tax)
# (c) Nano Nano Ltd 2019

import logging
import argparse
import io
import sys
import codecs

import xlrd

from .version import __version__
from .config import config
from .import_records import ImportRecords
from .transactions import TransactionHistory
from .audit import audit_records
from .price.valueasset import ValueAsset
from .tax import TaxCalculator

if sys.version_info[0] >= 3:
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO,
                    format='[%(asctime)s.%(msecs)03d] %(levelname)s -- : %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S')
log = logging.getLogger()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename",
                        type=str,
                        nargs='?',
                        help="filename of transaction records, "
                             "or can read CSV data from standard input")
    parser.add_argument("-v",
                        "--version",
                        action='version',
                        version='%(prog)s {version}'.format(version=__version__))
    parser.add_argument("-d",
                        "--debug",
                        action='store_true',
                        help="enabled debug logging")
    parser.add_argument("-ty",
                        "--taxyear",
                        type=int,
                        help="tax year")
    parser.add_argument("-s",
                        "--skipaudit",
                        action='store_true',
                        help="skip auditing of transactions")

    config.args = parser.parse_args()
    config.args.nocache = False

    if config.args.debug:
        log.setLevel(logging.DEBUG)
        config.output_config(parser.prog)

    import_records = ImportRecords()

    if config.args.filename:
        try:
            import_records.import_excel(config.args.filename)
        except xlrd.XLRDError:
            with io.open(config.args.filename, newline='', encoding='utf-8') as csv_file:
                import_records.import_csv(csv_file)
    else:
        if sys.version_info[0] < 3:
            import_records.import_csv(codecs.getreader('utf-8')(sys.stdin))
        else:
            import_records.import_csv(sys.stdin)

    if import_records.failures():
        parser.exit()

    transaction_records = import_records.get_records()

    if not config.args.skipaudit:
        audit_records(transaction_records)

    value_asset = ValueAsset()
    transaction_history = TransactionHistory(transaction_records, value_asset)

    tax = TaxCalculator(transaction_history.transactions)
    tax.pool_same_day()
    tax.match(tax.DISPOSAL_SAME_DAY)
    tax.match(tax.DISPOSAL_BED_AND_BREAKFAST)

    if config.args.debug:
        tax.output_transactions()

    tax.process_unmatched()
    tax.process_income()

    if config.args.taxyear:
        tax.report_capital_gains(config.args.taxyear)
        tax.report_income(config.args.taxyear)
    else:
        # Output for all years
        for year in sorted(tax.tax_events):
            tax.report_capital_gains(year)
            tax.report_income(year)

        tax.report_holdings(value_asset)
