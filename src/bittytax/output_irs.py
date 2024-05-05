# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import os
import re
from decimal import Decimal
from typing import Dict, List, Optional

import pkg_resources
from colorama import Fore
from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import NameObject, create_string_object
from typing_extensions import TypedDict

from .bt_types import AssetSymbol, Year
from .constants import WARNING
from .report import ProgressSpinner
from .tax import CapitalGainsReportTotal, TaxReportRecord
from .tax_event import TaxEventCapitalGains


class RowFieldNames(TypedDict):  # pylint: disable=too-few-public-methods
    description: str
    date_acq: str
    date_sold: str
    proceeds: str
    cost: str
    gain: str


class FormFieldNames:  # pylint: disable=too-few-public-methods
    TICK_BOX_3 = "/3"

    def __init__(self, fnum: int) -> None:
        ROWS: List[RowFieldNames] = [
            {
                "description": f"f{fnum}_3[0]",
                "date_acq": f"f{fnum}_4[0]",
                "date_sold": f"f{fnum}_5[0]",
                "proceeds": f"f{fnum}_6[0]",
                "cost": f"f{fnum}_7[0]",
                "gain": f"f{fnum}_10[0]",
            },
            {
                "description": f"f{fnum}_11[0]",
                "date_acq": f"f{fnum}_12[0]",
                "date_sold": f"f{fnum}_13[0]",
                "proceeds": f"f{fnum}_14[0]",
                "cost": f"f{fnum}_15[0]",
                "gain": f"f{fnum}_18[0]",
            },
            {
                "description": f"f{fnum}_19[0]",
                "date_acq": f"f{fnum}_20[0]",
                "date_sold": f"f{fnum}_21[0]",
                "proceeds": f"f{fnum}_22[0]",
                "cost": f"f{fnum}_23[0]",
                "gain": f"f{fnum}_26[0]",
            },
            {
                "description": f"f{fnum}_27[0]",
                "date_acq": f"f{fnum}_28[0]",
                "date_sold": f"f{fnum}_29[0]",
                "proceeds": f"f{fnum}_30[0]",
                "cost": f"f{fnum}_31[0]",
                "gain": f"f{fnum}_34[0]",
            },
            {
                "description": f"f{fnum}_35[0]",
                "date_acq": f"f{fnum}_36[0]",
                "date_sold": f"f{fnum}_37[0]",
                "proceeds": f"f{fnum}_38[0]",
                "cost": f"f{fnum}_39[0]",
                "gain": f"f{fnum}_42[0]",
            },
            {
                "description": f"f{fnum}_43[0]",
                "date_acq": f"f{fnum}_44[0]",
                "date_sold": f"f{fnum}_45[0]",
                "proceeds": f"f{fnum}_46[0]",
                "cost": f"f{fnum}_47[0]",
                "gain": f"f{fnum}_50[0]",
            },
            {
                "description": f"f{fnum}_51[0]",
                "date_acq": f"f{fnum}_52[0]",
                "date_sold": f"f{fnum}_53[0]",
                "proceeds": f"f{fnum}_54[0]",
                "cost": f"f{fnum}_55[0]",
                "gain": f"f{fnum}_58[0]",
            },
            {
                "description": f"f{fnum}_59[0]",
                "date_acq": f"f{fnum}_60[0]",
                "date_sold": f"f{fnum}_61[0]",
                "proceeds": f"f{fnum}_62[0]",
                "cost": f"f{fnum}_63[0]",
                "gain": f"f{fnum}_66[0]",
            },
            {
                "description": f"f{fnum}_67[0]",
                "date_acq": f"f{fnum}_68[0]",
                "date_sold": f"f{fnum}_69[0]",
                "proceeds": f"f{fnum}_70[0]",
                "cost": f"f{fnum}_71[0]",
                "gain": f"f{fnum}_74[0]",
            },
            {
                "description": f"f{fnum}_75[0]",
                "date_acq": f"f{fnum}_76[0]",
                "date_sold": f"f{fnum}_77[0]",
                "proceeds": f"f{fnum}_78[0]",
                "cost": f"f{fnum}_79[0]",
                "gain": f"f{fnum}_82[0]",
            },
            {
                "description": f"f{fnum}_83[0]",
                "date_acq": f"f{fnum}_84[0]",
                "date_sold": f"f{fnum}_85[0]",
                "proceeds": f"f{fnum}_86[0]",
                "cost": f"f{fnum}_87[0]",
                "gain": f"f{fnum}_90[0]",
            },
            {
                "description": f"f{fnum}_91[0]",
                "date_acq": f"f{fnum}_92[0]",
                "date_sold": f"f{fnum}_93[0]",
                "proceeds": f"f{fnum}_94[0]",
                "cost": f"f{fnum}_95[0]",
                "gain": f"f{fnum}_98[0]",
            },
            {
                "description": f"f{fnum}_99[0]",
                "date_acq": f"f{fnum}_100[0]",
                "date_sold": f"f{fnum}_101[0]",
                "proceeds": f"f{fnum}_102[0]",
                "cost": f"f{fnum}_103[0]",
                "gain": f"f{fnum}_106[0]",
            },
            {
                "description": f"f{fnum}_107[0]",
                "date_acq": f"f{fnum}_108[0]",
                "date_sold": f"f{fnum}_109[0]",
                "proceeds": f"f{fnum}_110[0]",
                "cost": f"f{fnum}_111[0]",
                "gain": f"f{fnum}_114[0]",
            },
        ]

        self.name = f"f{fnum}_1[0]"
        self.ssn = f"f{fnum}_2[0]"
        self.checkbox_3 = f"c{fnum}_1[2]"
        self.rows = ROWS
        self.total_proceeds = f"f{fnum}_115[0]"
        self.total_cost = f"f{fnum}_116[0]"
        self.total_gain = f"f{fnum}_119[0]"

    def row(self, row_num: int) -> RowFieldNames:
        return self.rows[row_num]


class OutputIrs:
    DEFAULT_FILENAME = "BittyTax_IRS"
    FILE_EXTENSION = "pdf"
    OUTPUT_FORMAT = "Form 8949"

    IRS_FORMS_DIR = pkg_resources.resource_filename(__name__, "irs_forms")
    F8949_PDF: Dict[Year, str] = {
        Year(2018): f"{IRS_FORMS_DIR}/f8949--2018.pdf",
        Year(2019): f"{IRS_FORMS_DIR}/f8949--2019.pdf",
        Year(2020): f"{IRS_FORMS_DIR}/f8949--2020.pdf",
        Year(2021): f"{IRS_FORMS_DIR}/f8949--2021.pdf",
        Year(2022): f"{IRS_FORMS_DIR}/f8949--2022.pdf",
        Year(2023): f"{IRS_FORMS_DIR}/f8949--2023.pdf",
    }

    def __init__(self, filename: str, tax_report: Dict[Year, TaxReportRecord]) -> None:
        self.tax_report = tax_report
        self.filename = filename
        self.name = ""
        self.ssn = ""
        self.page_num = 0
        self.f_num = 0
        self.writer: Optional[PdfWriter] = None
        self.reader: Optional[PdfReader] = None

    def _get_output_filename(self, tax_year: Year) -> str:
        if self.filename:
            filepath, file_extension = os.path.splitext(self.filename)
            filepath = f"{filepath}-{tax_year}.{self.FILE_EXTENSION}"
        else:
            filepath = f"{self.DEFAULT_FILENAME}-{tax_year}.{self.FILE_EXTENSION}"

        if not os.path.exists(filepath):
            return filepath

        filepath, file_extension = os.path.splitext(filepath)
        i = 2
        new_fname = f"{filepath}-{i}{file_extension}"
        while os.path.exists(new_fname):
            i += 1
            new_fname = f"{filepath}-{i}{file_extension}"

        return new_fname

    def write_pdf(self) -> None:
        for tax_year in sorted(self.tax_report):
            if tax_year not in self.F8949_PDF:
                print(f"{WARNING} {self.OUTPUT_FORMAT} for {tax_year} missing, skipping...")
                continue

            self._get_name_ssn()

            with ProgressSpinner(
                f"{Fore.CYAN}generating {self.OUTPUT_FORMAT} for {tax_year}{Fore.GREEN}: "
            ):
                self._make_f8949_pdf(tax_year)
                if self.writer:
                    filename = self._get_output_filename(tax_year)
                    with open(filename, "wb") as output_stream:
                        self.writer.write(output_stream)

            print(
                f"{Fore.WHITE}{self.OUTPUT_FORMAT} for {tax_year} created: {Fore.YELLOW}{filename}"
            )

    def _get_name_ssn(self) -> None:
        if not self.name:
            self.name = input("Enter Name: ")

        if not self.ssn:
            self.ssn = input("Enter SSN or TIN: ")

    def _make_f8949_pdf(self, tax_year: Year) -> None:
        self.reader = PdfReader(self.F8949_PDF[tax_year])
        self.writer = PdfWriter()
        self.writer.clone_reader_document_root(self.reader)

        self.page_num = 0
        self.f_num = 2

        fn = FormFieldNames(1)
        self._fill_header(fn)
        fn = self._fill_table(
            self.tax_report[tax_year]["CapitalGains"].short_term, fn, self.reader.pages[0]
        )
        self._fill_totals(self.tax_report[tax_year]["CapitalGains"].short_term_totals, fn)

        self.page_num += 1
        fn = FormFieldNames(2)
        self._fill_header(fn)
        fn = self._fill_table(
            self.tax_report[tax_year]["CapitalGains"].long_term, fn, self.reader.pages[1]
        )
        self._fill_totals(self.tax_report[tax_year]["CapitalGains"].long_term_totals, fn)

    def _update_page_field_names(self, source_page: PageObject, fnum_new: int) -> None:
        for j in range(0, len(source_page["/Annots"])):  # type: ignore[arg-type]
            writer_annot = source_page["/Annots"][j].get_object()  # type: ignore[index]
            match = re.match(r"(f|c)(\d+)_\d{1,3}\[\d\]", writer_annot.get("/T"))

            if not match:
                raise RuntimeError("Unexpected field name")

            tag = match.group(1)
            fnum_old = match.group(2)
            writer_annot.update(
                {
                    NameObject("/T"): create_string_object(
                        writer_annot.get("/T").replace(f"{tag}{fnum_old}_", f"{tag}{fnum_new}_")
                    )
                }
            )

    def _fill_header(self, fn: FormFieldNames) -> None:
        if self.writer:
            self.writer.update_page_form_field_values(
                self.writer.pages[self.page_num],
                {fn.name: self.name, fn.ssn: self.ssn, fn.checkbox_3: fn.TICK_BOX_3},
                auto_regenerate=False,
            )

    def _fill_table(
        self,
        cgains: Dict[AssetSymbol, List[TaxEventCapitalGains]],
        fn: FormFieldNames,
        source_page: PageObject,
    ) -> FormFieldNames:
        row_num = 0

        for asset in sorted(cgains):
            for te in cgains[asset]:
                if row_num > 13:
                    self.page_num += 1
                    self.f_num += 1
                    row_num = 0

                    self._update_page_field_names(source_page, self.f_num)
                    if self.writer:
                        self.writer.reset_translation(self.reader)
                        self.writer.insert_page(source_page, self.page_num)

                    fn = FormFieldNames(self.f_num)
                    self._fill_header(fn)

                self._fill_row(te, fn, row_num)
                row_num += 1
        return fn

    def _fill_row(self, te: TaxEventCapitalGains, fn: FormFieldNames, row_num: int) -> None:
        if self.writer:
            self.writer.update_page_form_field_values(
                self.writer.pages[self.page_num],
                {
                    fn.row(row_num)["description"]: f"\n{te.quantity.normalize():0,f} {te.asset}",
                    fn.row(row_num)["date_acq"]: te.a_date("%m/%d/%Y"),
                    fn.row(row_num)["date_sold"]: f"{te.date:%m/%d/%Y}",
                    fn.row(row_num)["proceeds"]: self.format_value(te.proceeds),
                    fn.row(row_num)["cost"]: self.format_value(te.cost),
                    fn.row(row_num)["gain"]: self.format_value(te.gain),
                },
                auto_regenerate=False,
            )

    def _fill_totals(self, cgains_totals: CapitalGainsReportTotal, fn: FormFieldNames) -> None:
        if self.writer:
            self.writer.update_page_form_field_values(
                self.writer.pages[self.page_num],
                {
                    fn.total_proceeds: self.format_value(cgains_totals["proceeds"]),
                    fn.total_cost: self.format_value(cgains_totals["cost"]),
                    fn.total_gain: self.format_value(cgains_totals["gain"]),
                },
                auto_regenerate=False,
            )

    @staticmethod
    def format_value(value: Decimal) -> str:
        if value < 0:
            return f"({abs(value):0,.2f})"
        return f"{value:0,.2f}"
