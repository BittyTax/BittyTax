# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import itertools
import os
import sys
import threading
import time
from datetime import datetime

import dateutil.parser
import jinja2
from colorama import Fore, Style
from xhtml2pdf import pisa

from .config import config
from .constants import _H1, ERROR, H1, TAX_RULES_UK_COMPANY
from .version import __version__


class ReportPdf:
    DEFAULT_FILENAME = "BittyTax_Report"
    FILE_EXTENSION = "pdf"
    TEMPLATE_FILE = "tax_report.html"

    def __init__(self, progname, audit, tax_report, price_report, holdings_report, args):
        self.env = jinja2.Environment(loader=jinja2.PackageLoader("bittytax", "templates"))
        self.filename = self.get_output_filename(args.output_filename, self.FILE_EXTENSION)

        self.env.filters["datefilter"] = self.datefilter
        self.env.filters["datefilter2"] = self.datefilter2
        self.env.filters["quantityfilter"] = self.quantityfilter
        self.env.filters["valuefilter"] = self.valuefilter
        self.env.filters["ratefilter"] = self.ratefilter
        self.env.filters["ratesfilter"] = self.ratesfilter
        self.env.filters["nowrapfilter"] = self.nowrapfilter
        self.env.filters["lenfilter"] = self.lenfilter
        self.env.globals["TAX_RULES_UK_COMPANY"] = TAX_RULES_UK_COMPANY

        template = self.env.get_template(self.TEMPLATE_FILE)
        html = template.render(
            {
                "date": datetime.now(),
                "author": f"{progname} v{__version__}",
                "config": config,
                "audit": audit,
                "tax_report": tax_report,
                "price_report": price_report,
                "holdings_report": holdings_report,
                "args": args,
            }
        )

        with ProgressSpinner():
            with open(self.filename, "w+b") as pdf_file:
                status = pisa.CreatePDF(html, dest=pdf_file)

        if not status.err:
            print(f"{Fore.WHITE}PDF tax report created: {Fore.YELLOW}{self.filename}")
        else:
            print(f"{ERROR} Failed to create PDF tax report")

    @staticmethod
    def datefilter(date):
        if isinstance(date, datetime):
            return f"{date:%d/%m/%Y}"
        return f"{dateutil.parser.parse(date):%d/%m/%Y}"

    @staticmethod
    def datefilter2(date):
        return f"{date:%b} {date.day}{ReportLog.format_day(date.day)} {date:%Y}"

    @staticmethod
    def quantityfilter(quantity):
        return f"{quantity.normalize():0,f}"

    @staticmethod
    def valuefilter(value):
        if config.ccy == "GBP":
            return f"&pound;{value:0,.2f}"
        if config.ccy == "EUR":
            return f"&euro;{value:0,.2f}"
        if config.ccy in ("USD", "AUD", "NZD"):
            return f"&dollar;{value:0,.2f}"
        if config.ccy in ("DKK", "NOK", "SEK"):
            return f"kr.{value:0,.2f}"
        raise ValueError("Currency not supported")

    @staticmethod
    def ratefilter(rate):
        if rate is None:
            return "*"
        return f"{rate}%"

    @staticmethod
    def ratesfilter(rates):
        return "/".join(map(ReportPdf.ratefilter, rates))

    @staticmethod
    def nowrapfilter(text):
        return text.replace(" ", "&nbsp;")

    @staticmethod
    def lenfilter(text, max_len=40, dots=3):
        return text[: max_len - dots] + "." * dots if len(text) > max_len else text

    @staticmethod
    def get_output_filename(filename, extension_type):
        if filename:
            filepath, file_extension = os.path.splitext(filename)
            if file_extension != extension_type:
                filepath = filepath + "." + extension_type
        else:
            filepath = ReportPdf.DEFAULT_FILENAME + "." + extension_type

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
    MAX_SYMBOL_LEN = 8
    MAX_NAME_LEN = 32
    MAX_NOTE_LEN = 40
    ASSET_WIDTH = MAX_SYMBOL_LEN + MAX_NAME_LEN + 3

    def __init__(self, audit, tax_report, price_report, holdings_report, args):
        self.audit_report = audit
        self.tax_report = tax_report
        self.price_report = price_report
        self.holdings_report = holdings_report

        print(f"{Fore.WHITE}tax report output:")
        if args.taxyear:
            if not args.summary:
                self.audit()

            print(
                f"{H1}Tax Year - {config.format_tax_year(args.taxyear)} "
                f"({self.format_date2(config.get_tax_year_start(args.taxyear))} to "
                f"{self.format_date2(config.get_tax_year_end(args.taxyear))}){_H1}"
            )
            self.capital_gains(args.taxyear, args.tax_rules, args.summary)
            if not args.summary:
                self.income(args.taxyear)
                print("{H1}Appendix{_H1}")
                self.price_data(args.taxyear)
        else:
            if not args.summary:
                self.audit()

            for tax_year in sorted(tax_report):
                print(
                    f"{H1}Tax Year - {config.format_tax_year(tax_year)} "
                    f"({self.format_date2(config.get_tax_year_start(tax_year))} to "
                    f"{self.format_date2(config.get_tax_year_end(tax_year))}){_H1}"
                )
                self.capital_gains(tax_year, args.tax_rules, args.summary)
                if not args.summary:
                    self.income(tax_year)

            if not args.summary:
                print(f"{H1}Appendix{_H1}")
                for tax_year in sorted(tax_report):
                    self.price_data(tax_year)
                    print("")
                self.holdings()

    def audit(self):
        print(f"{H1}Audit{_H1}")
        print(f"{Fore.CYAN}Final Balances")
        for wallet in sorted(self.audit_report.wallets, key=str.lower):
            print(f'\n{Fore.YELLOW}{"Wallet":<30} {"Asset":<{self.MAX_SYMBOL_LEN}} {"Balance":>25}')

            for asset in sorted(self.audit_report.wallets[wallet]):
                print(
                    f"{Fore.WHITE}{wallet:<30} {asset:<{self.MAX_SYMBOL_LEN}} "
                    f"{self.format_quantity(self.audit_report.wallets[wallet][asset]):>25}"
                )

    def capital_gains(self, tax_year, tax_rules, summary):
        cgains = self.tax_report[tax_year]["CapitalGains"]

        if tax_rules in TAX_RULES_UK_COMPANY:
            print(f"{Fore.CYAN}Chargeable Gains")
        else:
            print(f"{Fore.CYAN}Capital Gains")

        header = (
            f'{"Asset":<{self.MAX_SYMBOL_LEN}} {"Date":<10} {"Disposal Type":<28} '
            f'{"Quantity":>25} {"Cost":>13} {"Fees":>13} {"Proceeds":>13} {"Gain":>13}'
        )
        for asset in sorted(cgains.assets):
            disposals = quantity = cost = fees = proceeds = gain = 0
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
                    f"{Fore.RED if gain < 0 else Fore.WHITE}{self.format_value(gain):>13}"
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
        if cgains.estimate["proceeds_warning"]:
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

        if cgains.estimate["proceeds_warning"]:
            print(
                f"{Fore.YELLOW}*Assets sold are more than "
                f'{self.format_value(cgains.estimate["proceeds_limit"])}, '
                "this needs to be reported to HMRC if you already complete a Self Assessment"
            )

        if not summary:
            if tax_rules in TAX_RULES_UK_COMPANY:
                self.ct_estimate(tax_year)
            else:
                self.cgt_estimate(tax_year)

    def cgt_estimate(self, tax_year):
        cgains = self.tax_report[tax_year]["CapitalGains"]
        print(f"\n{Fore.CYAN}Tax Estimate\n")
        print(
            f"{Fore.CYAN}The figures below are only an estimate, "
            "they do not take into consideration other gains and losses in the same tax year, "
            "always consult with a professional accountant before filing.\n"
        )
        if cgains.totals["gain"] > 0:
            print(
                f'{Fore.WHITE}{"Taxable Gain*:":<40} '
                f'{self.format_value(cgains.estimate["taxable_gain"]):>13}'.replace(
                    "*", f"{Fore.YELLOW}*{Fore.WHITE}"
                )
            )
        else:
            print(
                f'{Fore.WHITE}{"Taxable Gain:":<40} '
                f'{self.format_value(cgains.estimate["taxable_gain"]):>13}'
            )

        print(
            f'{Fore.WHITE}{"Capital Gains Tax (Basic rate):":<40} '
            f'{self.format_value(cgains.estimate["cgt_basic"]):>13} '
            f'({self.format_rate(cgains.estimate["cgt_basic_rate"])})'
        )

        print(
            f'{Fore.WHITE}{"Capital Gains Tax (Higher rate):":<40} '
            f'{self.format_value(cgains.estimate["cgt_higher"]):>13} '
            f'({self.format_rate(cgains.estimate["cgt_higher_rate"])})'
        )

        if cgains.estimate["allowance_used"]:
            print(
                f'{Fore.YELLOW}*{self.format_value(cgains.estimate["allowance_used"])} of the '
                f'tax-free allowance ({self.format_value(cgains.estimate["allowance"])}) used'
            )

    def ct_estimate(self, tax_year):
        cgains = self.tax_report[tax_year]["CapitalGains"]
        print(f"\n{Fore.CYAN}Tax Estimate\n")
        print(
            f"{Fore.CYAN}The figures below are only an estimate, they do not take into "
            "consideration other gains and losses in the same tax year, always consult with a "
            "professional accountant before filing.\n"
        )
        print(
            f'{Fore.WHITE}{"Taxable Gain:":<40} '
            f'{self.format_value(cgains.estimate["taxable_gain"]):>13}'
        )

        if "ct_small" in cgains.estimate:
            print(
                f'{Fore.WHITE}{"Corporation Tax (Small profits rate):":<40} '
                f'{self.format_value(cgains.estimate["ct_small"]):>13} '
                f'({"/".join(map(self.format_rate, cgains.estimate["ct_small_rates"]))})'
            )

        print(
            f'{Fore.WHITE}{"Corporation Tax (Main rate):":<40} '
            f'{self.format_value(cgains.estimate["ct_main"]):>13} '
            f'({"/".join(map(self.format_rate, cgains.estimate["ct_main_rates"]))})'
        )

        if None in cgains.estimate["ct_small_rates"]:
            print(f"{Fore.YELLOW}* Main rate used")

    def income(self, tax_year):
        income = self.tax_report[tax_year]["Income"]

        print(f"\n{Fore.CYAN}Income\n")
        header = (
            f'{"Asset":<{self.MAX_SYMBOL_LEN}} {"Date":<10} {"Type":<10} {"Description":<40} '
            f'{"Quantity":<25} {"Amount":>13} {"Fees":>13}'
        )

        print(f"{Fore.YELLOW}{header}")

        for asset in sorted(income.assets):
            events = quantity = amount = fees = 0
            for te in income.assets[asset]:
                events += 1
                quantity += te.quantity
                amount += te.amount
                fees += te.fees
                print(
                    f"{Fore.WHITE}{te.asset:<{self.MAX_SYMBOL_LEN}} "
                    f"{self.format_date(te.date):<10} {te.type:<10} "
                    f"{self.format_note(te.note):<40} {self.format_quantity(te.quantity):<25} "
                    f"{self.format_value(te.amount):>13} {self.format_value(te.fees):>13}"
                )
            if events > 1:
                print(
                    f'{Fore.YELLOW}{"Total":<{self.MAX_SYMBOL_LEN}} {"":<10} '
                    f'{"":<10} {"":<40} {self.format_quantity(quantity):<25} '
                    f"{self.format_value(amount):>13} {self.format_value(fees):>13}\n"
                )

        print(
            f'{Fore.YELLOW}{"Income Type":<{self.MAX_SYMBOL_LEN + 11}} {"":<10} '
            f'{"":<40} {"":<25} {"Amount":>13} {"Fees":>13}'
        )

        for i_type in sorted(income.type_totals):
            print(
                f'{Fore.WHITE}{i_type:<{self.MAX_SYMBOL_LEN + 11}} {"":<10} '
                f'{"":<40} {"":<25} {self.format_value(income.type_totals[i_type]["amount"]):>13} '
                f'{self.format_value(income.type_totals[i_type]["fees"]):>13}'
            )

        print(f'{Fore.YELLOW}{"_" * len(header)}')
        print(
            f'{Fore.YELLOW}{Style.BRIGHT}{"Total":<{self.MAX_SYMBOL_LEN + 11}} {"":<10} '
            f'{"":<40} {"":<25} {self.format_value(income.totals["amount"]):>13} '
            f'{self.format_value(income.totals["fees"]):>13}{Style.NORMAL}'
        )

    def price_data(self, tax_year):
        print(f"{Fore.CYAN}Price Data - {config.format_tax_year(tax_year)}\n")
        print(
            f'{Fore.YELLOW}{"Asset":<{self.ASSET_WIDTH + 2}} {"Data Source":<16} '
            f'{"Date":<10}  {"Price (" + config.ccy + ")":>13} {"Price (BTC)":>25}'
        )

        if tax_year not in self.price_report:
            return

        price_missing_flag = False
        for asset in sorted(self.price_report[tax_year]):
            for date in sorted(self.price_report[tax_year][asset]):
                price_data = self.price_report[tax_year][asset][date]
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
            print(f"{Fore.BLUE}*Price of {self.format_value(0)} used")

    def holdings(self):
        print(f"{Fore.CYAN}Current Holdings\n")

        header = (
            f'{"Asset":<{self.ASSET_WIDTH}} {"Quantity":>25} {"Cost + Fees":>16} {"Value":>16} '
            f'{"Gain":>16}'
        )

        print(f"{Fore.YELLOW}{header}")
        for h in sorted(self.holdings_report["holdings"]):
            holding = self.holdings_report["holdings"][h]
            if holding["value"] is not None:
                print(
                    f"{Fore.WHITE}"
                    f'{self.format_asset(holding["asset"], holding["name"]):<{self.ASSET_WIDTH}} '
                    f'{self.format_quantity(holding["quantity"]):>25} '
                    f'{self.format_value(holding["cost"]):>16} '
                    f'{self.format_value(holding["value"]):>16} '
                    f'{Fore.RED if holding["gain"] < 0 else Fore.WHITE}'
                    f'{self.format_value(holding["gain"]):>16}'
                )
            else:
                print(
                    f"{Fore.WHITE}"
                    f'{self.format_asset(holding["asset"], holding["name"]):<{self.ASSET_WIDTH}} '
                    f'{self.format_quantity(holding["quantity"]):>25} '
                    f'{self.format_value(holding["cost"]):>16} '
                    f'{Fore.BLUE}{"Not available":>16} '
                    f'{"":>16}'
                )

        print(f'{Fore.YELLOW}{"_" * len(header)}')
        print(
            f"{Fore.YELLOW}{Style.BRIGHT}"
            f'{"Total":<{self.ASSET_WIDTH}} {"":>25} '
            f'{self.format_value(self.holdings_report["totals"]["cost"]):>16} '
            f'{self.format_value(self.holdings_report["totals"]["value"]):>16} '
            f'{Fore.RED if self.holdings_report["totals"]["gain"] < 0 else Fore.YELLOW}'
            f'{self.format_value(self.holdings_report["totals"]["gain"]):>16}'
        )

    @staticmethod
    def format_date(date):
        if isinstance(date, datetime):
            return f"{date:%d/%m/%Y}"
        return f"{dateutil.parser.parse(date):%d/%m/%Y}"

    @staticmethod
    def format_date2(date):
        return f"{date:%b} {date.day}{ReportLog.format_day(date.day)} {date:%Y}"

    @staticmethod
    def format_day(day):
        return "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    @staticmethod
    def format_quantity(quantity):
        if quantity is not None:
            return f"{quantity.normalize():0,f}"
        return "n/a"

    @staticmethod
    def format_value(value):
        return f"{config.sym()}{value + 0:0,.2f}"

    @staticmethod
    def format_asset(asset, name):
        if name is not None:
            return f"{asset} ({name})"
        return asset

    @staticmethod
    def format_rate(rate):
        if rate is None:
            return f"{Fore.YELLOW}*{Fore.WHITE}"
        return f"{rate}%"

    @staticmethod
    def format_note(note):
        return (
            note[: ReportLog.MAX_NOTE_LEN - 3] + "..."
            if len(note) > ReportLog.MAX_NOTE_LEN
            else note
        )


class ProgressSpinner:
    def __init__(self):
        self.spinner = itertools.cycle(["-", "\\", "|", "/"])
        self.busy = False

    def do_spinner(self):
        while self.busy:
            sys.stdout.write(next(self.spinner))
            sys.stdout.flush()
            time.sleep(0.1)
            sys.stdout.write("\b")
            sys.stdout.flush()

    def __enter__(self):
        if sys.stdout.isatty():
            self.busy = True
            sys.stdout.write(f"{Fore.CYAN}generating PDF report{Fore.GREEN}: ")
            threading.Thread(target=self.do_spinner).start()

    def __exit__(self, exc_type, exc_val, exc_traceback):
        if sys.stdout.isatty():
            self.busy = False
            sys.stdout.write("\r")
