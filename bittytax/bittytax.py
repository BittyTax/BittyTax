# -*- coding: utf-8 -*-
# Cryptoasset accounting, auditing and UK tax calculations (Capital Gains/Income Tax)
# (c) Nano Nano Ltd 2019

import logging
import argparse
import io
import sys

from .version import __version__
from .config import config
from .transactions import load_transaction_records, TransactionHistory
from .audit import audit_transactions
from .price.valueasset import ValueAsset
from .tax import TaxCalculator

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
                             "or can read from standard input")
    parser.add_argument("-ty",
                        "--taxyear",
                        type=int,
                        help="tax year")
    parser.add_argument("-s",
                        "--skipaudit",
                        action='store_true',
                        help="skip auditing of transactions")
    parser.add_argument("-d",
                        "--debug",
                        action='store_true',
                        help="enabled debug logging")
    parser.add_argument("-v",
                        "--version",
                        action='version',
                        version='%(prog)s {version}'.format(version=__version__))

    config.args = parser.parse_args()
    config.args.nocache = False

    if config.args.debug:
        log.setLevel(logging.DEBUG)
        config.output_config(parser.prog)

    if config.args.filename:
        with io.open(config.args.filename, newline='', encoding='utf-8') as import_file:
            transaction_records = load_transaction_records(import_file)
            import_file.close()
    else:
        transaction_records = load_transaction_records(sys.stdin)

    if not config.args.skipaudit:
        audit_transactions(sorted(transaction_records))

    transaction_history = TransactionHistory(transaction_records)
    value_asset = ValueAsset()
    transactions = transaction_history.split_transaction_records(value_asset)

    tax = TaxCalculator(transactions)
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
