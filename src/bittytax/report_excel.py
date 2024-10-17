# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import argparse
import os
import platform
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union

import xlsxwriter
from colorama import Fore

from .audit import AuditRecords, AuditTotals
from .bt_types import BUY_AND_SELL_TYPES, TRANSFER_TYPES, AssetSymbol, Date, Wallet, Year
from .config import config
from .constants import ACQUISITIONS_VARIOUS, COST_BASIS_ZERO_NOTE, EXCEL_PRECISION, PROJECT_URL
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
from .transactions import Buy, Sell
from .version import __version__

if platform.system() == "Darwin":
    # Default size for MacOS
    FONT_SIZE = 12
else:
    FONT_SIZE = 11

FONT_COLOR_GREY = "#808080"

PRECISION = Decimal("0.00")


@dataclass
class WorkbookFormats:  # pylint: disable=too-many-instance-attributes
    quantity: xlsxwriter.worksheet.Format
    date: xlsxwriter.worksheet.Format
    string_right: xlsxwriter.worksheet.Format
    string_link: xlsxwriter.worksheet.Format
    currency: xlsxwriter.worksheet.Format
    currency_bold: xlsxwriter.worksheet.Format
    currency_fixed: xlsxwriter.worksheet.Format
    currency_link: xlsxwriter.worksheet.Format
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
    grey: xlsxwriter.worksheet.Format
    red: xlsxwriter.worksheet.Format


class ReportExcel:  # pylint: disable=too-few-public-methods
    AUDIT_FILENAME = "BittyTax_Audit_Report"
    TAX_SUMMARY_FILENAME = "BittyTax_Summary_Report"
    TAX_FULL_FILENAME = "BittyTax_Report"

    FILE_EXTENSION = "xlsx"
    TITLE = "BittyTax Report"

    def __init__(
        self,
        progname: str,
        args: argparse.Namespace,
        audit: AuditRecords,
        buys_ordered: Optional[Dict[AssetSymbol, List[Buy]]] = None,
        sells_ordered: Optional[List[Sell]] = None,
        other_transactions: Optional[List[Union[Buy, Sell]]] = None,
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

                if buys_ordered is None:
                    raise RuntimeError("Missing buys_ordered")

                if sells_ordered is None:
                    raise RuntimeError("Missing sells_ordered")

                if other_transactions is None:
                    raise RuntimeError("Missing other_transactions")

                self._tax_full(
                    audit,
                    buys_ordered,
                    sells_ordered,
                    other_transactions,
                    tax_report,
                    price_report,
                    holdings_report,
                )
            self.workbook.close()

        print(f"{Fore.WHITE}EXCEL report created: {Fore.YELLOW}{os.path.abspath(filename)}")

    def _create_workbook(self, filename: str) -> xlsxwriter.Workbook:
        workbook = xlsxwriter.Workbook(filename, {"remove_timezone": True})
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
                {"font_size": FONT_SIZE, "font_color": "black", "num_format": "mm/dd/yy"}
            ),
            string_right=workbook.add_format(
                {"font_size": FONT_SIZE, "font_color": "black", "align": "right"}
            ),
            string_link=workbook.add_format(
                {"font_size": FONT_SIZE, "font_color": "black", "underline": True}
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
            currency_fixed=workbook.add_format(
                {
                    "font_size": FONT_SIZE,
                    "font_color": "black",
                    # "italic": True,
                    "num_format": '"='
                    + config.sym()
                    + '"#,##0.00_);[Red]("='
                    + config.sym()
                    + '"#,##0.00)',
                }
            ),
            currency_link=workbook.add_format(
                {
                    "font_size": FONT_SIZE,
                    "font_color": "black",
                    "underline": True,
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
            grey=workbook.add_format({"font_size": FONT_SIZE, "font_color": FONT_COLOR_GREY}),
            red=workbook.add_format({"font_size": FONT_SIZE, "font_color": "red"}),
        )
        return workbook_formats

    def _audit(self, audit: AuditRecords) -> None:
        worksheet = Worksheet(self.workbook, self.workbook_formats, "Audit")
        worksheet.audit_by_wallet(audit.wallets)
        worksheet.audit_by_crypto(self.audit_totals_filter(audit.totals))
        worksheet.audit_by_fiat(self.audit_totals_filter(audit.totals, fiat_only=True))
        worksheet.worksheet.autofit()

    def _tax_summary(
        self,
        tax_report: Dict[Year, TaxReportRecord],
        row_tracker: Optional["RowTracker"] = None,
    ) -> None:
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
                row_tracker,
            )
            worksheet.capital_gains(
                "Capital Gains - Long Term",
                tax_report[tax_year]["CapitalGains"].long_term,
                f"Tax_Year_{tax_year_table_str}_Capital_Gains_Long_Term",
                row_tracker,
            )
            worksheet.no_gain_no_loss(
                "Non-Taxable Transactions",
                tax_report[tax_year]["CapitalGains"],
                f"Tax_Year_{tax_year_table_str}_Non_Taxable_Transactions",
                row_tracker,
            )
            worksheet.income_by_asset(
                "Income - by Asset",
                tax_report[tax_year]["Income"],
                f"Tax_Year_{tax_year_table_str}_Income_Asset",
                row_tracker,
            )
            worksheet.income_by_type(
                "Income - by Type",
                tax_report[tax_year]["Income"],
                f"Tax_Year_{tax_year_table_str}_Income_Type",
                row_tracker,
            )
            worksheet.margin_trading(
                "Margin Trading",
                tax_report[tax_year]["MarginTrading"],
                f"Tax_Year_{tax_year_table_str}_Margin_Trading",
                row_tracker,
            )
            worksheet.worksheet.autofit()

    def _tax_full(
        self,
        audit: AuditRecords,
        buys_ordered: Dict[AssetSymbol, List[Buy]],
        sells_ordered: List[Sell],
        other_transactions: List[Union[Buy, Sell]],
        tax_report: Dict[Year, TaxReportRecord],
        price_report: Dict[Year, Dict[AssetSymbol, Dict[Date, VaPriceReport]]],
        holdings_report: Optional[HoldingsReportRecord],
    ) -> None:
        row_tracker = RowTracker()

        self._audit(audit)
        buys_worksheet = Worksheet(self.workbook, self.workbook_formats, "Buys")
        sells_worksheet = Worksheet(self.workbook, self.workbook_formats, "Sells")
        price_worksheet = Worksheet(self.workbook, self.workbook_formats, "Price Data")
        price_to_row = price_worksheet.price_data(price_report)
        price_worksheet.worksheet.autofit()

        other_buys = [t for t in other_transactions if isinstance(t, Buy)]
        buys_ordered_flat = [
            b for asset in sorted(buys_ordered, key=str.lower) for b in buys_ordered[asset]
        ]
        buys_worksheet.buys_ordered(
            buys_ordered_flat + sorted(other_buys), row_tracker, price_to_row
        )
        buys_worksheet.worksheet.autofit()

        other_sells = [t for t in other_transactions if isinstance(t, Sell)]
        sells_worksheet.sells_ordered(
            sorted(sells_ordered + other_sells), row_tracker, price_to_row
        )
        sells_worksheet.worksheet.autofit()

        self._tax_summary(tax_report, row_tracker)

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
    BUYS_HEADERS = [
        "Type",
        "Asset",
        "Quantity",
        "Date",
        f"Value ({config.ccy})",
        f"Fee ({config.ccy})",
        "Wallet",
        "Note",
        "TxHash",
        "Category",
        "Matched",
    ]

    SELLS_HEADERS = [
        "Type",
        "Asset",
        "Quantity",
        "Date",
        f"Value ({config.ccy})",
        f"Fee ({config.ccy})",
        "Wallet",
        "Note",
        "TxHash",
        "Category",
        "Matched",
    ]

    def __init__(
        self,
        workbook: xlsxwriter.Workbook,
        workbook_formats: WorkbookFormats,
        worksheet_name: str,
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

    def audit_by_wallet(self, audit_wallets: Dict[Wallet, Dict[AssetSymbol, Decimal]]) -> None:
        self.worksheet.merge_range(
            self.row_num,
            0,
            self.row_num,
            len(self.AUD_WALLET_HEADERS) - 1,
            "Audit - Wallet Balances",
            self.workbook_formats.title,
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
            len(self.AUD_WALLET_HEADERS) - 1,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.AUD_WALLET_HEADERS),
                "name": "Audit_Wallet",
            },
        )
        cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 2, col_abs=True)
        self.worksheet.conditional_format(
            start_row + 1,
            2,
            self.row_num,
            2,
            {
                "type": "formula",
                "criteria": f"=INT({cell})={cell}",
                "format": self.workbook_formats.num_int,
            },
        )
        self.row_num += 1

    def audit_by_crypto(self, audit_totals: Dict[AssetSymbol, AuditTotals]) -> None:
        self.worksheet.merge_range(
            self.row_num,
            0,
            self.row_num,
            len(self.AUD_CRYPTO_HEADERS) - 1,
            "Audit - Asset Balances - Cryptoassets",
            self.workbook_formats.title,
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
            len(self.AUD_CRYPTO_HEADERS) - 1,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.AUD_CRYPTO_HEADERS),
                "name": "Audit_Asset_Crypto",
            },
        )
        cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 1, col_abs=True)
        self.worksheet.conditional_format(
            start_row + 1,
            1,
            self.row_num,
            1,
            {
                "type": "formula",
                "criteria": f"=INT({cell})={cell}",
                "format": self.workbook_formats.num_int,
            },
        )
        cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 2, col_abs=True)
        self.worksheet.conditional_format(
            start_row + 1,
            2,
            self.row_num,
            2,
            {
                "type": "formula",
                "criteria": f"=INT({cell})={cell}",
                "format": self.workbook_formats.num_int_signed,
            },
        )
        self.row_num += 1

    def audit_by_fiat(self, audit_totals: Dict[AssetSymbol, AuditTotals]) -> None:
        self.worksheet.merge_range(
            self.row_num,
            0,
            self.row_num,
            len(self.AUD_FIAT_HEADERS) - 1,
            "Audit - Asset Balances - Fiat",
            self.workbook_formats.title,
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
            len(self.AUD_FIAT_HEADERS) - 1,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.AUD_FIAT_HEADERS),
                "name": "Audit_Asset_Fiat",
            },
        )
        cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 1, col_abs=True)
        self.worksheet.conditional_format(
            start_row + 1,
            1,
            self.row_num,
            1,
            {
                "type": "formula",
                "criteria": f"=INT({cell})={cell}",
                "format": self.workbook_formats.num_int,
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

    def buys_ordered(
        self,
        buys_ordered: List[Buy],
        row_tracker: "RowTracker",
        price_to_row: Dict[Tuple[AssetSymbol, Date], int],
    ) -> None:
        self.worksheet.merge_range(
            self.row_num,
            0,
            self.row_num,
            len(self.BUYS_HEADERS) - 1,
            "Buys",
            self.workbook_formats.title,
        )
        self.row_num += 1
        start_row = self.row_num

        for buy in buys_ordered:
            self.row_num += 1
            row_tracker.set_row(buy, self.row_num)

            if not buy.is_split:
                if buy.t_type in BUY_AND_SELL_TYPES:
                    link_name = f"{buy.t_type.value} (Buy)"
                else:
                    link_name = buy.t_type.value

                if buy.t_record:
                    self.worksheet.write_url(
                        self.row_num,
                        0,
                        f"external:{buy.t_record.t_row.filename}"
                        f"#'{buy.t_record.t_row.worksheet_name}'"
                        f"!A{buy.t_record.t_row.row_num}:M{buy.t_record.t_row.row_num}",
                        self.workbook_formats.string_link,
                        string=link_name,
                    )
                else:
                    self.worksheet.write_string(self.row_num, 0, link_name)

            self.worksheet.write_string(self.row_num, 1, buy.asset)
            self.worksheet.write_number(
                self.row_num, 2, buy.quantity.normalize(), self.workbook_formats.quantity
            )
            self.worksheet.write_datetime(
                self.row_num, 3, buy.timestamp, self.workbook_formats.date
            )
            if buy.cost is not None:
                if buy.cost_fixed:
                    self.worksheet.write_number(
                        self.row_num,
                        4,
                        buy.cost.normalize(),
                        self.workbook_formats.currency_fixed,
                    )
                else:
                    price_row = price_to_row.get((buy.asset, buy.date()))
                    if price_row is not None:
                        hyperlink = (
                            f"=HYPERLINK(\"#'Price Data'!A{price_row}:G{price_row}\","
                            f"{buy.cost.normalize()})"
                        )
                        self.worksheet.write_formula(
                            self.row_num,
                            4,
                            hyperlink,
                            self.workbook_formats.currency_link,
                        )
                    else:
                        self.worksheet.write_number(
                            self.row_num,
                            4,
                            buy.cost.normalize(),
                            self.workbook_formats.currency,
                        )
            if buy.fee_value is not None:
                self.worksheet.write_number(
                    self.row_num,
                    5,
                    buy.fee_value.normalize(),
                    self.workbook_formats.currency,
                )

            self.worksheet.write_string(self.row_num, 6, buy.wallet)
            self.worksheet.write_string(self.row_num, 7, buy.note)
            if buy.t_record and buy.t_record.t_row.tx_raw:
                self.worksheet.write_string(self.row_num, 8, buy.t_record.t_row.tx_raw.tx_hash)

            if not buy.is_crypto():
                category = "Fiat"
            elif buy.t_type in TRANSFER_TYPES:
                category = "Transfer"
            else:
                category = "Crypto"
            self.worksheet.write_string(self.row_num, 9, category)
            self.worksheet.write_boolean(self.row_num, 10, buy.matched)

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            len(self.BUYS_HEADERS) - 1,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.BUYS_HEADERS),
                "name": "Buys",
            },
        )
        cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 2, col_abs=True)
        self.worksheet.conditional_format(
            start_row + 1,
            2,
            self.row_num,
            2,
            {
                "type": "formula",
                "criteria": f"=INT({cell})={cell}",
                "format": self.workbook_formats.num_int,
            },
        )
        cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 10, col_abs=True)
        self.worksheet.conditional_format(
            start_row + 1,
            0,
            self.row_num,
            len(self.BUYS_HEADERS) - 1,
            {
                "type": "formula",
                "criteria": f"={cell}=FALSE",
                "format": self.workbook_formats.grey,
            },
        )
        cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 7, col_abs=True)
        self.worksheet.conditional_format(
            start_row + 1,
            0,
            self.row_num,
            len(self.BUYS_HEADERS) - 1,
            {
                "type": "formula",
                "criteria": f'={cell}="{COST_BASIS_ZERO_NOTE}"',
                "format": self.workbook_formats.red,
            },
        )
        self.worksheet.ignore_errors(
            {"formula_differs": xlsxwriter.utility.xl_range(start_row, 4, self.row_num, 4)}
        )

    def sells_ordered(
        self,
        sells_ordered: List[Sell],
        row_tracker: "RowTracker",
        price_to_row: Dict[Tuple[AssetSymbol, Date], int],
    ) -> None:
        self.worksheet.merge_range(
            self.row_num,
            0,
            self.row_num,
            len(self.SELLS_HEADERS) - 1,
            "Sells",
            self.workbook_formats.title,
        )
        self.row_num += 1
        start_row = self.row_num

        for sell in sells_ordered:
            self.row_num += 1
            row_tracker.set_row(sell, self.row_num)

            if sell.t_record:
                if sell.t_record.fee == sell:
                    link_name = f"{sell.t_type.value} ({sell.t_record.t_type.value} Fee)"
                elif sell.t_type in BUY_AND_SELL_TYPES:
                    link_name = f"{sell.t_type.value} (Sell)"
                else:
                    link_name = sell.t_type.value

                self.worksheet.write_url(
                    self.row_num,
                    0,
                    f"external:{sell.t_record.t_row.filename}"
                    f"#'{sell.t_record.t_row.worksheet_name}'"
                    f"!A{sell.t_record.t_row.row_num}:M{sell.t_record.t_row.row_num}",
                    self.workbook_formats.string_link,
                    string=link_name,
                )
            else:
                self.worksheet.write_string(self.row_num, 0, sell.t_type.value)

            self.worksheet.write_string(self.row_num, 1, sell.asset)
            self.worksheet.write_number(
                self.row_num, 2, sell.quantity.normalize(), self.workbook_formats.quantity
            )
            self.worksheet.write_datetime(
                self.row_num, 3, sell.timestamp, self.workbook_formats.date
            )
            if sell.proceeds is not None:
                if sell.proceeds_fixed:
                    self.worksheet.write_number(
                        self.row_num,
                        4,
                        sell.proceeds.normalize(),
                        self.workbook_formats.currency_fixed,
                    )
                else:
                    price_row = price_to_row.get((sell.asset, sell.date()))
                    if price_row is not None:
                        hyperlink = (
                            f"=HYPERLINK(\"#'Price Data'!A{price_row}:G{price_row}\","
                            f"{sell.proceeds.normalize()})"
                        )
                        self.worksheet.write_formula(
                            self.row_num,
                            4,
                            hyperlink,
                            self.workbook_formats.currency_link,
                        )
                    else:
                        self.worksheet.write_number(
                            self.row_num,
                            4,
                            sell.proceeds.normalize(),
                            self.workbook_formats.currency,
                        )
            if sell.fee_value is not None:
                self.worksheet.write_number(
                    self.row_num,
                    5,
                    sell.fee_value.normalize(),
                    self.workbook_formats.currency,
                )

            self.worksheet.write_string(self.row_num, 6, sell.wallet)
            self.worksheet.write_string(self.row_num, 7, sell.note)
            if sell.t_record and sell.t_record.t_row.tx_raw:
                self.worksheet.write_string(self.row_num, 8, sell.t_record.t_row.tx_raw.tx_hash)

            if not sell.is_crypto():
                category = "Fiat"
            elif sell.t_type in TRANSFER_TYPES:
                category = "Transfer"
            else:
                category = "Crypto"
            self.worksheet.write_string(self.row_num, 9, category)
            self.worksheet.write_boolean(self.row_num, 10, sell.matched)

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            len(self.SELLS_HEADERS) - 1,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.SELLS_HEADERS),
                "name": "Sells",
            },
        )
        cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 2, col_abs=True)
        self.worksheet.conditional_format(
            start_row + 1,
            2,
            self.row_num,
            2,
            {
                "type": "formula",
                "criteria": f"=INT({cell})={cell}",
                "format": self.workbook_formats.num_int,
            },
        )
        cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 10, col_abs=True)
        self.worksheet.conditional_format(
            start_row + 1,
            0,
            self.row_num,
            len(self.SELLS_HEADERS) - 1,
            {
                "type": "formula",
                "criteria": f"={cell}=FALSE",
                "format": self.workbook_formats.grey,
            },
        )
        self.worksheet.ignore_errors(
            {"formula_differs": xlsxwriter.utility.xl_range(start_row, 4, self.row_num, 4)}
        )

    def price_data(
        self,
        price_report: Dict[Year, Dict[AssetSymbol, Dict[Date, VaPriceReport]]],
    ) -> Dict[Tuple[AssetSymbol, Date], int]:
        price_to_row = {}
        self.worksheet.merge_range(
            self.row_num,
            0,
            self.row_num,
            len(self.PRICE_HEADERS) - 1,
            "Price Data",
            self.workbook_formats.title,
        )
        self.row_num += 1
        start_row = self.row_num

        for year in sorted(price_report):
            for asset in sorted(price_report[year], key=str.lower):
                for date in sorted(price_report[year][asset]):
                    self.row_num += 1
                    price_to_row[(asset, date)] = self.row_num + 1

                    price_data = price_report[year][asset][date]
                    if price_data["price_ccy"] is not None:
                        self.worksheet.write_string(self.row_num, 0, asset)
                        self.worksheet.write_string(self.row_num, 1, price_data["name"])
                        self.worksheet.write_url(
                            self.row_num,
                            2,
                            price_data["url"],
                            self.workbook_formats.string_link,
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
            len(self.PRICE_HEADERS) - 1,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.PRICE_HEADERS),
                "name": "Price_Data",
            },
        )
        self.worksheet.ignore_errors(
            {"number_stored_as_text": xlsxwriter.utility.xl_range(start_row, 4, self.row_num, 4)}
        )
        self.row_num += 1
        return price_to_row

    def capital_gains(
        self,
        title: str,
        cgains: Dict[AssetSymbol, List[TaxEventCapitalGains]],
        table_name: str,
        row_tracker: Optional["RowTracker"],
    ) -> None:
        self.worksheet.merge_range(
            self.row_num,
            0,
            self.row_num,
            len(self.CG_HEADERS) - 1,
            title,
            self.workbook_formats.title,
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
                            {"font_size": FONT_SIZE - 1, "x_scale": 2},
                        )
                    else:
                        self.worksheet.write_datetime(
                            self.row_num, 2, te.acquisition_dates[0], self.workbook_formats.date
                        )
                self.worksheet.write_datetime(self.row_num, 3, te.date, self.workbook_formats.date)

                quantity = sum(buy.quantity for buy in te.buys)
                if quantity != te.sell.quantity:
                    proceeds_percent = quantity / te.sell.quantity
                    self.worksheet.write_comment(
                        self.row_num,
                        4,
                        (
                            f"Disposal is short-term and long-term\nProceeds is "
                            f"{proceeds_percent:.0%} ({quantity:,} / {te.sell.quantity:,})"
                        ),
                        {"font_size": FONT_SIZE - 1, "x_scale": 2},
                    )

                zero_basis = [buy for buy in te.buys if buy.t_record is None]
                if zero_basis:
                    self.worksheet.write_comment(
                        self.row_num,
                        5,
                        "Cost basis zero used",
                        {"font_size": FONT_SIZE - 1, "x_scale": 2},
                    )

                if row_tracker:
                    cell_range = row_tracker.get_row(te.sell)
                    hyperlink = f'=HYPERLINK("#Sells!{cell_range}", {te.proceeds})'
                    self.worksheet.write_formula(
                        self.row_num, 4, hyperlink, self.workbook_formats.currency_link
                    )

                    cell_range = row_tracker.get_rows_from_list(te.buys)
                    hyperlink = f'=HYPERLINK("#Buys!{cell_range}", {te.cost})'
                    self.worksheet.write_formula(
                        self.row_num, 5, hyperlink, self.workbook_formats.currency_link
                    )
                else:
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
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 4, end_a_row, 4)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Cost
            self.worksheet.write_formula(
                self.row_num,
                5,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 5, end_a_row, 5)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Gain/Loss
            self.worksheet.write_formula(
                self.row_num,
                6,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 6, end_a_row, 6)})",
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
            len(self.CG_HEADERS) - 1,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.CG_HEADERS),
                "name": table_name,
            },
        )
        cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 1, col_abs=True)
        self.worksheet.conditional_format(
            start_row + 1,
            1,
            self.row_num,
            1,
            {
                "type": "formula",
                "criteria": f"=INT({cell})={cell}",
                "format": self.workbook_formats.num_int,
            },
        )
        self.worksheet.ignore_errors(
            {"formula_differs": xlsxwriter.utility.xl_range(start_row + 1, 4, self.row_num, 4)}
        )
        self.worksheet.ignore_errors(
            {"formula_differs": xlsxwriter.utility.xl_range(start_row + 1, 5, self.row_num, 5)}
        )
        self.row_num += 1

    def no_gain_no_loss(
        self,
        title: str,
        cgains: CalculateCapitalGains,
        table_name: str,
        row_tracker: Optional["RowTracker"],
    ) -> None:
        if not cgains.non_tax_by_type:
            self.worksheet.merge_range(
                self.row_num,
                0,
                self.row_num,
                len(self.NON_TAX_HEADERS) - 1,
                title,
                self.workbook_formats.title,
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
                len(self.NON_TAX_HEADERS) - 1,
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
                self.row_num,
                0,
                self.row_num,
                len(self.NON_TAX_HEADERS) - 1,
                f"{title} - {t_type}",
                self.workbook_formats.title,
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

                if row_tracker:
                    cell_range = row_tracker.get_row(te.sell)
                    hyperlink = f'=HYPERLINK("#Sells!{cell_range}", {te.market_value})'
                    self.worksheet.write_formula(
                        self.row_num, 5, hyperlink, self.workbook_formats.currency_link
                    )

                    cell_range = row_tracker.get_rows_from_list(te.buys)
                    hyperlink = f'=HYPERLINK("#Buys!{cell_range}", {te.cost})'
                    self.worksheet.write_formula(
                        self.row_num, 6, hyperlink, self.workbook_formats.currency_link
                    )
                else:
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
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 5, end_row, 5)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Cost Basis
            self.worksheet.write_formula(
                self.row_num,
                6,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 6, end_row, 6)})",
                self.workbook_formats.currency_bold,
            )
            self.worksheet.add_table(
                start_row,
                0,
                self.row_num,
                len(self.NON_TAX_HEADERS) - 1,
                {
                    "style": self.TABLE_STYLE,
                    "columns": self._get_columns(self.NON_TAX_HEADERS),
                    "name": f"{table_name}_{t_type.replace('-', '_')}",
                },
            )
            cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 1, col_abs=True)
            self.worksheet.conditional_format(
                start_row + 1,
                1,
                self.row_num,
                1,
                {
                    "type": "formula",
                    "criteria": f"=INT({cell})={cell}",
                    "format": self.workbook_formats.num_int,
                },
            )
            self.worksheet.ignore_errors(
                {"formula_differs": xlsxwriter.utility.xl_range(start_row + 1, 5, self.row_num, 5)}
            )
            self.worksheet.ignore_errors(
                {"formula_differs": xlsxwriter.utility.xl_range(start_row + 1, 6, self.row_num, 6)}
            )
            self.row_num += 1

    def income_by_asset(
        self,
        title: str,
        income: CalculateIncome,
        table_name: str,
        row_tracker: Optional["RowTracker"],
    ) -> None:
        self.worksheet.merge_range(
            self.row_num,
            0,
            self.row_num,
            len(self.IN_ASSET_HEADERS) - 1,
            title,
            self.workbook_formats.title,
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

                if row_tracker:
                    cell_range = row_tracker.get_row_grouped(te.buy)
                    hyperlink = f'=HYPERLINK("#Buys!{cell_range}", {te.amount})'
                    self.worksheet.write_formula(
                        self.row_num, 5, hyperlink, self.workbook_formats.currency_link
                    )
                    hyperlink = f'=HYPERLINK("#Buys!{cell_range}", {te.fees})'
                    self.worksheet.write_formula(
                        self.row_num, 6, hyperlink, self.workbook_formats.currency_link
                    )
                else:
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
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 5, end_a_row, 5)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Fees
            self.worksheet.write_formula(
                self.row_num,
                6,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 6, end_a_row, 6)})",
                self.workbook_formats.currency_bold,
            )
        else:
            self.worksheet.write_number(self.row_num, 5, 0, self.workbook_formats.currency_bold)
            self.worksheet.write_number(self.row_num, 6, 0, self.workbook_formats.currency_bold)

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            len(self.IN_ASSET_HEADERS) - 1,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.IN_ASSET_HEADERS),
                "name": table_name,
            },
        )
        cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 1, col_abs=True)
        self.worksheet.conditional_format(
            start_row + 1,
            1,
            self.row_num,
            1,
            {
                "type": "formula",
                "criteria": f"=INT({cell})={cell}",
                "format": self.workbook_formats.num_int,
            },
        )
        self.worksheet.ignore_errors(
            {"formula_differs": xlsxwriter.utility.xl_range(start_row + 1, 5, self.row_num, 5)}
        )
        self.worksheet.ignore_errors(
            {"formula_differs": xlsxwriter.utility.xl_range(start_row + 1, 6, self.row_num, 6)}
        )
        self.row_num += 1

    def income_by_type(
        self,
        title: str,
        income: CalculateIncome,
        table_name: str,
        row_tracker: Optional["RowTracker"],
    ) -> None:
        self.worksheet.merge_range(
            self.row_num,
            0,
            self.row_num,
            len(self.IN_TYPE_HEADERS) - 1,
            title,
            self.workbook_formats.title,
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

                if row_tracker:
                    cell_range = row_tracker.get_row_grouped(te.buy)
                    hyperlink = f'=HYPERLINK("#Buys!{cell_range}", {te.amount})'
                    self.worksheet.write_formula(
                        self.row_num, 5, hyperlink, self.workbook_formats.currency_link
                    )
                    hyperlink = f'=HYPERLINK("#Buys!{cell_range}", {te.fees})'
                    self.worksheet.write_formula(
                        self.row_num, 6, hyperlink, self.workbook_formats.currency_link
                    )
                else:
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
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 5, end_a_row, 5)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Fees
            self.worksheet.write_formula(
                self.row_num,
                6,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 6, end_a_row, 6)})",
                self.workbook_formats.currency_bold,
            )
        else:
            self.worksheet.write_number(self.row_num, 5, 0, self.workbook_formats.currency_bold)
            self.worksheet.write_number(self.row_num, 6, 0, self.workbook_formats.currency_bold)

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            len(self.IN_TYPE_HEADERS) - 1,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.IN_TYPE_HEADERS),
                "name": table_name,
            },
        )
        cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 2, col_abs=True)
        self.worksheet.conditional_format(
            start_row + 1,
            2,
            self.row_num,
            2,
            {
                "type": "formula",
                "criteria": f"=INT({cell})={cell}",
                "format": self.workbook_formats.num_int,
            },
        )
        self.worksheet.ignore_errors(
            {"formula_differs": xlsxwriter.utility.xl_range(start_row + 1, 5, self.row_num, 5)}
        )
        self.worksheet.ignore_errors(
            {"formula_differs": xlsxwriter.utility.xl_range(start_row + 1, 6, self.row_num, 6)}
        )

        self.row_num += 1

    def margin_trading(
        self,
        title: str,
        margin: CalculateMarginTrading,
        table_name: str,
        row_tracker: Optional["RowTracker"],
    ) -> None:
        self.worksheet.merge_range(
            self.row_num,
            0,
            self.row_num,
            len(self.MARGIN_HEADERS) - 1,
            title,
            self.workbook_formats.title,
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

                if row_tracker:
                    cell_range = row_tracker.get_row_grouped(te.t)
                    if isinstance(te.t, Buy):
                        link = f"#Buys!{cell_range}"
                    elif isinstance(te.t, Sell):
                        link = f"#Sells!{cell_range}"
                    else:
                        raise RuntimeError

                    self.worksheet.write_formula(
                        self.row_num,
                        3,
                        f'=HYPERLINK("{link}", {te.gain})',
                        self.workbook_formats.currency_link,
                    )
                    self.worksheet.write_formula(
                        self.row_num,
                        4,
                        f'=HYPERLINK("{link}", {te.loss})',
                        self.workbook_formats.currency_link,
                    )
                    self.worksheet.write_formula(
                        self.row_num,
                        5,
                        f'=HYPERLINK("{link}", {te.fee})',
                        self.workbook_formats.currency_link,
                    )
                else:
                    self.worksheet.write_number(
                        self.row_num, 3, te.gain, self.workbook_formats.currency
                    )
                    self.worksheet.write_number(
                        self.row_num, 4, te.loss, self.workbook_formats.currency
                    )
                    self.worksheet.write_number(
                        self.row_num, 5, te.fee, self.workbook_formats.currency
                    )

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
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 3, end_a_row, 3)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Losses
            self.worksheet.write_formula(
                self.row_num,
                4,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 4, end_a_row, 4)})",
                self.workbook_formats.currency_bold,
            )
            # Grand total Fees
            self.worksheet.write_formula(
                self.row_num,
                5,
                f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 5, end_a_row, 5)})",
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
            len(self.MARGIN_HEADERS) - 1,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.MARGIN_HEADERS),
                "name": table_name,
            },
        )
        self.worksheet.ignore_errors(
            {"formula_differs": xlsxwriter.utility.xl_range(start_row + 1, 3, self.row_num, 3)}
        )
        self.worksheet.ignore_errors(
            {"formula_differs": xlsxwriter.utility.xl_range(start_row + 1, 4, self.row_num, 4)}
        )
        self.worksheet.ignore_errors(
            {"formula_differs": xlsxwriter.utility.xl_range(start_row + 1, 5, self.row_num, 5)}
        )
        self.row_num += 1

    def holdings(
        self,
        title: str,
        holdings_report: HoldingsReportRecord,
        table_name: str,
    ) -> None:
        self.worksheet.merge_range(
            self.row_num,
            0,
            self.row_num,
            len(self.HOLDINGS_HEADERS) - 1,
            title,
            self.workbook_formats.title,
        )
        self.row_num += 1
        start_row = self.row_num
        end_a_row = None

        self.row_num += 1

        for h in sorted(holdings_report["holdings"], key=str.lower):
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
            end_a_row = self.row_num
            self.row_num += 1

        self.worksheet.write_string(self.row_num, 0, "Total", self.workbook_formats.bold)

        # Total Cost Basis
        self.worksheet.write_formula(
            self.row_num,
            3,
            f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 3, end_a_row, 3)})",
            self.workbook_formats.currency_bold,
        )
        # Total Market Value
        self.worksheet.write_formula(
            self.row_num,
            4,
            f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 4, end_a_row, 4)})",
            self.workbook_formats.currency_bold,
        )
        # Total Gain/Loss
        self.worksheet.write_formula(
            self.row_num,
            5,
            f"=SUBTOTAL(9,{xlsxwriter.utility.xl_range(start_row + 1, 5, end_a_row, 5)})",
            self.workbook_formats.currency_bold,
        )

        self.worksheet.add_table(
            start_row,
            0,
            self.row_num,
            len(self.HOLDINGS_HEADERS) - 1,
            {
                "style": self.TABLE_STYLE,
                "columns": self._get_columns(self.HOLDINGS_HEADERS),
                "name": table_name,
            },
        )
        cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row + 1, 2, col_abs=True)
        self.worksheet.conditional_format(
            start_row + 1,
            2,
            self.row_num,
            2,
            {
                "type": "formula",
                "criteria": f"=INT({cell})={cell}",
                "format": self.workbook_formats.num_int,
            },
        )
        self.row_num += 1


class RowTracker:
    def __init__(self) -> None:
        self.buys_to_row: Dict[Buy, List[int]] = {}
        self.sells_to_row: Dict[Sell, int] = {}

    def set_row(self, t: Union[Buy, Sell], row_num: int) -> None:
        if isinstance(t, Buy):
            self.buys_to_row[t] = [row_num]
            if t.is_split and t.t_record and t.t_record.buy:
                # Also add splits to the primary Buy
                self.buys_to_row[t.t_record.buy].append(row_num)
        elif isinstance(t, Sell):
            self.sells_to_row[t] = row_num
        else:
            raise RuntimeError("Unexpected transaction type")

    def get_rows_from_list(self, buys: List[Buy]) -> str:
        buy_matches = []
        for buy in buys:
            if buy in self.buys_to_row:
                buy_matches.append(self.buys_to_row[buy][0])
            else:
                raise RuntimeError("buy missing in buys_to_row")

        if buy_matches:
            min_row = min(buy_matches)
            max_row = max(buy_matches)
            return xlsxwriter.utility.xl_range(min_row, 0, max_row, 10)
        raise RuntimeError("buy missing in buys_to_row")

    def get_row(self, sell: Sell) -> str:
        sell_row = self.sells_to_row[sell]
        if sell_row:
            return xlsxwriter.utility.xl_range(sell_row, 0, sell_row, 10)
        raise RuntimeError("sell missing in sells_to_row")

    def get_row_grouped(self, t: Union[Buy, Sell]) -> str:
        if isinstance(t, Buy):
            buy_rows = self.buys_to_row.get(t)
            if buy_rows:
                min_row = min(buy_rows)
                max_row = max(buy_rows)
                return xlsxwriter.utility.xl_range(min_row, 0, max_row, 10)
            return ""
        if isinstance(t, Sell):
            sell_row = self.sells_to_row.get(t)
            if sell_row:
                return xlsxwriter.utility.xl_range(sell_row, 0, sell_row, 10)
            raise RuntimeError("Missing Sell in sell_to_row")
        raise RuntimeError("Unexpected transaction type")
