# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import argparse
import os
import platform
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

import xlsxwriter
from colorama import Fore

from .audit import AuditRecords, AuditTotals
from .bt_types import AssetSymbol, Date, Wallet, Year
from .config import config
from .constants import ACQUISITIONS_VARIOUS, EXCEL_PRECISION, PROJECT_URL
from .price.valueasset import VaPriceReport
from .report import ProgressSpinner
from .tax import (
    CalculateCapitalGains,
    CalculateIncome,
    CalculateMarginTrading,
    HoldingsReportRecord,
    TaxReportRecord,
)
from .tax_event import TaxEventCapitalGains
from .version import __version__

if platform.system() == "Darwin":
    # Default size for MacOS
    FONT_SIZE = 12
else:
    FONT_SIZE = 11


@dataclass
class WorkbookFormats:  # pylint: disable=too-many-instance-attributes
    quantity: xlsxwriter.worksheet.Format
    date: xlsxwriter.worksheet.Format
    string_left: xlsxwriter.worksheet.Format
    string_right: xlsxwriter.worksheet.Format
    currency: xlsxwriter.worksheet.Format
    currency_bold: xlsxwriter.worksheet.Format
    num_float: xlsxwriter.worksheet.Format
    num_float_red: xlsxwriter.worksheet.Format
    num_float_red_signed: xlsxwriter.worksheet.Format
    num_string: xlsxwriter.worksheet.Format
    num_string_red: xlsxwriter.worksheet.Format
    num_int: xlsxwriter.worksheet.Format
    num_int_signed: xlsxwriter.worksheet.Format
    bold: xlsxwriter.worksheet.Format
    title: xlsxwriter.worksheet.Format
    header: xlsxwriter.worksheet.Format


class ReportExcel:  # pylint: disable=too-few-public-methods
    AUDIT_FILENAME = "BittyTax_Audit_Report"
    TAX_SUMMARY_FILENAME = "BittyTax_Summary_Report"
    TAX_FULL_FILENAME = "BittyTax_Report"

    DEFAULT_FILENAME = "BittyTax_Report"
    FILE_EXTENSION = "xlsx"
    TITLE = "BittyTax Report"
    DATE_FORMAT = "mm/dd/yy"

    def __init__(
        self,
        progname: str,
        args: argparse.Namespace,
        audit: AuditRecords,
        tax_report: Optional[Dict[Year, TaxReportRecord]] = None,
        price_report: Optional[Dict[Year, Dict[AssetSymbol, Dict[Date, VaPriceReport]]]] = None,
        holdings_report: Optional[HoldingsReportRecord] = None,
    ) -> None:
        self.progname = progname

        with ProgressSpinner(f"{Fore.CYAN}generating EXCEL report{Fore.GREEN}: "):
            if args.audit_only:
                filename = self.get_output_filename(args.output_filename, self.AUDIT_FILENAME)
                self.workbook = self._create_workbook(filename)
                self.workbook_formats = self._create_formats(self.workbook)
                self._audit(audit)
            elif args.summary_only:
                filename = self.get_output_filename(args.output_filename, self.TAX_SUMMARY_FILENAME)
                self.workbook = self._create_workbook(filename)
                self.workbook_formats = self._create_formats(self.workbook)
                if tax_report is None:
                    raise RuntimeError("Missing tax_report")

                self._tax_summary(tax_report)
            else:
                filename = self.get_output_filename(args.output_filename, self.TAX_FULL_FILENAME)
                self.workbook = self._create_workbook(filename)
                self.workbook_formats = self._create_formats(self.workbook)
                if tax_report is None:
                    raise RuntimeError("Missing tax_report")

                if price_report is None:
                    raise RuntimeError("Missing price_report")

                self._tax_full(audit, tax_report, price_report, holdings_report)
            self.workbook.close()

        print(f"{Fore.WHITE}EXCEL report created: {Fore.YELLOW}{os.path.abspath(filename)}")

    def _create_workbook(self, filename: str) -> xlsxwriter.Workbook:
        workbook = xlsxwriter.Workbook(filename)
        workbook.set_size(1800, 1200)
        workbook.formats[0].set_font_size(FONT_SIZE)
        workbook.set_properties(
            {
                "title": self.TITLE,
                "author": f"{self.progname} v{__version__}",
                "comments": PROJECT_URL,
            }
        )
        return workbook

    def _create_formats(self, workbook: xlsxwriter.Workbook) -> WorkbookFormats:
        workbook_formats = WorkbookFormats(
            quantity=workbook.add_format(
                {"font_size": FONT_SIZE, "font_color": "black", "num_format": "#,##0." + "#" * 30}
            ),
            date=workbook.add_format(
                {"font_size": FONT_SIZE, "font_color": "black", "num_format": self.DATE_FORMAT}
            ),
            string_left=workbook.add_format({"font_size": FONT_SIZE, "underline": True}),
            string_right=workbook.add_format(
                {"font_size": FONT_SIZE, "font_color": "black", "align": "right"}
            ),
            currency=workbook.add_format(
                {
                    "font_size": FONT_SIZE,
                    "font_color": "black",
                    "num_format": '"'
                    + config.sym()
                    + '"#,##0.00_);[Red]("'
                    + config.sym()
                    + '"#,##0.00)',
                }
            ),
            currency_bold=workbook.add_format(
                {
                    "font_size": FONT_SIZE,
                    "font_color": "black",
                    "bold": True,
                    "num_format": '"'
                    + config.sym()
                    + '"#,##0.00_);[Red]("'
                    + config.sym()
                    + '"#,##0.00)',
                }
            ),
            num_float=workbook.add_format(
                {"font_size": FONT_SIZE, "font_color": "black", "num_format": "#,##0." + "#" * 30}
            ),
            num_float_red=workbook.add_format(
                {"font_size": FONT_SIZE, "font_color": "red", "num_format": "#,##0." + "#" * 30}
            ),
            num_float_red_signed=workbook.add_format(
                {
                    "font_size": FONT_SIZE,
                    "font_color": "red",
                    "num_format": "+#,##0." + "#" * 30 + ";-#,##0." + "#" * 30 + ";0",
                }
            ),
            num_string=workbook.add_format(
                {"font_size": FONT_SIZE, "font_color": "black", "align": "right"}
            ),
            num_string_red=workbook.add_format(
                {"font_size": FONT_SIZE, "font_color": "red", "align": "right"}
            ),
            num_int=workbook.add_format({"num_format": "#,##0"}),
            num_int_signed=workbook.add_format({"num_format": "+#,##0;-#,##0;0"}),
            bold=workbook.add_format({"font_size": FONT_SIZE, "bold": True}),
            title=workbook.add_format(
                {"font_size": 16, "font_color": "black", "font_name": "Helvetica"}
            ),
            header=workbook.add_format(
                {
                    "font_size": FONT_SIZE,
                    "font_color": "white",
                    "bold": True,
                    "bg_color": "black",
                    "border": 1,
                    "border_color": "white",
                }
            ),
        )
        return workbook_formats

    def _audit(self, audit: AuditRecords) -> None:
        worksheet = Worksheet(self.workbook, self.workbook_formats, "Audit")
        worksheet.audit_by_wallet("Audit - Wallet Balances", audit.wallets, "Audit_Wallet")
        worksheet.audit_by_crypto(
            "Audit - Asset Balances - Cryptoassets",
            self.audit_totals_filter(audit.totals),
            "Audit_Asset_Crypto",
        )
        worksheet.audit_by_fiat(
            "Audit - Asset Balances - Fiat",
            self.audit_totals_filter(audit.totals, fiat_only=True),
            "Audit_Asset_Fiat",
        )
        worksheet.worksheet.autofit()

    def _tax_summary(self, tax_report: Dict[Year, TaxReportRecord]) -> None:
        for tax_year in sorted(tax_report):
            tax_year_table_str = config.format_tax_year(tax_year).replace("/", "_")

            worksheet = Worksheet(
                self.workbook,
                self.workbook_formats,
                f"Tax Year {config.format_tax_year(tax_year)}",
            )
            worksheet.capital_gains(
                "Capital Gains - Short Term",
                tax_report[tax_year]["CapitalGains"].short_term,
                f"Tax_Year_{tax_year_table_str}_Capital_Gains_Short_Term",
            )
            worksheet.capital_gains(
                "Capital Gains - Long Term",
                tax_report[tax_year]["CapitalGains"].long_term,
                f"Tax_Year_{tax_year_table_str}_Capital_Gains_Long_Term",
            )
            worksheet.no_gain_no_loss(
                "Non-Taxable Transactions",
                tax_report[tax_year]["CapitalGains"],
                f"Tax_Year_{tax_year_table_str}_Non_Taxable_Transactions",
            )
            worksheet.income_by_asset(
                "Income - by Asset",
                tax_report[tax_year]["Income"],
                f"Tax_Year_{tax_year_table_str}_Income_Asset",
            )
            worksheet.income_by_type(
                "Income - by Type",
                tax_report[tax_year]["Income"],
                f"Tax_Year_{tax_year_table_str}_Income_Type",
            )
            worksheet.margin_trading(
                "Margin Trading",
                tax_report[tax_year]["MarginTrading"],
                f"Tax_Year_{tax_year_table_str}_Margin_Trading",
            )
            worksheet.worksheet.autofit()

    def _tax_full(
        self,
        audit: AuditRecords,
        tax_report: Dict[Year, TaxReportRecord],
        price_report: Dict[Year, Dict[AssetSymbol, Dict[Date, VaPriceReport]]],
        holdings_report: Optional[HoldingsReportRecord],
    ) -> None:
        self._audit(audit)
        self._tax_summary(tax_report)

        worksheet = Worksheet(self.workbook, self.workbook_formats, "Price Data")
        worksheet.price_data("Price Data", price_report, "Price_Data")
        worksheet.worksheet.autofit()
        if holdings_report:
            worksheet = Worksheet(self.workbook, self.workbook_formats, "Current Holdings")
            worksheet.holdings("Current Holdings", holdings_report, "Holdings")
        worksheet.worksheet.autofit()

    @staticmethod
    def get_output_filename(filename: str, default_filename: str) -> str:
        if filename:
            filepath, file_extension = os.path.splitext(filename)
            if file_extension != ReportExcel.FILE_EXTENSION:
                filepath = filepath + "." + ReportExcel.FILE_EXTENSION
        else:
            filepath = default_filename + "." + ReportExcel.FILE_EXTENSION

        if not os.path.exists(filepath):
            return filepath

        filepath, file_extension = os.path.splitext(filepath)
        i = 2
        new_fname = f"{filepath}-{i}{file_extension}"
        while os.path.exists(new_fname):
            i += 1
            new_fname = f"{filepath}-{i}{file_extension}"
        return new_fname

    @staticmethod
    def audit_totals_filter(
        audit_totals: Dict[AssetSymbol, AuditTotals], fiat_only: bool = False
    ) -> Dict[AssetSymbol, AuditTotals]:
        filtered_totals: Dict[AssetSymbol, AuditTotals] = {}

        for asset in audit_totals:
            if config.audit_hide_empty:
                if not audit_totals[asset].total and not audit_totals[asset].transfers_mismatch:
                    continue

            if fiat_only and asset not in config.fiat_list:
                continue
            if not fiat_only and asset in config.fiat_list:
                continue

            filtered_totals[asset] = audit_totals[asset]

        return filtered_totals


class Worksheet:
    SHEETNAME_MAX_LEN = 31
    MAX_COL_WIDTH = 30
    TABLE_STYLE = "Table Style Medium 9"

    AUD_WALLET_HEADERS = ["Wallet", "Asset", "Balance"]
    AUD_CRYPTO_HEADERS = ["Asset", "Balance", "Transfers Mismatch"]
    AUD_FIAT_HEADERS = ["Asset", "Balance"]
    CG_HEADERS = [
        "Asset",
        "Quantity",
        "Date Acquired",
        "Date Sold",
        "Proceeds",
        "Cost Basis",
        "Gain or (Loss)",
    ]
    IN_ASSET_HEADERS = [
        "Asset",
        "Quantity",
        "Description",
        "Date Acquired",
        "Income Type",
        "Market Value",
        "Fees",
    ]
    IN_TYPE_HEADERS = [
        "Income Type",
        "Asset",
        "Quantity",
        "Description",
        "Date Acquired",
        "Market Value",
        "Fees",
    ]
    NON_TAX_HEADERS = [
        "Asset",
        "Quantity",
        "Description",
        "Date Disposed",
        "Disposal Type",
        "Market Value",
        "Cost Basis",
    ]
    MARGIN_HEADERS = [
        "Wallet",
        "Contract",
        "Date",
        "Gains",
        "Losses",
        "Fees",
    ]
    PRICE_HEADERS = [
        "Asset Symbol",
        "Asset Name",
        "Data Source",
        "Date",
        "Tax Year",
        f"Price ({config.ccy})",
        "Price (BTC)",
    ]
    HOLDINGS_HEADERS = [
        "Asset Symbol",
        "Asset Name",
        "Quantity",
        "Cost Basis",
        "Market Value",
        "Gain or (Loss)",
    ]

    def __init__(
        self, workbook: xlsxwriter.Workbook, workbook_formats: WorkbookFormats, worksheet_name: str
    ) -> None:
        self.workbook = workbook
        self.workbook_formats = workbook_formats
        self.row_num = 0
        self.worksheet = self.workbook.add_worksheet(worksheet_name)
        self.worksheet.set_comments_author("BittyTax")

    def _get_columns(self, headers: List[str]) -> List[Dict[str, str]]:
        return [
            {"header": header, "header_format": self.workbook_formats.header} for header in headers
        ]

    def audit_by_wallet(
        self, title: str, audit_wallets: Dict[Wallet, Dict[AssetSymbol, Decimal]], table_name: str
    ) -> None:
        self.worksheet.merge_range(
            self.row_num, 0, self.row_num, 2, title, self.workbook_formats.title
        )
        self.row_num += 1
        start_row = self.row_num

        for wallet in sorted(audit_wallets, key=str.lower):
            for asset in sorted(audit_wallets[wallet], key=str.lower):
                self.row_num += 1
                self.worksheet.write_string(self.row_num, 0, wallet)
                self.worksheet.write_string(self.row_num, 1, asset)
                self._xl_balance(self.row_num, 2, audit_wallets[wallet][asset])

        if start_row == self.row_num:
            # Add blank row if table is empty
            self.row_num += 1

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            2,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.AUD_WALLET_HEADERS),
                "name": table_name,
            },
        )
        self.row_num += 1

    def audit_by_crypto(
        self, title: str, audit_totals: Dict[AssetSymbol, AuditTotals], table_name: str
    ) -> None:
        self.worksheet.merge_range(
            self.row_num, 0, self.row_num, 2, title, self.workbook_formats.title
        )
        self.row_num += 1
        start_row = self.row_num

        for asset in sorted(audit_totals, key=str.lower):
            self.row_num += 1
            self.worksheet.write_string(self.row_num, 0, asset)
            self._xl_balance(self.row_num, 1, audit_totals[asset].total)
            self._xl_mismatch(self.row_num, 2, audit_totals[asset].transfers_mismatch)

        if start_row == self.row_num:
            # Add blank row if table is empty
            self.row_num += 1

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            2,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.AUD_CRYPTO_HEADERS),
                "name": table_name,
            },
        )
        self.row_num += 1

    def audit_by_fiat(
        self, title: str, audit_totals: Dict[AssetSymbol, AuditTotals], table_name: str
    ) -> None:
        self.worksheet.merge_range(
            self.row_num, 0, self.row_num, 1, title, self.workbook_formats.title
        )
        self.row_num += 1
        start_row = self.row_num

        for asset in sorted(audit_totals):
            self.row_num += 1
            self.worksheet.write_string(self.row_num, 0, asset)
            self._xl_balance(self.row_num, 1, audit_totals[asset].total)

        if start_row == self.row_num:
            # Add blank row if table is empty
            self.row_num += 1

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            1,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.AUD_FIAT_HEADERS),
                "name": table_name,
            },
        )
        self.row_num += 1

    def _xl_balance(self, row_num: int, col_num: int, balance: Decimal) -> None:
        if len(balance.normalize().as_tuple().digits) > EXCEL_PRECISION:
            if balance < 0:
                wb_format = self.workbook_formats.num_string_red
            else:
                wb_format = self.workbook_formats.num_string

            self.worksheet.write_string(row_num, col_num, f"{balance.normalize():0,f}", wb_format)
        else:
            if balance < 0:
                wb_format = self.workbook_formats.num_float_red
            else:
                wb_format = self.workbook_formats.num_float

            self.worksheet.write_number(row_num, col_num, balance.normalize(), wb_format)
            cell = xlsxwriter.utility.xl_rowcol_to_cell(row_num, col_num)

            if not config.large_data:
                # Lots of conditional formatting can slow down Excel
                self.worksheet.conditional_format(
                    row_num,
                    col_num,
                    row_num,
                    col_num,
                    {
                        "type": "formula",
                        "criteria": f"=INT({cell})={cell}",
                        "format": self.workbook_formats.num_int,
                    },
                )

    def _xl_mismatch(self, row_num: int, col_num: int, mismatch: Decimal) -> None:
        if not mismatch:
            return

        if len(mismatch.normalize().as_tuple().digits) > EXCEL_PRECISION:
            if mismatch > 0:
                mismatch_str = f"+{mismatch.normalize():0,f}"
            else:
                mismatch_str = f"{mismatch.normalize():0,f}"

            self.worksheet.write_string(
                row_num, col_num, mismatch_str, self.workbook_formats.num_string_red
            )
        else:
            self.worksheet.write_number(
                row_num, col_num, mismatch.normalize(), self.workbook_formats.num_float_red_signed
            )
            cell = xlsxwriter.utility.xl_rowcol_to_cell(row_num, col_num)

            if not config.large_data:
                # Lots of conditional formatting can slow down Excel
                self.worksheet.conditional_format(
                    row_num,
                    col_num,
                    row_num,
                    col_num,
                    {
                        "type": "formula",
                        "criteria": f"=INT({cell})={cell}",
                        "format": self.workbook_formats.num_int_signed,
                    },
                )

    def capital_gains(
        self,
        title: str,
        cgains: Dict[AssetSymbol, List[TaxEventCapitalGains]],
        table_name: str,
    ) -> None:
        self.worksheet.merge_range(
            self.row_num, 0, self.row_num, 6, title, self.workbook_formats.title
        )
        self.row_num += 1
        start_row = self.row_num
        end_a_row = None

        self.row_num += 1

        for asset in sorted(cgains, key=str.lower):
            start_a_row = self.row_num
            for te in cgains[asset]:
                self.worksheet.write_string(self.row_num, 0, te.asset)
                self.worksheet.write_number(
                    self.row_num, 1, te.quantity.normalize(), self.workbook_formats.quantity
                )
                if te.acquisition_dates:
                    if len(te.acquisition_dates) > 1 and not all(
                        date == te.acquisition_dates[0] for date in te.acquisition_dates
                    ):
                        self.worksheet.write_string(
                            self.row_num,
                            2,
                            ACQUISITIONS_VARIOUS,
                            self.workbook_formats.string_right,
                        )
                        self.worksheet.write_comment(
                            self.row_num,
                            2,
                            ", ".join([f"{d:%m/%d/%Y}" for d in sorted(set(te.acquisition_dates))]),
                            {"font_size": 11, "x_scale": 2},
                        )
                    else:
                        self.worksheet.write_datetime(
                            self.row_num, 2, te.acquisition_dates[0], self.workbook_formats.date
                        )
                self.worksheet.write_datetime(self.row_num, 3, te.date, self.workbook_formats.date)
                self.worksheet.write_number(
                    self.row_num, 4, te.proceeds, self.workbook_formats.currency
                )
                self.worksheet.write_number(
                    self.row_num, 5, te.cost, self.workbook_formats.currency
                )
                self.worksheet.write_number(
                    self.row_num, 6, te.gain, self.workbook_formats.currency
                )
                self.worksheet.set_row(self.row_num, None, None, {"level": 2, "hidden": True})
                end_a_row = self.row_num
                self.row_num += 1

            self.worksheet.write_string(
                self.row_num, 0, f"{asset} Total", self.workbook_formats.bold
            )
            # Subtotal Quantity
            self.worksheet.write_formula(
                self.row_num,
                1,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_a_row, 1, end_a_row, 1)})",
                self.workbook_formats.quantity,
            )
            # Subtotal Proceeds
            self.worksheet.write_formula(
                self.row_num,
                4,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_a_row, 4, end_a_row, 4)})",
                self.workbook_formats.currency,
            )
            # Subtotal Cost
            self.worksheet.write_formula(
                self.row_num,
                5,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_a_row, 5, end_a_row, 5)})",
                self.workbook_formats.currency,
            )
            # Subtotal Gain/Loss
            self.worksheet.write_formula(
                self.row_num,
                6,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_a_row, 6, end_a_row, 6)})",
                self.workbook_formats.currency,
            )
            self.worksheet.set_row(self.row_num, None, None, {"level": 1, "collapsed": True})
            self.row_num += 1

        self.worksheet.write_string(self.row_num, 0, "Grand Total", self.workbook_formats.bold)

        if end_a_row is not None:
            # Grand total Proceeds
            self.worksheet.write_formula(
                self.row_num,
                4,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row, 4, end_a_row, 4)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Cost
            self.worksheet.write_formula(
                self.row_num,
                5,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row, 5, end_a_row, 5)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Gain/Loss
            self.worksheet.write_formula(
                self.row_num,
                6,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row, 6, end_a_row, 6)})",
                self.workbook_formats.currency_bold,
            )
        else:
            self.worksheet.write_number(self.row_num, 4, 0, self.workbook_formats.currency_bold)
            self.worksheet.write_number(self.row_num, 5, 0, self.workbook_formats.currency_bold)
            self.worksheet.write_number(self.row_num, 6, 0, self.workbook_formats.currency_bold)

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            6,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.CG_HEADERS),
                "name": table_name,
            },
        )
        self.row_num += 1

    def income_by_asset(
        self,
        title: str,
        income: CalculateIncome,
        table_name: str,
    ) -> None:
        self.worksheet.merge_range(
            self.row_num, 0, self.row_num, 6, title, self.workbook_formats.title
        )
        self.row_num += 1
        start_row = self.row_num
        end_a_row = None

        self.row_num += 1

        for asset in sorted(income.assets, key=str.lower):
            start_a_row = self.row_num
            for te in income.assets[asset]:
                self.worksheet.write_string(self.row_num, 0, te.asset)
                self.worksheet.write_number(
                    self.row_num, 1, te.quantity.normalize(), self.workbook_formats.quantity
                )
                self.worksheet.write_string(self.row_num, 2, te.note)
                self.worksheet.write_datetime(self.row_num, 3, te.date, self.workbook_formats.date)
                self.worksheet.write_string(self.row_num, 4, te.type.value)
                self.worksheet.write_number(
                    self.row_num, 5, te.amount, self.workbook_formats.currency_bold
                )
                self.worksheet.write_number(
                    self.row_num, 6, te.fees, self.workbook_formats.currency_bold
                )
                self.worksheet.set_row(self.row_num, None, None, {"level": 2, "hidden": True})
                end_a_row = self.row_num
                self.row_num += 1

            self.worksheet.write_string(
                self.row_num, 0, f"{asset} Total", self.workbook_formats.bold
            )
            # Subtotal Quantity
            self.worksheet.write_formula(
                self.row_num,
                1,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_a_row, 1, end_a_row, 1)})",
                self.workbook_formats.quantity,
            )
            # Subtotal Market Value
            self.worksheet.write_formula(
                self.row_num,
                5,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_a_row, 5, end_a_row, 5)})",
                self.workbook_formats.currency,
            )
            # Subtotal Fees
            self.worksheet.write_formula(
                self.row_num,
                6,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_a_row, 6, end_a_row, 6)})",
                self.workbook_formats.currency,
            )
            self.worksheet.set_row(self.row_num, None, None, {"level": 1, "collapsed": True})
            self.row_num += 1

        self.worksheet.write_string(self.row_num, 0, "Grand Total", self.workbook_formats.bold)

        if end_a_row is not None:
            # Grand total Market Value
            self.worksheet.write_formula(
                self.row_num,
                5,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row, 5, end_a_row, 5)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Fees
            self.worksheet.write_formula(
                self.row_num,
                6,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row, 6, end_a_row, 6)})",
                self.workbook_formats.currency_bold,
            )
        else:
            self.worksheet.write_number(self.row_num, 5, 0, self.workbook_formats.currency_bold)
            self.worksheet.write_number(self.row_num, 6, 0, self.workbook_formats.currency_bold)

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            6,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.IN_ASSET_HEADERS),
                "name": table_name,
            },
        )
        self.row_num += 1

    def income_by_type(
        self,
        title: str,
        income: CalculateIncome,
        table_name: str,
    ) -> None:
        self.worksheet.merge_range(
            self.row_num, 0, self.row_num, 6, title, self.workbook_formats.title
        )
        self.row_num += 1
        start_row = self.row_num
        end_a_row = None

        self.row_num += 1

        for t_type in sorted(income.types):
            start_a_row = self.row_num
            for te in income.types[t_type]:
                self.worksheet.write_string(self.row_num, 0, te.type.value)
                self.worksheet.write_string(self.row_num, 1, te.asset)
                self.worksheet.write_number(
                    self.row_num, 2, te.quantity.normalize(), self.workbook_formats.quantity
                )
                self.worksheet.write_string(self.row_num, 3, te.note)
                self.worksheet.write_datetime(self.row_num, 4, te.date, self.workbook_formats.date)
                self.worksheet.write_number(
                    self.row_num, 5, te.amount, self.workbook_formats.currency
                )
                self.worksheet.write_number(
                    self.row_num, 6, te.fees, self.workbook_formats.currency
                )
                self.worksheet.set_row(self.row_num, None, None, {"level": 2, "hidden": True})
                end_a_row = self.row_num
                self.row_num += 1

            self.worksheet.write_string(
                self.row_num, 0, f"{t_type} Total", self.workbook_formats.bold
            )
            # Subtotal Market Value
            self.worksheet.write_formula(
                self.row_num,
                5,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_a_row, 5, end_a_row, 5)})",
                self.workbook_formats.currency,
            )
            # Subtotal Fees
            self.worksheet.write_formula(
                self.row_num,
                6,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_a_row, 6, end_a_row, 6)})",
                self.workbook_formats.currency,
            )
            self.worksheet.set_row(self.row_num, None, None, {"level": 1, "collapsed": True})
            self.row_num += 1

        self.worksheet.write_string(self.row_num, 0, "Grand Total", self.workbook_formats.bold)

        if end_a_row is not None:
            # Grand total Market Value
            self.worksheet.write_formula(
                self.row_num,
                5,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row, 5, end_a_row, 5)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Fees
            self.worksheet.write_formula(
                self.row_num,
                6,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row, 6, end_a_row, 6)})",
                self.workbook_formats.currency_bold,
            )
        else:
            self.worksheet.write_number(self.row_num, 5, 0, self.workbook_formats.currency_bold)
            self.worksheet.write_number(self.row_num, 6, 0, self.workbook_formats.currency_bold)

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            6,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.IN_TYPE_HEADERS),
                "name": table_name,
            },
        )
        self.row_num += 1

    def no_gain_no_loss(
        self,
        title: str,
        cgains: CalculateCapitalGains,
        table_name: str,
    ) -> None:
        if not cgains.non_tax_by_type:
            self.worksheet.merge_range(
                self.row_num, 0, self.row_num, 6, title, self.workbook_formats.title
            )
            self.row_num += 1
            start_row = self.row_num
            self.row_num += 1
            self.worksheet.write_string(self.row_num, 0, "Grand Total", self.workbook_formats.bold)
            self.worksheet.write_number(self.row_num, 5, 0, self.workbook_formats.currency_bold)
            self.worksheet.write_number(self.row_num, 6, 0, self.workbook_formats.currency_bold)
            self.worksheet.add_table(
                start_row,
                0,
                self.row_num,
                6,
                {
                    "style": self.TABLE_STYLE,
                    "columns": self._get_columns(self.NON_TAX_HEADERS),
                    "name": table_name,
                },
            )
            self.row_num += 1
            return

        for t_type in sorted(cgains.non_tax_by_type):
            self.worksheet.merge_range(
                self.row_num, 0, self.row_num, 6, f"{title} - {t_type}", self.workbook_formats.title
            )
            self.row_num += 1
            start_row = self.row_num
            self.row_num += 1
            for te in cgains.non_tax_by_type[t_type]:
                self.worksheet.write_string(self.row_num, 0, te.asset)
                self.worksheet.write_number(
                    self.row_num, 1, te.quantity.normalize(), self.workbook_formats.quantity
                )
                self.worksheet.write_string(self.row_num, 2, te.note)
                self.worksheet.write_datetime(self.row_num, 3, te.date, self.workbook_formats.date)
                self.worksheet.write_string(self.row_num, 4, te.disposal_type.value)
                self.worksheet.write_number(
                    self.row_num, 5, te.market_value, self.workbook_formats.currency
                )
                self.worksheet.write_number(
                    self.row_num, 6, te.cost, self.workbook_formats.currency
                )
                self.worksheet.set_row(self.row_num, None, None, {"level": 1, "hidden": True})
                end_row = self.row_num
                self.row_num += 1

            self.worksheet.write_string(self.row_num, 0, "Grand Total", self.workbook_formats.bold)
            # Grand total Market Value
            self.worksheet.write_formula(
                self.row_num,
                5,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row, 5, end_row, 5)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Cost Basis
            self.worksheet.write_formula(
                self.row_num,
                6,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row, 6, end_row, 6)})",
                self.workbook_formats.currency_bold,
            )
            self.worksheet.add_table(
                start_row,
                0,
                self.row_num,
                6,
                {
                    "style": self.TABLE_STYLE,
                    "columns": self._get_columns(self.NON_TAX_HEADERS),
                    "name": table_name,
                },
            )
            self.row_num += 1

    def margin_trading(
        self,
        title: str,
        margin: CalculateMarginTrading,
        table_name: str,
    ) -> None:
        self.worksheet.merge_range(
            self.row_num, 0, self.row_num, 5, title, self.workbook_formats.title
        )
        self.row_num += 1
        start_row = self.row_num
        end_a_row = None

        self.row_num += 1

        for wallet, note in sorted(
            margin.contracts, key=lambda key: (key[0].lower(), key[1].lower())
        ):
            start_a_row = self.row_num
            for te in margin.contracts[(wallet, note)]:
                self.worksheet.write_string(self.row_num, 0, wallet)
                self.worksheet.write_string(self.row_num, 1, note)
                self.worksheet.write_datetime(self.row_num, 2, te.date, self.workbook_formats.date)
                self.worksheet.write_number(
                    self.row_num, 3, te.gain, self.workbook_formats.currency
                )
                self.worksheet.write_number(
                    self.row_num, 4, te.loss, self.workbook_formats.currency
                )
                self.worksheet.write_number(self.row_num, 5, te.fee, self.workbook_formats.currency)
                self.worksheet.set_row(self.row_num, None, None, {"level": 2, "hidden": True})
                end_a_row = self.row_num
                self.row_num += 1

            self.worksheet.write_string(
                self.row_num, 0, f"{wallet} {note} Total", self.workbook_formats.bold
            )
            # Subtotal Gains
            self.worksheet.write_formula(
                self.row_num,
                3,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_a_row, 3, end_a_row, 3)})",
                self.workbook_formats.currency,
            )
            # Subtotal Losses
            self.worksheet.write_formula(
                self.row_num,
                4,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_a_row, 4, end_a_row, 4)})",
                self.workbook_formats.currency,
            )
            # Subtotal Fees
            self.worksheet.write_formula(
                self.row_num,
                5,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_a_row, 5, end_a_row, 5)})",
                self.workbook_formats.currency,
            )
            self.worksheet.set_row(self.row_num, None, None, {"level": 1, "collapsed": True})
            self.row_num += 1

        self.worksheet.write_string(self.row_num, 0, "Grand Total", self.workbook_formats.bold)

        if end_a_row is not None:
            # Grand total Gains
            self.worksheet.write_formula(
                self.row_num,
                3,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row, 3, end_a_row, 3)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Losses
            self.worksheet.write_formula(
                self.row_num,
                4,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row, 4, end_a_row, 4)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Fees
            self.worksheet.write_formula(
                self.row_num,
                5,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row, 5, end_a_row, 5)})",
                self.workbook_formats.currency_bold,
            )
        else:
            self.worksheet.write_number(self.row_num, 3, 0, self.workbook_formats.currency_bold)
            self.worksheet.write_number(self.row_num, 4, 0, self.workbook_formats.currency_bold)
            self.worksheet.write_number(self.row_num, 5, 0, self.workbook_formats.currency_bold)

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            5,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.MARGIN_HEADERS),
                "name": table_name,
            },
        )
        self.row_num += 1

    def price_data(
        self,
        title: str,
        price_report: Dict[Year, Dict[AssetSymbol, Dict[Date, VaPriceReport]]],
        table_name: str,
    ) -> None:
        self.worksheet.merge_range(
            self.row_num, 0, self.row_num, 6, title, self.workbook_formats.title
        )
        self.row_num += 1
        start_row = self.row_num

        for year in sorted(price_report):
            for asset in sorted(price_report[year], key=str.lower):
                for date in sorted(price_report[year][asset]):
                    self.row_num += 1
                    price_data = price_report[year][asset][date]
                    if price_data["price_ccy"] is not None:
                        self.worksheet.write_string(self.row_num, 0, asset)
                        self.worksheet.write_string(self.row_num, 1, price_data["name"])
                        self.worksheet.write_url(
                            self.row_num,
                            2,
                            price_data["url"],
                            self.workbook_formats.string_left,
                            string=price_data["data_source"],
                        )
                        self.worksheet.write_datetime(
                            self.row_num, 3, date, self.workbook_formats.date
                        )
                        self.worksheet.write_string(
                            self.row_num,
                            4,
                            config.format_tax_year(year),
                            self.workbook_formats.string_right,
                        )
                        self.worksheet.write_number(
                            self.row_num, 5, price_data["price_ccy"], self.workbook_formats.currency
                        )
                        if price_data["price_btc"] is not None:
                            self.worksheet.write_number(
                                self.row_num,
                                6,
                                price_data["price_btc"].normalize(),
                                self.workbook_formats.quantity,
                            )
                        else:
                            self.worksheet.write_string(
                                self.row_num, 6, "N/A", self.workbook_formats.string_right
                            )
                    else:
                        self.worksheet.write_string(self.row_num, 0, asset)
                        self.worksheet.write_string(self.row_num, 1, price_data["name"])
                        self.worksheet.write_datetime(
                            self.row_num, 3, date, self.workbook_formats.date
                        )
                        self.worksheet.write_string(
                            self.row_num,
                            4,
                            config.format_tax_year(year),
                            self.workbook_formats.string_right,
                        )
                        self.worksheet.write_string(
                            self.row_num, 5, "NOT AVAILABLE", self.workbook_formats.string_right
                        )

        if start_row == self.row_num:
            # Add blank row if table is empty
            self.row_num += 1

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            6,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.PRICE_HEADERS),
                "name": table_name,
            },
        )
        self.worksheet.ignore_errors(
            {"number_stored_as_text": xlsxwriter.utility.xl_range(start_row, 4, self.row_num, 4)}
        )
        self.row_num += 1

    def holdings(
        self,
        title: str,
        holdings_report: HoldingsReportRecord,
        table_name: str,
    ) -> None:
        self.worksheet.merge_range(
            self.row_num, 0, self.row_num, 5, title, self.workbook_formats.title
        )
        self.row_num += 1
        start_row = self.row_num

        for h in sorted(holdings_report["holdings"], key=str.lower):
            self.row_num += 1
            holding = holdings_report["holdings"][h]
            self.worksheet.write_string(self.row_num, 0, h)
            self.worksheet.write_string(self.row_num, 1, holding["name"])
            self.worksheet.write_number(
                self.row_num, 2, holding["quantity"].normalize(), self.workbook_formats.quantity
            )
            self.worksheet.write_number(
                self.row_num, 3, holding["cost"], self.workbook_formats.currency
            )
            if holding["value"] is not None:
                self.worksheet.write_number(
                    self.row_num, 4, holding["value"], self.workbook_formats.currency
                )
                self.worksheet.write_number(
                    self.row_num, 5, holding["gain"], self.workbook_formats.currency
                )
            else:
                self.worksheet.write_string(
                    self.row_num, 4, "NOT AVAILABLE", self.workbook_formats.string_right
                )

        if start_row == self.row_num:
            # Add blank row if table is empty
            self.row_num += 1

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            5,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.HOLDINGS_HEADERS),
                "name": table_name,
            },
        )
        self.row_num += 1
