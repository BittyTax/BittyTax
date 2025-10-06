# -*- coding: utf-8 -*-
# Cryptocurrency tax calculator for US tax rules
# (c) Nano Nano Ltd 2019

import argparse
import builtins
import io
import os
import platform
import sys
from typing import Dict, List, Tuple

import colorama
from colorama import Fore

from .audit import AuditRecords
from .audit_excel import AuditLogExcel
from .bt_types import (
    TAX_RULES_UK_COMPANY,
    TAX_RULES_US_INDIVIDUAL,
    AssetSymbol,
    CostBasisMethod,
    TaxRules,
    Year,
)
from .config import config
from .constants import (
    ACCT_FORMAT_EXCEL,
    ACCT_FORMAT_IRS,
    ACCT_FORMAT_PDF,
    ACCT_FORMAT_TAXACT,
    ACCT_FORMAT_TURBOTAX_CSV,
    ACCT_FORMAT_TURBOTAX_TXF,
    ERROR,
    TERMINAL_POWERSHELL_GUI,
    WARNING,
)
from .exceptions import ImportFailureError
from .export_records import ExportRecords
from .holdings import Holdings
from .import_records import ImportRecords
from .output_csv import OutputCapitalGainsCsv, OutputTaxAct, OutputTurboTaxCsv
from .output_irs import OutputIrs
from .output_txf import OutputTurboTaxTxf
from .price.exceptions import DataSourceError
from .price.valueasset import ValueAsset
from .report import ReportLog, ReportPdf
from .report_excel import ReportExcel
from .t_record import TransactionRecord
from .tax import CalculateCapitalGains as CCG
from .tax import TaxCalculator
from .transactions import TransactionHistory
from .utils import bt_print
from .version import __version__

if sys.stdout.encoding != "UTF-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]


def main() -> None:
    if config.terminal == TERMINAL_POWERSHELL_GUI:
        colorama.init(strip=False)
        builtins.print = bt_print  # type: ignore[assignment]
    else:
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
        choices=[tax_rules.name for tax_rules in TaxRules],
        metavar="{UK_INDIVIDUAL,US_INDIVIDUAL_FIFO,US_INDIVIDUAL_LIFO,US_INDIVIDUAL_HIFO,"
        "US_INDIVIDUAL_LOFO,UK_COMPANY_XXX} where XXX is the month which starts the financial year"
        ", i.e. JAN, FEB, etc.",
        default=config.default_tax_rules,
        type=str.upper,
        dest="tax_rules",
        help=f"specify tax rules to use, default: {config.default_tax_rules}",
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
        help="specify the output filename for the PDF report",
    )
    parser.add_argument(
        "--format",
        choices=[
            ACCT_FORMAT_PDF,
            ACCT_FORMAT_EXCEL,
            ACCT_FORMAT_IRS,
            ACCT_FORMAT_TURBOTAX_CSV,
            ACCT_FORMAT_TURBOTAX_TXF,
            ACCT_FORMAT_TAXACT,
        ],
        default=ACCT_FORMAT_PDF,
        type=str.upper,
        help="specify the output format, default: PDF",
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
    try:
        args.tax_rules = TaxRules[args.tax_rules]
    except KeyError as e:
        if args.tax_rules == config.default_tax_rules:
            parser.error(
                f'Unrecognised --taxrules option "{args.tax_rules}" '
                f"used in {config.BITTYTAX_CONFIG} file\n"
            )
        else:
            raise RuntimeError(f"Unrecognised args.tax_rules: {args.tax_rules}") from e

    config.debug = args.debug

    if config.debug:
        print(f"{Fore.YELLOW}{parser.prog} v{__version__}")
        print(f"{Fore.GREEN}python: v{platform.python_version()}")
        print(f"{Fore.GREEN}system: {platform.system()}, release: {platform.release()}")
        for arg in vars(args):
            print(f"{Fore.GREEN}args: {arg}: {getattr(args, arg)}")
        config.output_config(sys.stdout)

    if args.tax_rules not in TAX_RULES_US_INDIVIDUAL:
        parser.exit(message=f"{ERROR} {args.tax_rules} not supported in this version\n")

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
        if audit.audit_log:
            audit_log_excel = AuditLogExcel(parser.prog, audit.audit_log)
            audit_log_excel.write_excel()

        if args.nopdf:
            ReportLog(args, audit)
        else:
            if args.format == ACCT_FORMAT_EXCEL:
                ReportExcel(parser.prog, args, audit)
            else:
                ReportPdf(parser.prog, args, audit)
    else:
        try:
            tax, value_asset = _do_tax(transaction_records, args.tax_rules)
            if tax.match_missing:
                parser.exit(
                    message=f"{ERROR} Unmatched disposal(s) detected, "
                    f"turn on logging [-d] to see transactions\n"
                )

            if not args.skip_integrity:
                int_passed = _do_integrity_check(audit, tax.holdings_per_asset)
                if not int_passed:
                    print(f"{Fore.RESET}Do you want to continue? [y/N] ", end="")
                    if input() != "y":
                        parser.exit()

            _do_each_tax_year(tax, args.tax_year, args.summary_only, value_asset)

        except DataSourceError as e:
            parser.exit(message=f"{ERROR} {e}\n")

        if args.nopdf:
            ReportLog(args, audit, tax.tax_report, value_asset.price_report, tax.holdings_report)
        else:
            if args.format == ACCT_FORMAT_PDF:
                ReportPdf(
                    parser.prog,
                    args,
                    audit,
                    tax.tax_report,
                    value_asset.price_report,
                    tax.holdings_report,
                )
            elif args.format == ACCT_FORMAT_EXCEL:
                ReportExcel(
                    parser.prog,
                    args,
                    audit,
                    tax.buy_list,
                    tax.sells_ordered,
                    tax.other_transactions,
                    tax.tax_report,
                    value_asset.price_report,
                    tax.holdings_report,
                )
            elif args.format == ACCT_FORMAT_IRS:
                output_pdf = OutputIrs(args.output_filename, tax.tax_report)
                output_pdf.write_pdf()
            elif args.format == ACCT_FORMAT_TURBOTAX_CSV:
                output_csv: OutputCapitalGainsCsv = OutputTurboTaxCsv(
                    args.output_filename, tax.tax_report
                )
                output_csv.write_csv()
            elif args.format == ACCT_FORMAT_TURBOTAX_TXF:
                output_txf = OutputTurboTaxTxf(args.output_filename, tax.tax_report)
                output_txf.write_txf()
            elif args.format == ACCT_FORMAT_TAXACT:
                output_csv = OutputTaxAct(args.output_filename, tax.tax_report)
                output_csv.write_csv()


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
                import_records.import_csv(csv_file, filename)
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
    transaction_records: List[TransactionRecord], tax_rules: TaxRules
) -> Tuple[TaxCalculator, ValueAsset]:
    value_asset = ValueAsset()
    transaction_history = TransactionHistory(transaction_records, value_asset)

    tax = TaxCalculator(transaction_history.transactions, tax_rules)
    # Important - process income and margin trades before splitting
    tax.process_income()
    tax.process_margin_trades()

    tax.order_transactions()
    if tax_rules is TaxRules.US_INDIVIDUAL_FIFO:
        tax.match_transactions(CostBasisMethod.FIFO)
    elif tax_rules is TaxRules.US_INDIVIDUAL_LIFO:
        tax.match_transactions(CostBasisMethod.LIFO)
    elif tax_rules is TaxRules.US_INDIVIDUAL_HIFO:
        tax.match_transactions(CostBasisMethod.HIFO)
    elif tax_rules is TaxRules.US_INDIVIDUAL_LOFO:
        tax.match_transactions(CostBasisMethod.LOFO)
    else:
        raise RuntimeError(f"Unexpected tax_rules: {tax_rules}")

    if not tax.match_missing:
        tax.process_holdings()

    return tax, value_asset


def _do_integrity_check(audit: AuditRecords, holdings: Dict[AssetSymbol, Holdings]) -> bool:
    int_passed = True

    if config.transfers_include:
        transfer_mismatch = _transfer_mismatches(holdings)
    else:
        transfer_mismatch = False

    pools_match = audit.compare_holdings(holdings)

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
                f"{WARNING} Integrity check failed: audit does not match holdings, "
                f"please check Withdrawals and Deposits are correct, and have correct fees"
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
