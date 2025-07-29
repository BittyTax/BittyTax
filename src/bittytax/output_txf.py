# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import datetime
import os
import sys
from typing import Dict, TextIO

from colorama import Fore

from .bt_types import DisposalType, Year
from .constants import ACQUISITIONS_VARIOUS
from .tax import TaxReportRecord
from .tax_event import TaxEventCapitalGains
from .version import __version__


class OutputTurboTaxTxf:  # pylint: disable=too-few-public-methods
    DEFAULT_FILENAME = "BittyTax_TurboTax"
    FILE_EXTENSION = "txf"
    OUTPUT_FORMAT = "TurboTax TXF"
    TXF_VERSION = "042"
    TAX_REF_SHORT_TERM = "712"
    TAX_REF_LONG_TERM = "714"

    def __init__(self, filename: str, tax_report: Dict[Year, TaxReportRecord]) -> None:
        self.tax_report = tax_report
        self.filename = self._get_output_filename(filename)

    def _get_output_filename(self, filename: str) -> str:
        if filename:
            filepath, file_extension = os.path.splitext(filename)
            if file_extension != self.FILE_EXTENSION:
                filepath = f"{filepath}.{self.FILE_EXTENSION}"
        else:
            filepath = f"{self.DEFAULT_FILENAME}.{self.FILE_EXTENSION}"

        if not os.path.exists(filepath):
            return filepath

        filepath, file_extension = os.path.splitext(filepath)
        i = 2
        new_fname = f"{filepath}-{i}{file_extension}"
        while os.path.exists(new_fname):
            i += 1
            new_fname = f"{filepath}-{i}{file_extension}"

        return new_fname

    def write_txf(self) -> None:
        if self.filename:
            with open(self.filename, "w", encoding="utf-8") as txt_file:
                self._write_header_record(txt_file)
                for tax_year in sorted(self.tax_report):
                    for asset in sorted(self.tax_report[tax_year]["CapitalGains"].short_term):
                        for te in self.tax_report[tax_year]["CapitalGains"].short_term[asset]:
                            self._write_data_record(txt_file, te, self.TAX_REF_SHORT_TERM)
                    for asset in sorted(self.tax_report[tax_year]["CapitalGains"].long_term):
                        for te in self.tax_report[tax_year]["CapitalGains"].long_term[asset]:
                            self._write_data_record(txt_file, te, self.TAX_REF_LONG_TERM)

            sys.stdout.write(
                f"{Fore.WHITE}{self.OUTPUT_FORMAT} file created: {Fore.YELLOW}{self.filename}\n"
            )

    def _write_header_record(self, txt_file: TextIO) -> None:
        txt_file.write(f"V{self.TXF_VERSION}\n")
        txt_file.write(f"ABittyTax v{__version__}\n")
        txt_file.write(f"D{datetime.datetime.now():%m/%d/%Y}\n")
        txt_file.write("^\n")

    def _write_data_record(self, txt_file: TextIO, te: TaxEventCapitalGains, tax_ref: str) -> None:
        txt_file.write("TD\n")
        txt_file.write(f"N{tax_ref}\n")
        txt_file.write(f"P{te.quantity.normalize():0,f} {te.asset}\n")
        txt_file.write(f"D{self._format_acq_date(te)}\n")
        txt_file.write(f"D{te.date:%m/%d/%Y}\n")
        txt_file.write(f"${te.cost.normalize():0f}\n")
        txt_file.write(f"${te.proceeds.normalize():0f}\n")
        txt_file.write("^\n")

    @staticmethod
    def _format_acq_date(te: TaxEventCapitalGains) -> str:
        acq_date = te.a_date("%m/%d/%Y")
        if acq_date == ACQUISITIONS_VARIOUS and te.disposal_type != DisposalType.LONG_TERM:
            # Lowercase "various" indicates a short-term disposal, uppercase "VARIOUS" is long-term
            return acq_date.lower()
        return acq_date
