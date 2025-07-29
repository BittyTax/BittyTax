# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import argparse
import datetime
import itertools
import os
import sys
import threading
import time
from decimal import Decimal
from types import TracebackType
from typing import Dict, List, Optional, Tuple, Type

import jinja2
from colorama import Fore, Style
from xhtml2pdf import pisa

from .audit import AuditRecords, AuditTotals
from .bt_types import TAX_RULES_UK_COMPANY, AssetName, AssetSymbol, Date, Note, TaxRules, Year
from .config import config
from .constants import _H1, ERROR, H1, TERMINAL_POWERSHELL_GUI
from .price.valueasset import VaPriceReport
from .tax import (
    CalculateCapitalGains,
    CalculateIncome,
    CalculateMarginTrading,
    CapitalGainsReportEstimate,
    HoldingsReportRecord,
    TaxReportRecord,
)
from .version import __version__

if sys.version_info < (3, 9):
    import importlib_resources as pkg_resources
else:
    import importlib.resources as pkg_resources


class ReportPdf:
    AUDIT_FILENAME = "BittyTax_Audit_Report"
    TAX_SUMMARY_FILENAME = "BittyTax_Summary_Report"
    TAX_FULL_FILENAME = "BittyTax_Report"
    FILE_EXTENSION = "pdf"

    AUDIT_TEMPLATE = "audit_report.html"
    TAX_SUMMARY_TEMPLATE = "tax_summary_report.html"
    TAX_FULL_TEMPLATE = "tax_full_report.html"

    def __init__(
        self,
        progname: str,
        args: argparse.Namespace,
        audit: AuditRecords,
        tax_report: Optional[Dict[Year, TaxReportRecord]] = None,
        price_report: Optional[Dict[Year, Dict[AssetSymbol, Dict[Date, VaPriceReport]]]] = None,
        holdings_report: Optional[HoldingsReportRecord] = None,
    ) -> None:
        self.env = jinja2.Environment(loader=jinja2.PackageLoader(__package__, "templates"))

        self.env.filters["datefilter"] = self.datefilter
        self.env.filters["datefilter2"] = self.datefilter2
        self.env.filters["quantityfilter"] = self.quantityfilter
        self.env.filters["valuefilter"] = self.valuefilter
        self.env.filters["ratefilter"] = self.ratefilter
        self.env.filters["ratesfilter"] = self.ratesfilter
        self.env.filters["nowrapfilter"] = self.nowrapfilter
        self.env.filters["lenfilter"] = self.lenfilter
        self.env.filters["audittotalsfilter"] = self.audittotalsfilter
        self.env.filters["mismatchfilter"] = self.mismatchfilter
        self.env.globals["TAX_RULES_UK_COMPANY"] = TAX_RULES_UK_COMPANY
        self.env.globals["TEMPLATE_PATH"] = pkg_resources.files(__package__).joinpath("templates")

        if args.audit_only:
            filename = self.get_output_filename(args.output_filename, self.AUDIT_FILENAME)
            template = self.env.get_template(self.AUDIT_TEMPLATE)
            html = template.render(
                {
                    "date": datetime.datetime.now(),
                    "author": f"{progname} v{__version__}",
                    "config": config,
                    "args": args,
                    "audit": audit,
                }
            )
        elif args.summary_only:
            filename = self.get_output_filename(args.output_filename, self.TAX_SUMMARY_FILENAME)
            template = self.env.get_template(self.TAX_SUMMARY_TEMPLATE)
            html = template.render(
                {
                    "date": datetime.datetime.now(),
                    "author": f"{progname} v{__version__}",
                    "config": config,
                    "args": args,
                    "tax_report": tax_report,
                }
            )
        else:
            filename = self.get_output_filename(args.output_filename, self.TAX_FULL_FILENAME)
            template = self.env.get_template(self.TAX_FULL_TEMPLATE)
            html = template.render(
                {
                    "date": datetime.datetime.now(),
                    "author": f"{progname} v{__version__}",
                    "config": config,
                    "args": args,
                    "audit": audit,
                    "tax_report": tax_report,
                    "price_report": price_report,
                    "holdings_report": holdings_report,
                }
            )

        with ProgressSpinner(f"{Fore.CYAN}generating PDF report{Fore.GREEN}: "):
            with open(filename, "w+b") as pdf_file:
                status = pisa.CreatePDF(html, dest=pdf_file)

        if not status.err:
            sys.stdout.write(
                f"{Fore.WHITE}PDF report created: {Fore.YELLOW}{os.path.abspath(filename)}\n"
            )
        else:
            print(f"{ERROR} Failed to create PDF report")

    @staticmethod
    def datefilter(date: Date) -> str:
        return f"{date:%d/%m/%Y}"

    @staticmethod
    def datefilter2(date: Date) -> str:
        return f"{date:%b} {date.day}{ReportLog.format_day(date.day)} {date:%Y}"

    @staticmethod
    def quantityfilter(quantity: Decimal) -> str:
        return f"{quantity.normalize():0,f}"

    @staticmethod
    def valuefilter(value: Decimal) -> str:
        if config.ccy == "GBP":
            return f"&pound;{value:0,.2f}"
        if config.ccy == "EUR":
            return f"&euro;{value:0,.2f}"
        if config.ccy in ("USD", "AUD", "NZD"):
            return f"&dollar;{value:0,.2f}"
        if config.ccy in ("DKK", "NOK", "SEK"):
            return f"kr.{value:0,.2f}"
        raise RuntimeError("Currency not supported")

    @staticmethod
    def ratefilter(rate: Optional[Decimal]) -> str:
        if rate is None:
            return "*"
        return f"{rate}%"

    @staticmethod
    def ratesfilter(rates: List[Decimal]) -> str:
        return "/".join(map(ReportPdf.ratefilter, rates))

    @staticmethod
    def nowrapfilter(text: str) -> str:
        return text.replace(" ", "&nbsp;")

    @staticmethod
    def lenfilter(text: str, max_len: int = 40, dots: int = 3) -> str:
        return text[: max_len - dots] + "." * dots if len(text) > max_len else text

    @staticmethod
    def audittotalsfilter(
        audit_totals_list: List[Tuple[AssetSymbol, AuditTotals]], fiat_only: bool = False
    ) -> List[Tuple[AssetSymbol, AuditTotals]]:
        for asset, audit_totals in list(audit_totals_list):
            if config.audit_hide_empty:
                if not audit_totals.total and not audit_totals.transfers_mismatch:
                    audit_totals_list.remove((asset, audit_totals))
                    continue

            if fiat_only and asset not in config.fiat_list:
                audit_totals_list.remove((asset, audit_totals))
            elif not fiat_only and asset in config.fiat_list:
                audit_totals_list.remove((asset, audit_totals))

        return audit_totals_list

    @staticmethod
    def mismatchfilter(quantity: Decimal) -> str:
        if quantity:
            return f"{quantity.normalize():+0,f}"
        return ""

    @staticmethod
    def get_output_filename(filename: str, default_filename: str) -> str:
        if filename:
            filepath, file_extension = os.path.splitext(filename)
            if file_extension != ReportPdf.FILE_EXTENSION:
                filepath = filepath + "." + ReportPdf.FILE_EXTENSION
        else:
            filepath = default_filename + "." + ReportPdf.FILE_EXTENSION

        if not os.path.exists(filepath):
            return filepath

        filepath, file_extension = os.path.splitext(filepath)
        i = 2
        new_fname = f"{filepath}-{i}{file_extension}"
        while os.path.exists(new_fname):
            i += 1
            new_fname = f"{filepath}-{i}{file_extension}"

        return new_fname


class ReportLog:
    MAX_SYMBOL_LEN = 20
    MAX_NAME_LEN = 32
    MAX_NOTE_LEN = 40
    ASSET_WIDTH = MAX_SYMBOL_LEN + MAX_NAME_LEN + 3

    def __init__(
        self,
        args: argparse.Namespace,
        audit: AuditRecords,
        tax_report: Optional[Dict[Year, TaxReportRecord]] = None,
        price_report: Optional[Dict[Year, Dict[AssetSymbol, Dict[Date, VaPriceReport]]]] = None,
        holdings_report: Optional[HoldingsReportRecord] = None,
    ) -> None:
        if args.audit_only:
            self._audit(audit)
        elif args.summary_only:
            if tax_report is None:
                raise RuntimeError("Missing tax_report")

            self._tax_summary(args.tax_rules, tax_report)
        else:
            if tax_report is None:
                raise RuntimeError("Missing tax_report")

            if price_report is None:
                raise RuntimeError("Missing price_report")

            self._tax_full(args.tax_rules, audit, tax_report, price_report, holdings_report)

    def _tax_summary(self, tax_rules: TaxRules, tax_report: Dict[Year, TaxReportRecord]) -> None:
        print(f"{Fore.WHITE}tax report output:")
        for tax_year in sorted(tax_report):
            print(
                f"{H1}Tax Year - {config.format_tax_year(tax_year)} "
                f"({self.format_date2(Date(config.get_tax_year_start(tax_year)))} to "
                f"{self.format_date2(Date(config.get_tax_year_end(tax_year)))}){_H1}"
            )
            if tax_rules in TAX_RULES_UK_COMPANY:
                print(f"{Fore.CYAN}Chargeable Gains")
                self._capital_gains(tax_report[tax_year]["CapitalGains"])
            else:
                print(f"{Fore.CYAN}Capital Gains")
                self._capital_gains(tax_report[tax_year]["CapitalGains"])

    def _tax_full(
        self,
        tax_rules: TaxRules,
        audit: AuditRecords,
        tax_report: Dict[Year, TaxReportRecord],
        price_report: Dict[Year, Dict[AssetSymbol, Dict[Date, VaPriceReport]]],
        holdings_report: Optional[HoldingsReportRecord],
    ) -> None:
        print(f"{Fore.WHITE}tax report output:")
        self._audit(audit)

        for tax_year in sorted(tax_report):
            print(
                f"{H1}Tax Year - {config.format_tax_year(tax_year)} "
                f"({self.format_date2(Date(config.get_tax_year_start(tax_year)))} to "
                f"{self.format_date2(Date(config.get_tax_year_end(tax_year)))}){_H1}"
            )
            if tax_rules in TAX_RULES_UK_COMPANY:
                print(f"{Fore.CYAN}Chargeable Gains")
                self._capital_gains(tax_report[tax_year]["CapitalGains"])
                self._ct_estimate(tax_report[tax_year]["CapitalGains"])
            else:
                print(f"{Fore.CYAN}Capital Gains")
                self._capital_gains(tax_report[tax_year]["CapitalGains"])
                self._cgt_estimate(tax_report[tax_year]["CapitalGains"])

            self._income(tax_report[tax_year]["Income"])
            self._margin_trading(tax_report[tax_year]["MarginTrading"])

        print(f"{H1}Appendix{_H1}")
        for tax_year in sorted(tax_report):
            print(f"{Fore.CYAN}Price Data - {config.format_tax_year(tax_year)}\n")
            print(
                f'{Fore.YELLOW}{"Asset":<{self.ASSET_WIDTH + 2}} {"Data Source":<16} '
                f'{"Date":<10}  {"Price (" + config.ccy + ")":>13} {"Price (BTC)":>25}'
            )

            if tax_year in price_report:
                self._price_data(price_report[tax_year])

            print("")

        if holdings_report:
            self._holdings(holdings_report)

    def _audit(self, audit: AuditRecords) -> None:
        print(f"{H1}Audit{_H1}")
        print(f"{Fore.CYAN}Wallet Balances")
        for wallet in sorted(audit.wallets, key=str.lower):
            print(f'\n{Fore.YELLOW}{"Wallet":<30} {"Asset":<{self.MAX_SYMBOL_LEN}} {"Balance":>25}')

            for asset in sorted(audit.wallets[wallet]):
                print(
                    f"{Fore.WHITE}{wallet:<30} {asset:<{self.MAX_SYMBOL_LEN}} "
                    f"{Fore.RED if audit.wallets[wallet][asset] < 0 else Fore.WHITE}"
                    f"{self.format_quantity(audit.wallets[wallet][asset]):>25}"
                )

        print(f"\n{Fore.CYAN}Asset Balances (Cryptoassets)")
        print(
            f'\n{Fore.YELLOW}{"Asset":<{self.MAX_SYMBOL_LEN}} {"Balance":>25} '
            f'{"Transfers Mismatch":>25}'
        )
        for asset, audit_totals in sorted(filter(self.filter_audit_totals, audit.totals.items())):
            print(
                f"{Fore.WHITE}{asset:<{self.MAX_SYMBOL_LEN}} "
                f"{Fore.RED if audit_totals.total < 0 else Fore.WHITE}"
                f"{self.format_quantity(audit_totals.total):>25} "
                f"{Fore.RED}{self.format_mismatch(audit_totals.transfers_mismatch):>25}"
            )

        print(f"\n{Fore.CYAN}Asset Balances (Fiat Currency)")
        print(f'\n{Fore.YELLOW}{"Asset":<{self.MAX_SYMBOL_LEN}} {"Balance":>25}')
        for asset, audit_totals in sorted(
            filter(
                lambda pair: self.filter_audit_totals(pair, fiat_only=True), audit.totals.items()
            )
        ):
            print(
                f"{Fore.WHITE}{asset:<{self.MAX_SYMBOL_LEN}} "
                f"{Fore.RED if audit_totals.total < 0 else Fore.WHITE}"
                f"{self.format_quantity(audit_totals.total):>25}"
            )

    def _capital_gains(self, cgains: CalculateCapitalGains) -> None:
        header = (
            f'{"Asset":<{self.MAX_SYMBOL_LEN}} {"Date":<10} {"Disposal Type":<28} '
            f'{"Quantity":>25} {"Cost":>13} {"Fees":>13} {"Proceeds":>13} {"Gain":>13}'
        )
        for asset in sorted(cgains.assets):
            disposals = quantity = cost = fees = proceeds = gain = Decimal(0)
            print(f"\n{Fore.YELLOW}{header}")
            for te in cgains.assets[asset]:
                disposals += 1
                quantity += te.quantity
                cost += te.cost
                fees += te.fees
                proceeds += te.proceeds
                gain += te.gain
                print(
                    f"{Fore.WHITE}{te.asset:<{self.MAX_SYMBOL_LEN}} "
                    f"{self.format_date(te.date):<10} "
                    f"{te.format_disposal():<28} {self.format_quantity(te.quantity):>25} "
                    f"{self.format_value(te.cost):>13} {self.format_value(te.fees):>13} "
                    f"{self.format_value(te.proceeds):>13} "
                    f"{Fore.RED if te.gain < 0 else Fore.WHITE}{self.format_value(te.gain):>13}"
                )

            if disposals > 1:
                print(
                    f'{Fore.YELLOW}{"Total":<{self.MAX_SYMBOL_LEN}} {"":<10} '
                    f'{"":<28} {self.format_quantity(quantity):>25} '
                    f"{self.format_value(cost):>13} {self.format_value(fees):>13} "
                    f"{self.format_value(proceeds):>13} "
                    f"{Fore.RED if gain < 0 else Fore.YELLOW}{self.format_value(gain):>13}"
                )

        print(f'{Fore.YELLOW}{"_" * len(header)}')
        print(
            f'{Fore.YELLOW}{Style.BRIGHT}{"Total":<{self.MAX_SYMBOL_LEN}} {"":<10} '
            f'{"":<28} {"":>25} {self.format_value(cgains.totals["cost"]):>13} '
            f'{self.format_value(cgains.totals["fees"]):>13} '
            f'{self.format_value(cgains.totals["proceeds"]):>13} '
            f'{Fore.RED if cgains.totals["gain"] < 0 else Fore.YELLOW}'
            f'{self.format_value(cgains.totals["gain"]):>13}{Style.NORMAL}'
        )

        print(f"\n{Fore.CYAN}Summary\n")
        print(f'{Fore.WHITE}{"Number of disposals:":<40} {cgains.summary["disposals"]:>13}')
        if cgains.summary["proceeds_warning"]:
            print(
                f'{Fore.WHITE}{"Disposal proceeds:":<40} '
                f'{"*" + self.format_value(cgains.totals["proceeds"]):>13}'.replace(
                    "*", f"{Fore.YELLOW}*{Fore.WHITE}"
                )
            )
        else:
            print(
                f'{Fore.WHITE}{"Disposal proceeds:":<40} '
                f'{self.format_value(cgains.totals["proceeds"]):>13}'
            )

        print(
            f'{Fore.WHITE}{"Allowable costs (including the":<40} '
            f'{self.format_value(cgains.totals["cost"] + cgains.totals["fees"]):>13}'
        )

        print(f"{Fore.WHITE}purchase price):")
        print(
            f'{Fore.WHITE}{"Gains in the year, before losses:":<40} '
            f'{self.format_value(cgains.summary["total_gain"]):>13}'
        )
        print(
            f'{Fore.WHITE}{"Losses in the year:":<40} '
            f'{self.format_value(abs(cgains.summary["total_loss"])):>13}'
        )

        if cgains.split_date:
            print(
                f'\n{Fore.WHITE}{f"Gains before {self.format_date2(cgains.split_date)}":<40} '
                f'{Fore.RED if cgains.split_totals["gain_before"] < 0 else Fore.WHITE}'
                f'{self.format_value(cgains.split_totals["gain_before"]):>13}'
            )

            print(
                f'{Fore.WHITE}{f"Gains on or after {self.format_date2(cgains.split_date)}":<40} '
                f'{Fore.RED if cgains.split_totals["gain_after"] < 0 else Fore.WHITE}'
                f'{self.format_value(cgains.split_totals["gain_after"]):>13}'
            )

        if cgains.summary["proceeds_limit"] is not None and cgains.summary["proceeds_warning"]:
            print(
                f"{Fore.YELLOW}*Assets sold are more than "
                f'{self.format_value(cgains.summary["proceeds_limit"])}, '
                "this needs to be reported to HMRC if you already complete a Self Assessment"
            )

    def _cgt_estimate(self, cgains: CalculateCapitalGains) -> None:
        print(f"\n{Fore.CYAN}Tax Estimate\n")
        print(
            f"{Fore.CYAN}The figures below are only an estimate, "
            "they do not take into consideration other gains and losses in the same tax year, "
            "always consult with a professional accountant before filing."
        )

        if not cgains.split_date:
            self._cgt_estimate2(cgains.cgt_estimate)
        else:
            print(f"\n{Fore.CYAN}Gains before {self.format_date2(cgains.split_date)}")
            self._cgt_estimate2(cgains.cgt_estimate)
            print(f"\n{Fore.CYAN}Gains on or after {self.format_date2(cgains.split_date)}")
            self._cgt_estimate2(cgains.cgt_estimate_split)

    def _cgt_estimate2(self, cgt_estimate: CapitalGainsReportEstimate) -> None:
        if cgt_estimate["allowance_used"]:
            print(
                f'\n{Fore.WHITE}{"Taxable Gain*:":<40} '
                f'{self.format_value(cgt_estimate["taxable_gain"]):>13}'.replace(
                    "*", f"{Fore.YELLOW}*{Fore.WHITE}"
                )
            )
        else:
            print(
                f'\n{Fore.WHITE}{"Taxable Gain:":<40} '
                f'{self.format_value(cgt_estimate["taxable_gain"]):>13}'
            )

        print(
            f'{Fore.WHITE}{"Capital Gains Tax (Basic rate):":<40} '
            f'{self.format_value(cgt_estimate["cgt_basic"]):>13} '
            f'({self.format_rate(cgt_estimate["cgt_basic_rate"])})'
        )

        print(
            f'{Fore.WHITE}{"Capital Gains Tax (Higher rate):":<40} '
            f'{self.format_value(cgt_estimate["cgt_higher"]):>13} '
            f'({self.format_rate(cgt_estimate["cgt_higher_rate"])})'
        )

        if cgt_estimate["allowance_used"]:
            print(
                f'{Fore.YELLOW}*{self.format_value(cgt_estimate["allowance_used"])} of the '
                f'"Annual Exempt Amount" ({self.format_value(cgt_estimate["allowance"])}) '
                f"tax-free allowance used"
            )

    def _ct_estimate(self, cgains: CalculateCapitalGains) -> None:
        print(f"\n{Fore.CYAN}Tax Estimate\n")
        print(
            f"{Fore.CYAN}The figures below are only an estimate, they do not take into "
            "consideration other gains and losses in the same tax year, always consult with a "
            "professional accountant before filing.\n"
        )
        print(
            f'{Fore.WHITE}{"Taxable Gain:":<40} '
            f'{self.format_value(cgains.ct_estimate["taxable_gain"]):>13}'
        )

        if "ct_small" in cgains.ct_estimate:
            print(
                f'{Fore.WHITE}{"Corporation Tax (Small profits rate):":<40} '
                f'{self.format_value(cgains.ct_estimate["ct_small"]):>13} '
                f'({"/".join(map(self.format_rate, cgains.ct_estimate["ct_small_rates"]))})'
            )

        print(
            f'{Fore.WHITE}{"Corporation Tax (Main rate):":<40} '
            f'{self.format_value(cgains.ct_estimate["ct_main"]):>13} '
            f'({"/".join(map(self.format_rate, cgains.ct_estimate["ct_main_rates"]))})'
        )

        if None in cgains.ct_estimate["ct_small_rates"]:
            print(f"{Fore.YELLOW}* Main rate used")

    def _income(self, income: CalculateIncome) -> None:
        print(f"\n{Fore.CYAN}Income\n")
        header = (
            f'{"Asset":<{self.MAX_SYMBOL_LEN}} {"Date":<10} {"Income Type":<15} '
            f'{"Description":<40} {"Quantity":>25} {"Market Value":>15} {"Fees":>13}'
        )

        print(f"{Fore.YELLOW}{header}")
        for asset in sorted(income.assets):
            events = quantity = amount = fees = Decimal(0)
            for te in income.assets[asset]:
                events += 1
                quantity += te.quantity
                amount += te.amount
                fees += te.fees
                print(
                    f"{Fore.WHITE}{te.asset:<{self.MAX_SYMBOL_LEN}} "
                    f"{self.format_date(te.date):<10} {te.type.value:<15} "
                    f"{self.format_note(te.note):<40} {self.format_quantity(te.quantity):>25} "
                    f"{self.format_value(te.amount):>15} {self.format_value(te.fees):>13}"
                )
            if events > 1:
                print(
                    f'{Fore.YELLOW}{"Total":<{self.MAX_SYMBOL_LEN}} {"":<15} '
                    f'{"":<10} {"":<40} {self.format_quantity(quantity):>25} '
                    f"{self.format_value(amount):>15} {self.format_value(fees):>13}\n"
                )

        print(
            f'{Fore.YELLOW}{"Income Type":<{self.MAX_SYMBOL_LEN + 11}} {"":<15} '
            f'{"":<40} {"":>25} {"Market Value":>15} {"Fees":>13}'
        )

        for i_type in sorted(income.type_totals):
            print(
                f'{Fore.WHITE}{i_type:<{self.MAX_SYMBOL_LEN + 11}} {"":<15} '
                f'{"":<40} {"":>25} {self.format_value(income.type_totals[i_type]["amount"]):>15} '
                f'{self.format_value(income.type_totals[i_type]["fees"]):>13}'
            )

        print(f'{Fore.YELLOW}{"_" * len(header)}')
        print(
            f'{Fore.YELLOW}{Style.BRIGHT}{"Total":<{self.MAX_SYMBOL_LEN + 11}} {"":<15} '
            f'{"":<40} {"":>25} {self.format_value(income.totals["amount"]):>15} '
            f'{self.format_value(income.totals["fees"]):>13}{Style.NORMAL}'
        )

    def _margin_trading(self, margin: CalculateMarginTrading) -> None:
        print(f"\n{Fore.CYAN}Margin Trading\n")
        print("These figures are NOT included in the Summary or Tax Estimate above.\n")
        header = (
            f'{"Wallet":<30} {"Contract":<40} {"Gains":>13} {"Losses":>13} {"Fees":>13} '
            f'{"Fee Rebates":>13}'
        )

        print(f"{Fore.YELLOW}{header}")
        for wallet, note in sorted(
            margin.contract_totals, key=lambda key: (key[0].lower(), key[1].lower())
        ):
            print(
                f"{Fore.WHITE}{wallet:<30} "
                f"{Fore.WHITE}{self.format_note(note):<40} "
                f'{self.format_value(margin.contract_totals[(wallet, note)]["gains"]):>13} '
                f'{self.format_value(margin.contract_totals[(wallet, note)]["losses"]):>13} '
                f'{self.format_value(margin.contract_totals[(wallet, note)]["fees"]):>13} '
                f'{self.format_value(margin.contract_totals[(wallet, note)]["fee_rebates"]):>13}'
                f"{Style.NORMAL}"
            )

        print(f'{Fore.YELLOW}{"_" * len(header)}')
        print(
            f'{Fore.YELLOW}{Style.BRIGHT}{"Total":<30} '
            f'{"":<40} '
            f'{self.format_value(margin.totals["gains"]):>13} '
            f'{self.format_value(margin.totals["losses"]):>13} '
            f'{self.format_value(margin.totals["fees"]):>13} '
            f'{self.format_value(margin.totals["fee_rebates"]):>13}{Style.NORMAL}'
        )

    def _price_data(self, price_report: Dict[AssetSymbol, Dict[Date, VaPriceReport]]) -> None:
        price_missing_flag = False
        for asset in sorted(price_report):
            for date in sorted(price_report[asset]):
                price_data = price_report[asset][date]
                if price_data["price_ccy"] is not None:
                    print(
                        f"{Fore.WHITE}"
                        f'1 {self.format_asset(asset, price_data["name"]):<{self.ASSET_WIDTH}} '
                        f'{price_data["data_source"]:<16} {self.format_date(date):<10}  '
                        f'{self.format_value(price_data["price_ccy"]):>13} '
                        f'{self.format_quantity(price_data["price_btc"]):>25}'
                    )
                else:
                    price_missing_flag = True
                    print(
                        f"{Fore.WHITE}"
                        f'1 {self.format_asset(asset, price_data["name"]):<{self.ASSET_WIDTH}} '
                        f'{"":<16} {self.format_date(date):<10} '
                        f'{Fore.BLUE}{"Not available*":>13} '
                        f'{"":>25}'
                    )

        if price_missing_flag:
            print(f"{Fore.BLUE}*Price of {self.format_value(Decimal(0))} used")

    def _holdings(self, holdings_report: HoldingsReportRecord) -> None:
        print(f"{Fore.CYAN}Current Holdings\n")

        header = (
            f'{"Asset":<{self.ASSET_WIDTH}} {"Quantity":>25} {"Cost + Fees":>16} '
            f'{"Market Value":>16} {"Gain":>16}'
        )

        print(f"{Fore.YELLOW}{header}")
        for h in sorted(holdings_report["holdings"]):
            holding = holdings_report["holdings"][h]
            if holding["value"] is not None:
                print(
                    f"{Fore.WHITE}"
                    f'{self.format_asset(h, holding["name"]):<{self.ASSET_WIDTH}} '
                    f'{self.format_quantity(holding["quantity"]):>25} '
                    f'{self.format_value(holding["cost"]):>16} '
                    f'{self.format_value(holding["value"]):>16} '
                    f'{Fore.RED if holding["gain"] < 0 else Fore.WHITE}'
                    f'{self.format_value(holding["gain"]):>16}'
                )
            else:
                print(
                    f"{Fore.WHITE}"
                    f'{self.format_asset(h, holding["name"]):<{self.ASSET_WIDTH}} '
                    f'{self.format_quantity(holding["quantity"]):>25} '
                    f'{self.format_value(holding["cost"]):>16} '
                    f'{Fore.BLUE}{"Not available":>16} '
                    f'{"":>16}'
                )

        print(f'{Fore.YELLOW}{"_" * len(header)}')
        print(
            f"{Fore.YELLOW}{Style.BRIGHT}"
            f'{"Total":<{self.ASSET_WIDTH}} {"":>25} '
            f'{self.format_value(holdings_report["totals"]["cost"]):>16} '
            f'{self.format_value(holdings_report["totals"]["value"]):>16} '
            f'{Fore.RED if holdings_report["totals"]["gain"] < 0 else Fore.YELLOW}'
            f'{self.format_value(holdings_report["totals"]["gain"]):>16}'
        )

    @staticmethod
    def format_date(date: Date) -> str:
        return f"{date:%d/%m/%Y}"

    @staticmethod
    def format_date2(date: Date) -> str:
        return f"{date:%b} {date.day}{ReportLog.format_day(date.day)} {date:%Y}"

    @staticmethod
    def format_day(day: int) -> str:
        return "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    @staticmethod
    def format_quantity(quantity: Optional[Decimal]) -> str:
        if quantity is not None:
            return f"{quantity.normalize():0,f}"
        return "n/a"

    @staticmethod
    def format_value(value: Decimal) -> str:
        return f"{config.sym()}{value + 0:0,.2f}"

    @staticmethod
    def format_asset(asset: AssetSymbol, name: AssetName) -> str:
        if name:
            return f"{asset} ({name})"
        return asset

    @staticmethod
    def format_rate(rate: Optional[Decimal]) -> str:
        if rate is None:
            return f"{Fore.YELLOW}*{Fore.WHITE}"
        return f"{rate}%"

    @staticmethod
    def format_note(note: Note) -> str:
        return (
            note[: ReportLog.MAX_NOTE_LEN - 3] + "..."
            if len(note) > ReportLog.MAX_NOTE_LEN
            else note
        )

    @staticmethod
    def format_mismatch(quantity: Decimal) -> str:
        if quantity:
            return f"{quantity.normalize():+0,f}"
        return ""

    @staticmethod
    def filter_audit_totals(pair: Tuple[AssetSymbol, AuditTotals], fiat_only: bool = False) -> bool:
        asset, audit_totals = pair
        if config.audit_hide_empty:
            if not audit_totals.total and not audit_totals.transfers_mismatch:
                return False

        if fiat_only and asset not in config.fiat_list:
            return False
        if not fiat_only and asset in config.fiat_list:
            return False
        return True


class ProgressSpinner:
    def __init__(self, message: str) -> None:
        self.message = message
        self.spinner = itertools.cycle(["-", "\\", "|", "/"])
        self.busy = False

    def do_spinner(self) -> None:
        while self.busy:
            sys.stderr.write(next(self.spinner))
            sys.stderr.flush()
            time.sleep(0.1)
            if self.busy:
                sys.stderr.write("\b")
                sys.stderr.flush()

    def __enter__(self) -> None:
        if not self._disable():
            self.busy = True
            sys.stderr.write(self.message)
            threading.Thread(target=self.do_spinner).start()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ) -> None:
        if not self._disable():
            self.busy = False
            sys.stderr.write("\r")

    def _disable(self) -> bool:
        # Disable the spinner if it's not a terminal, or not using the Powershell GUI
        return bool(not sys.stdout.isatty() and config.terminal != TERMINAL_POWERSHELL_GUI)
