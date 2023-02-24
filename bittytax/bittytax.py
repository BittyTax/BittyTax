# -*- coding: utf-8 -*-
# Cryptocurrency tax calculator for UK tax rules
# (c) Nano Nano Ltd 2019

import argparse
import codecs
import io
import platform
import sys

import colorama
import xlrd
from colorama import Back, Fore

from .audit import AuditRecords
from .config import config
from .exceptions import ImportFailureError
from .export_records import ExportRecords
from .import_records import ImportRecords
from .price.exceptions import DataSourceError
from .price.valueasset import ValueAsset
from .report import ReportLog, ReportPdf
from .tax import CalculateCapitalGains as CCG
from .tax import TaxCalculator
from .transactions import TransactionHistory
from .version import __version__

if sys.stdout.encoding != "UTF-8":
    if sys.version_info[:2] >= (3, 7):
        sys.stdout.reconfigure(encoding="utf-8")
    elif sys.version_info[:2] >= (3, 1):
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    else:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout)


def main():
    colorama.init()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "filename",
        type=str,
        nargs="?",
        help="filename of transaction records, or can read CSV data from standard input",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%s v%s" % (parser.prog, __version__),
    )
    parser.add_argument("-d", "--debug", action="store_true", help="enable debug logging")
    parser.add_argument(
        "-ty",
        "--taxyear",
        type=validate_year,
        help="tax year must be in the range (%s-%s)"
        % (min(CCG.CG_DATA_INDIVIDUAL), max(CCG.CG_DATA_INDIVIDUAL)),
    )
    parser.add_argument(
        "--taxrules",
        choices=[config.TAX_RULES_UK_INDIVIDUAL] + config.TAX_RULES_UK_COMPANY,
        metavar="{UK_INDIVIDUAL, UK_COMPANY_XXX} "
        "where XXX is the month which starts the financial year, i.e. JAN, FEB, etc.",
        default=str(config.TAX_RULES_UK_INDIVIDUAL),
        type=str.upper,
        dest="tax_rules",
        help="specify tax rules to use, default: UK_INDIVIDUAL",
    )
    parser.add_argument(
        "--skipint",
        dest="skip_integrity",
        action="store_true",
        help="skip integrity check",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="only output the capital gains summary in the tax report",
    )
    parser.add_argument(
        "-o",
        dest="output_filename",
        type=str,
        help="specify the output filename for the tax report",
    )
    parser.add_argument(
        "--nopdf",
        action="store_true",
        help="don't output PDF report, output report to terminal only",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="export your transaction records populated with price data",
    )

    args = parser.parse_args()
    config.debug = args.debug

    if config.debug:
        print("%s%s v%s" % (Fore.YELLOW, parser.prog, __version__))
        print("%spython: v%s" % (Fore.GREEN, platform.python_version()))
        print("%ssystem: %s, release: %s" % (Fore.GREEN, platform.system(), platform.release()))
        config.output_config()

    if args.tax_rules in config.TAX_RULES_UK_COMPANY:
        config.start_of_year_month = config.TAX_RULES_UK_COMPANY.index(args.tax_rules) + 1
        config.start_of_year_day = 1

    try:
        transaction_records = do_import(args.filename)
    except IOError:
        parser.exit(
            "%sERROR%s File could not be read: %s"
            % (Back.RED + Fore.BLACK, Back.RESET + Fore.RED, args.filename)
        )
    except ImportFailureError:
        parser.exit()

    if args.export:
        do_export(transaction_records)
        parser.exit()

    audit = AuditRecords(transaction_records)

    try:
        tax, value_asset = do_tax(transaction_records, args.tax_rules, args.skip_integrity)
        if not args.skip_integrity:
            int_passed = do_integrity_check(audit, tax.holdings)
            if not int_passed:
                parser.exit()

        if not args.summary:
            tax.process_income()

        do_each_tax_year(tax, args.taxyear, args.summary, value_asset)

    except DataSourceError as e:
        parser.exit("%sERROR%s %s" % (Back.RED + Fore.BLACK, Back.RESET + Fore.RED, e))

    if args.nopdf:
        ReportLog(audit, tax.tax_report, value_asset.price_report, tax.holdings_report, args)
    else:
        ReportPdf(
            parser.prog,
            audit,
            tax.tax_report,
            value_asset.price_report,
            tax.holdings_report,
            args,
        )


def validate_year(value):
    year = int(value)
    if year not in CCG.CG_DATA_INDIVIDUAL:
        raise argparse.ArgumentTypeError(
            "tax year %d is not supported, must be in the range (%s-%s)"
            % (year, min(CCG.CG_DATA_INDIVIDUAL), max(CCG.CG_DATA_INDIVIDUAL))
        )

    return year


def do_import(filename):
    import_records = ImportRecords()

    if filename:
        try:
            import_records.import_excel(filename)
        except xlrd.XLRDError:
            with io.open(filename, newline="", encoding="utf-8") as csv_file:
                import_records.import_csv(csv_file)
    else:
        if sys.version_info[0] < 3:
            import_records.import_csv(codecs.getreader("utf-8")(sys.stdin))
        else:
            import_records.import_csv(sys.stdin)

    print(
        "%simport %s (success=%s, failure=%s)"
        % (
            Fore.WHITE,
            "successful" if import_records.failure_cnt <= 0 else "failure",
            import_records.success_cnt,
            import_records.failure_cnt,
        )
    )

    if import_records.failure_cnt > 0:
        raise ImportFailureError

    return import_records.get_records()


def do_tax(transaction_records, tax_rules, skip_integrity_check):
    value_asset = ValueAsset()
    transaction_history = TransactionHistory(transaction_records, value_asset)

    tax = TaxCalculator(transaction_history.transactions, tax_rules)
    tax.pool_same_day()
    tax.match_sell(tax.DISPOSAL_SAME_DAY)

    if tax_rules == config.TAX_RULES_UK_INDIVIDUAL:
        tax.match_buyback(tax.DISPOSAL_BED_AND_BREAKFAST)
    elif tax_rules in config.TAX_RULES_UK_COMPANY:
        tax.match_sell(tax.DISPOSAL_TEN_DAY)

    tax.process_section104(skip_integrity_check)
    return tax, value_asset


def do_integrity_check(audit, holdings):
    int_passed = True

    if config.transfers_include:
        transfer_mismatch = transfer_mismatches(holdings)
    else:
        transfer_mismatch = False

    pools_match = audit.compare_pools(holdings)

    if not pools_match or transfer_mismatch:
        int_passed = False

    print(
        "%sintegrity check: %s%s" % (Fore.CYAN, Fore.YELLOW, "passed" if int_passed else "failed")
    )

    if transfer_mismatch:
        print(
            "%sWARNING%s Integrity check failed: disposal(s) detected during transfer, "
            "turn on logging [-d] to see transactions"
            % (Back.YELLOW + Fore.BLACK, Back.RESET + Fore.YELLOW)
        )
    elif not pools_match:
        if not config.transfers_include:
            print(
                "%sWARNING%s Integrity check failed: audit does not match section 104 pools, "
                "please check Withdrawals and Deposits for missing fees"
                % (Back.YELLOW + Fore.BLACK, Back.RESET + Fore.YELLOW)
            )
        else:
            print(
                "%sERROR%s Integrity check failed: audit does not match section 104 pools"
                % (Back.RED + Fore.BLACK, Back.RESET + Fore.RED)
            )
        audit.report_failures()
    return int_passed


def transfer_mismatches(holdings):
    return bool([asset for asset in holdings if holdings[asset].mismatches])


def do_each_tax_year(tax, tax_year, summary, value_asset):
    if tax_year:
        print("%scalculating tax year %s" % (Fore.CYAN, config.format_tax_year(tax_year)))

        tax.calculate_capital_gains(tax_year)
        if not summary:
            tax.calculate_income(tax_year)
    else:
        # Calculate for all years
        for year in sorted(tax.tax_events):
            print("%scalculating tax year %s" % (Fore.CYAN, config.format_tax_year(year)))

            if year in CCG.CG_DATA_INDIVIDUAL:
                tax.calculate_capital_gains(year)
                if not summary:
                    tax.calculate_income(year)
            else:
                print(
                    "%sWARNING%s Tax year %s is not supported"
                    % (Back.YELLOW + Fore.BLACK, Back.RESET + Fore.YELLOW, year)
                )

        if not summary:
            tax.calculate_holdings(value_asset)

    return tax, value_asset


def do_export(transaction_records):
    value_asset = ValueAsset()
    TransactionHistory(transaction_records, value_asset)
    ExportRecords(transaction_records).write_csv()
