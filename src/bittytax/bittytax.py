# -*- coding: utf-8 -*-
# Cryptocurrency tax calculator for UK tax rules
# (c) Nano Nano Ltd 2019

import argparse
import io
import os
import platform
import sys
from typing import Dict, List, Tuple

import colorama
from colorama import Fore

from .audit import AuditRecords
from .bt_types import AssetSymbol, DisposalType, Year
from .config import config
from .constants import ERROR, TAX_RULES_UK_COMPANY, TAX_RULES_UK_INDIVIDUAL, WARNING
from .exceptions import ImportFailureError
from .export_records import ExportRecords
from .holdings import Holdings
from .import_records import ImportRecords
from .price.exceptions import DataSourceError
from .price.valueasset import ValueAsset
from .record import TransactionRecord
from .report import ReportLog, ReportPdf
from .tax import CalculateCapitalGains as CCG
from .tax import TaxCalculator
from .transactions import TransactionHistory
from .version import __version__

if sys.stdout.encoding != "UTF-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]


def main() -> None:
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
        version=f"{parser.prog} v{__version__}",
    )
    parser.add_argument("-d", "--debug", action="store_true", help="enable debug logging")
    parser.add_argument(
        "-ty",
        "--taxyear",
        type=_validate_year,
        dest="tax_year",
        help=(
            f"tax year must be in the range "
            f"({min(CCG.CG_DATA_INDIVIDUAL)}-{max(CCG.CG_DATA_INDIVIDUAL)})"
        ),
    )
    parser.add_argument(
        "--taxrules",
        choices=[TAX_RULES_UK_INDIVIDUAL] + TAX_RULES_UK_COMPANY,
        metavar="{UK_INDIVIDUAL, UK_COMPANY_XXX} "
        "where XXX is the month which starts the financial year, i.e. JAN, FEB, etc.",
        default=TAX_RULES_UK_INDIVIDUAL,
        type=str.upper,
        dest="tax_rules",
        help="specify tax rules to use, default: UK_INDIVIDUAL",
    )
    parser.add_argument(
        "--audit",
        dest="audit_only",
        action="store_true",
        help="audit only",
    )
    parser.add_argument(
        "--skipint",
        dest="skip_integrity",
        action="store_true",
        help="skip integrity check",
    )
    parser.add_argument(
        "--summary",
        dest="summary_only",
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
        print(f"{Fore.YELLOW}{parser.prog} v{__version__}")
        print(f"{Fore.GREEN}python: v{platform.python_version()}")
        print(f"{Fore.GREEN}system: {platform.system()}, release: {platform.release()}")
        config.output_config(sys.stdout)

    if args.tax_rules in TAX_RULES_UK_COMPANY:
        config.start_of_year_month = TAX_RULES_UK_COMPANY.index(args.tax_rules) + 1
        config.start_of_year_day = 1

    try:
        transaction_records = _do_import(args.filename)
    except IOError:
        parser.exit(message=f"{ERROR} File could not be read: {args.filename}\n")
    except ImportFailureError:
        parser.exit()

    if args.export:
        _do_export(transaction_records)
        parser.exit()

    audit = AuditRecords(transaction_records)

    if args.audit_only:
        if args.nopdf:
            ReportLog(args, audit)
        else:
            ReportPdf(parser.prog, args, audit)
    else:
        try:
            tax, value_asset = _do_tax(transaction_records, args.tax_rules, args.skip_integrity)
            if not args.skip_integrity:
                int_passed = _do_integrity_check(audit, tax.holdings)
                if not int_passed:
                    parser.exit()

            if not args.summary_only:
                tax.process_income()
                tax.process_margin_trades()

            _do_each_tax_year(tax, args.tax_year, args.summary_only, value_asset)

        except DataSourceError as e:
            parser.exit(message=f"{ERROR} {e}\n")

        if args.nopdf:
            ReportLog(args, audit, tax.tax_report, value_asset.price_report, tax.holdings_report)
        else:
            ReportPdf(
                parser.prog,
                args,
                audit,
                tax.tax_report,
                value_asset.price_report,
                tax.holdings_report,
            )


def _validate_year(value: str) -> int:
    year = int(value)
    if year not in CCG.CG_DATA_INDIVIDUAL:
        raise argparse.ArgumentTypeError(
            f"tax year {year} is not supported, must be in the range "
            f"({min(CCG.CG_DATA_INDIVIDUAL)}-{max(CCG.CG_DATA_INDIVIDUAL)})",
        )

    return year


def _do_import(filename: str) -> List[TransactionRecord]:
    import_records = ImportRecords()

    if filename:
        _, file_extension = os.path.splitext(filename)
        if file_extension == ".xlsx":
            import_records.import_excel_xlsx(filename)
        elif file_extension == ".xls":
            import_records.import_excel_xls(filename)
        else:
            with io.open(filename, newline="", encoding="utf-8") as csv_file:
                import_records.import_csv(csv_file)
    else:
        import_records.import_csv(sys.stdin)

    print(
        f"{Fore.WHITE}import {'successful' if import_records.failure_cnt <= 0 else 'failure'} "
        f"(success={import_records.success_cnt}, failure={import_records.failure_cnt})"
    )

    if import_records.failure_cnt > 0:
        raise ImportFailureError

    return import_records.get_records()


def _do_tax(
    transaction_records: List[TransactionRecord], tax_rules: str, skip_integrity_check: bool
) -> Tuple[TaxCalculator, ValueAsset]:
    value_asset = ValueAsset()
    transaction_history = TransactionHistory(transaction_records, value_asset)

    tax = TaxCalculator(transaction_history.transactions, tax_rules)
    tax.pool_same_day()
    tax.match_sell(DisposalType.SAME_DAY)

    if tax_rules == TAX_RULES_UK_INDIVIDUAL:
        tax.match_buyback(DisposalType.BED_AND_BREAKFAST)
    elif tax_rules in TAX_RULES_UK_COMPANY:
        tax.match_sell(DisposalType.TEN_DAY)

    tax.process_section104(skip_integrity_check)
    return tax, value_asset


def _do_integrity_check(audit: AuditRecords, holdings: Dict[AssetSymbol, Holdings]) -> bool:
    int_passed = True

    if config.transfers_include:
        transfer_mismatch = _transfer_mismatches(holdings)
    else:
        transfer_mismatch = False

    pools_match = audit.compare_pools(holdings)

    if not pools_match or transfer_mismatch:
        int_passed = False

    print(f"{Fore.CYAN}integrity check: {Fore.YELLOW}{'passed' if int_passed else 'failed'}")

    if transfer_mismatch:
        print(
            f"{WARNING} Integrity check failed: disposal(s) detected during transfer, "
            f"turn on logging [-d] to see transactions"
        )
    elif not pools_match:
        if not config.transfers_include:
            print(
                f"{WARNING} Integrity check failed: audit does not match section 104 pools, "
                f"please check Withdrawals and Deposits for missing fees"
            )
        else:
            print(f"{ERROR} Integrity check failed: audit does not match section 104 pools")
        audit.report_failures()
    return int_passed


def _transfer_mismatches(holdings: Dict[AssetSymbol, Holdings]) -> bool:
    return bool([asset for asset in holdings if holdings[asset].mismatches])


def _do_each_tax_year(
    tax: TaxCalculator, tax_year: Year, summary_only: bool, value_asset: ValueAsset
) -> None:
    if tax_year:
        print(f"{Fore.CYAN}calculating tax year {config.format_tax_year(tax_year)}")

        calc_cgt = tax.calculate_capital_gains(tax_year)
        if summary_only:
            tax.tax_report[tax_year] = {"CapitalGains": calc_cgt}
        else:
            calc_income = tax.calculate_income(tax_year)
            calc_margin_trading = tax.calculate_margin_trading(tax_year)
            tax.tax_report[tax_year] = {
                "CapitalGains": calc_cgt,
                "Income": calc_income,
                "MarginTrading": calc_margin_trading,
            }
    else:
        # Calculate for all years
        for year in sorted(tax.tax_events):
            print(f"{Fore.CYAN}calculating tax year {config.format_tax_year(year)}")

            if year in CCG.CG_DATA_INDIVIDUAL:
                calc_cgt = tax.calculate_capital_gains(year)
                if summary_only:
                    tax.tax_report[year] = {"CapitalGains": calc_cgt}
                else:
                    calc_income = tax.calculate_income(year)
                    calc_margin_trading = tax.calculate_margin_trading(year)
                    tax.tax_report[year] = {
                        "CapitalGains": calc_cgt,
                        "Income": calc_income,
                        "MarginTrading": calc_margin_trading,
                    }
            else:
                print(f"{WARNING} Tax year {year} is not supported")

        if not summary_only:
            tax.calculate_holdings(value_asset)


def _do_export(transaction_records: List[TransactionRecord]) -> None:
    value_asset = ValueAsset()
    TransactionHistory(transaction_records, value_asset)
    ExportRecords(transaction_records).write_csv()


if __name__ == "__main__":
    main()
