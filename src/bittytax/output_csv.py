# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import csv
import os
import sys
from abc import ABC, abstractmethod
from typing import Dict, List

import _csv
from colorama import Fore

from .bt_types import DisposalType, Year
from .constants import ACQUISITIONS_VARIOUS
from .tax import TaxReportRecord
from .tax_event import TaxEventCapitalGains


class OutputCapitalGainsCsv(ABC):
    FILE_EXTENSION = "csv"

    def __init__(self, filename: str, tax_report: Dict[Year, TaxReportRecord]) -> None:
        self.tax_report = tax_report
        self.filename = self._get_output_filename(filename)

    @property
    @abstractmethod
    def output_format(self) -> str:
        pass

    @property
    @abstractmethod
    def default_filename(self) -> str:
        pass

    @property
    @abstractmethod
    def header(self) -> List[str]:
        pass

    def _get_output_filename(self, filename: str) -> str:
        if filename:
            filepath, file_extension = os.path.splitext(filename)
            if file_extension != self.FILE_EXTENSION:
                filepath = f"{filepath}.{self.FILE_EXTENSION}"
        else:
            filepath = f"{self.default_filename}.{self.FILE_EXTENSION}"

        if not os.path.exists(filepath):
            return filepath

        filepath, file_extension = os.path.splitext(filepath)
        i = 2
        new_fname = f"{filepath}-{i}{file_extension}"
        while os.path.exists(new_fname):
            i += 1
            new_fname = f"{filepath}-{i}{file_extension}"

        return new_fname

    def write_csv(self) -> None:
        if self.filename:
            with open(self.filename, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file, lineterminator="\n")
                self._write_rows(writer)

            sys.stdout.write(
                f"{Fore.WHITE}{self.output_format} file created: {Fore.YELLOW}{self.filename}\n"
            )

    def _write_rows(self, writer: "_csv._writer") -> None:
        writer.writerow(self.header)

        for tax_year in sorted(self.tax_report):
            for asset in sorted(self.tax_report[tax_year]["CapitalGains"].short_term):
                for te in self.tax_report[tax_year]["CapitalGains"].short_term[asset]:
                    writer.writerow(self._to_csv(te))
            for asset in sorted(self.tax_report[tax_year]["CapitalGains"].long_term):
                for te in self.tax_report[tax_year]["CapitalGains"].long_term[asset]:
                    writer.writerow(self._to_csv(te))

    @staticmethod
    @abstractmethod
    def _to_csv(te: TaxEventCapitalGains) -> List[str]:
        pass


class OutputTurboTaxCsv(OutputCapitalGainsCsv):
    output_format = "TurboTax CSV"
    default_filename = "BittyTax_TurboTax"

    header = [
        "Amount",
        "Currency Name",
        "Purchase Date",
        "Date Sold",
        "Proceeds",
        "Cost Basis",
    ]

    @staticmethod
    def _to_csv(te: TaxEventCapitalGains) -> List[str]:
        if not te.acquisition_dates:
            raise RuntimeError("missing te.acquisition_dates")

        return [
            f"{te.quantity.normalize():0,f}",
            f"{te.asset}",
            f"{OutputTurboTaxCsv._format_acq_date(te)}",
            f"{te.date:%m/%d/%Y}",
            f"{te.proceeds.normalize():0f}",
            f"{te.cost.normalize():0f}",
        ]

    @staticmethod
    def _format_acq_date(te: TaxEventCapitalGains) -> str:
        acq_date = te.a_date("%m/%d/%Y")
        if acq_date == ACQUISITIONS_VARIOUS and te.disposal_type != DisposalType.LONG_TERM:
            # Lowercase "various" indicates a short-term disposal, uppercase "VARIOUS" is long-term
            return acq_date.lower()
        return acq_date


class OutputTaxAct(OutputCapitalGainsCsv):
    output_format = "TaxAct"
    default_filename = "BittyTax_TaxAct"

    header = [
        "Description",
        "Date Acquired",
        "Date Sold",
        "Sales Proceeds",
        "Cost or Other Basis",
        "Long/Short",
    ]

    @staticmethod
    def _to_csv(te: TaxEventCapitalGains) -> List[str]:
        return [
            f"{te.quantity.normalize():0,f} {te.asset}",
            te.a_date("%m/%d/%Y"),
            f"{te.date:%m/%d/%Y}",
            f"{te.proceeds.normalize():0f}",
            f"{te.cost.normalize():0f}",
            OutputTaxAct._format_disposal(te.disposal_type),
        ]

    @staticmethod
    def _format_disposal(disposal_type: DisposalType) -> str:
        if disposal_type is DisposalType.LONG_TERM:
            return "LONG"
        if disposal_type is DisposalType.SHORT_TERM:
            return "SHORT"
        raise RuntimeError("Unexpected disposal_type")
