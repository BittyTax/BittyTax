# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import csv
import os
import sys
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List

import _csv
from colorama import Fore

from .bt_types import Year
from .tax import TaxReportRecord
from .tax_event import TaxEventCapitalGains


class HoldingPeriod(Enum):
    SHORT = "SHORT"
    LONG = "LONG"


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

            sys.stderr.write(
                f"{Fore.WHITE}{self.output_format} file created: {Fore.YELLOW}{self.filename}\n"
            )

    def _write_rows(self, writer: "_csv._writer") -> None:
        writer.writerow(self.header)

        for tax_year in sorted(self.tax_report):
            for asset in sorted(self.tax_report[tax_year]["CapitalGains"].short_term):
                for te in self.tax_report[tax_year]["CapitalGains"].short_term[asset]:
                    writer.writerow(self._to_csv(te, HoldingPeriod.SHORT))
            for asset in sorted(self.tax_report[tax_year]["CapitalGains"].long_term):
                for te in self.tax_report[tax_year]["CapitalGains"].long_term[asset]:
                    writer.writerow(self._to_csv(te, HoldingPeriod.LONG))

    @staticmethod
    @abstractmethod
    def _to_csv(te: TaxEventCapitalGains, _holding_period: HoldingPeriod) -> List[str]:
        pass


class OutputTurboTax(OutputCapitalGainsCsv):
    output_format = "TurboTax"
    default_filename = "TurboTax"

    header = [
        "Purchase Date",
        "Date Sold",
        "Proceeds",
        "Cost Basis",
        "Currency Name",
    ]

    @staticmethod
    def _to_csv(te: TaxEventCapitalGains, _holding_period: HoldingPeriod) -> List[str]:
        if not te.acquisition_dates:
            raise RuntimeError("missing te.acquisition_dates")

        return [
            ", ".join([f"{d:%m/%d/%Y}" for d in sorted(set(te.acquisition_dates))]),
            f"{te.date:%m/%d/%Y}",
            f"{te.proceeds.normalize():0f}",
            f"{te.cost.normalize():0f}",
            f"{te.asset} {te.quantity.normalize():0,f}",
        ]


class OutputTaxAct(OutputCapitalGainsCsv):
    output_format = "TaxAct"
    default_filename = "TaxAct"

    header = [
        "Description",
        "Date Acquired",
        "Date Sold",
        "Sales Proceeds",
        "Cost or Other Basis",
        "Long/Short",
    ]

    @staticmethod
    def _to_csv(te: TaxEventCapitalGains, holding_period: HoldingPeriod) -> List[str]:
        return [
            f"{te.asset} {te.quantity.normalize():0,f}",
            te.a_date("%m/%d/%Y"),
            f"{te.date:%m/%d/%Y}",
            f"{te.proceeds.normalize():0f}",
            f"{te.cost.normalize():0f}",
            holding_period.value,
        ]
