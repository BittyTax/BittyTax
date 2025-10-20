# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import argparse
import copy
import csv
import io
import os
import sys
import warnings
from typing import Dict, Iterator, List, Optional, Tuple

import openpyxl
import xlrd
from colorama import Fore
from typing_extensions import Unpack

from ..config import config
from ..constants import ERROR, WARNING
from .dataparser import ConsolidateType, DataParser, ParserArgs
from .datarow import DataRow
from .exceptions import DataFormatUnrecognised, DataRowError


class DataFile:
    CSV_DELIMITERS = (",", ";")

    remove_duplicates = False
    data_files: Dict["DataFile", "DataFile"] = {}
    data_files_ordered: List["DataFile"] = []

    def __init__(self, parser: DataParser, reader: Iterator[List[str]]) -> None:
        self.parser = copy.copy(parser)
        self.data_rows = [
            DataRow(line_num + 1, row, parser.in_header, parser.worksheet_name)
            for line_num, row in enumerate(reader)
        ]
        self.failures: List[DataRow] = []

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DataFile):
            return NotImplemented

        if self.parser.consolidate_type is ConsolidateType.HEADER_MATCH:
            return (
                self.parser.row_handler,
                self.parser.all_handler,
                tuple(self.parser.in_header),
            ) == (
                other.parser.row_handler,
                other.parser.all_handler,
                tuple(other.parser.in_header),
            )
        return (self.parser.row_handler, self.parser.all_handler) == (
            other.parser.row_handler,
            other.parser.all_handler,
        )

    def __hash__(self) -> int:
        if self.parser.consolidate_type is ConsolidateType.HEADER_MATCH:
            return hash(
                (self.parser.row_handler, self.parser.all_handler, tuple(self.parser.in_header))
            )
        return hash((self.parser.row_handler, self.parser.all_handler))

    def __iadd__(self, other: "DataFile") -> "DataFile":
        if len(other.parser.header) > len(self.parser.header):
            self.parser = other.parser

        if self.remove_duplicates:
            self.data_rows += [dr for dr in other.data_rows if dr not in self.data_rows]
        else:
            # Checking for duplicates can be very slow for large files
            if not config.large_data:
                duplicates = [dr for dr in other.data_rows if dr in self.data_rows]
                if duplicates:
                    sys.stderr.write(
                        f'{WARNING} Duplicate rows detected for "{self.parser.name}", '
                        f"use the [--duplicates] option to remove them (use with care)\n"
                    )
                    if config.debug:
                        for dr in duplicates:
                            if self.parser.in_header_row_num is None:
                                raise RuntimeError("Missing in_header_row_num")

                            sys.stderr.write(
                                f"{Fore.CYAN}duplicate: "
                                f"row[{self.parser.in_header_row_num + dr.line_num}] {dr}\n"
                            )
            self.data_rows += other.data_rows

        return self

    def parse(self, **kwargs: Unpack[ParserArgs]) -> None:
        if self.parser.row_handler:
            for data_row in self.data_rows:
                if config.debug:
                    if self.parser.in_header_row_num is None:
                        raise RuntimeError("Missing in_header_row_num")

                    sys.stderr.write(
                        f"{Fore.YELLOW}conv: "
                        f"row[{self.parser.in_header_row_num + data_row.line_num}] {data_row}\n"
                    )

                data_row.parse(self.parser, **kwargs)
        else:
            # All rows handled together
            DataRow.parse_all(self.data_rows, self.parser, **kwargs)

        self.failures = [dr for dr in self.data_rows if dr.failure is not None]

        if self.failures:
            sys.stderr.write(f'{WARNING} Parser failure for "{self.parser.name}"\n')

            for data_row in self.failures:
                if self.parser.in_header_row_num is None:
                    raise RuntimeError("Missing in_header_row_num")

                sys.stderr.write(
                    f"{Fore.YELLOW}"
                    f"row[{self.parser.in_header_row_num + data_row.line_num}] {data_row}\n"
                )
                if isinstance(data_row.failure, DataRowError):
                    sys.stderr.write(f"{ERROR} {data_row.failure}\n")
                else:
                    sys.stderr.write(f'{ERROR} Unexpected error: "{data_row.failure}"\n')

    @classmethod
    def read_excel_xlsx(cls, filename: str) -> Iterator[xlrd.sheet.Sheet]:
        warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
        with open(filename, "rb") as df:
            try:
                workbook = openpyxl.load_workbook(
                    df,
                    read_only=True,
                    data_only=True,
                    keep_vba=False,
                    keep_links=False,
                    rich_text=False,
                )

                if config.debug:
                    sys.stderr.write(f"{Fore.CYAN}conv: EXCEL\n")

                for sheet_name in workbook.sheetnames:
                    try:
                        dimensions = workbook[sheet_name].calculate_dimension()
                    except ValueError:
                        workbook[sheet_name].reset_dimensions()
                    else:
                        if dimensions == "A1:A1" or dimensions.endswith("1048576"):
                            workbook[sheet_name].reset_dimensions()

                    yield workbook[sheet_name]

                workbook.close()
                del workbook
            except (IOError, KeyError) as e:
                raise DataFormatUnrecognised(filename) from e

    @classmethod
    def read_worksheet_xlsx(
        cls,
        worksheet: openpyxl.worksheet.worksheet.Worksheet,
        filename: str,
        args: argparse.Namespace,
    ) -> None:
        reader = cls.get_cell_values_xlsx(worksheet.rows)
        parser = cls.get_parser(reader)

        if parser is None:
            raise DataFormatUnrecognised(filename, worksheet.title)

        sys.stderr.write(
            f"{Fore.WHITE}file: {Fore.YELLOW}{filename} '{worksheet.title}' "
            f'{Fore.WHITE}matched as {Fore.CYAN}"{parser.name}"\n'
        )

        if parser.deprecated:
            sys.stderr.write(
                f'{WARNING} This parser is deprecated, please use "{parser.deprecated.name}"\n'
            )

        data_file = DataFile(parser, reader)
        data_file.parse(
            filename=filename,
            worksheet=worksheet.title,
            unconfirmed=args.unconfirmed,
            cryptoasset=args.cryptoasset,
        )

        cls.consolidate_datafiles(data_file)

    @classmethod
    def read_excel_xls(cls, filename: str) -> Iterator[Tuple[xlrd.sheet.Sheet, int]]:
        try:
            with xlrd.open_workbook(
                filename, logfile=open(os.devnull, "w", encoding="utf-8")
            ) as workbook:
                if config.debug:
                    sys.stderr.write(f"{Fore.CYAN}conv: EXCEL\n")

                for worksheet in workbook.sheets():
                    yield worksheet, workbook.datemode
        except (xlrd.XLRDError, xlrd.compdoc.CompDocError) as e:
            raise DataFormatUnrecognised(filename) from e

    @classmethod
    def read_worksheet_xls(
        cls, worksheet: xlrd.sheet.Sheet, datemode: int, filename: str, args: argparse.Namespace
    ) -> None:
        reader = cls.get_cell_values_xls(worksheet.get_rows(), datemode)
        parser = cls.get_parser(reader)

        if parser is None:
            raise DataFormatUnrecognised(filename, worksheet.name)

        sys.stderr.write(
            f"{Fore.WHITE}file: {Fore.YELLOW}{filename} '{worksheet.name}' "
            f'{Fore.WHITE}matched as {Fore.CYAN}"{parser.name}"\n'
        )

        if parser.deprecated:
            sys.stderr.write(
                f'{WARNING} This parser is deprecated, please use "{parser.deprecated.name}"\n'
            )

        data_file = DataFile(parser, reader)
        data_file.parse(
            filename=filename,
            worksheet=worksheet.name,
            unconfirmed=args.unconfirmed,
            cryptoasset=args.cryptoasset,
        )

        cls.consolidate_datafiles(data_file)

    @staticmethod
    def get_cell_values_xlsx(rows: List[openpyxl.cell.cell.Cell]) -> Iterator[List[str]]:
        for row in rows:
            yield [DataFile.convert_cell_xlsx(cell) for cell in row]

    @staticmethod
    def convert_cell_xlsx(cell: openpyxl.cell.cell.Cell) -> str:
        if cell.value is None:
            return ""
        return str(cell.value)

    @staticmethod
    def get_cell_values_xls(
        rows: Iterator[List[xlrd.sheet.Cell]], datemode: int
    ) -> Iterator[List[str]]:
        for row in rows:
            yield [DataFile.convert_cell_xls(cell, datemode) for cell in row]

    @staticmethod
    def convert_cell_xls(cell: xlrd.sheet.Cell, datemode: int) -> str:
        if cell.ctype == xlrd.XL_CELL_DATE:
            value = (
                f"{xlrd.xldate.xldate_as_datetime(cell.value, datemode):%Y-%m-%dT%H:%M:%S.%f %Z}"
            )
        elif cell.ctype in (
            xlrd.XL_CELL_NUMBER,
            xlrd.XL_CELL_BOOLEAN,
            xlrd.XL_CELL_ERROR,
        ):
            # repr is required to ensure no precision is lost
            value = repr(cell.value)
        else:
            value = str(cell.value)

        return value

    @classmethod
    def read_csv(cls, filename: str, args: argparse.Namespace) -> None:
        for reader in cls.read_csv_with_delimiter(filename):
            parser = cls.get_parser(reader)

            if parser is not None:
                sys.stderr.write(
                    f"{Fore.WHITE}file: {Fore.YELLOW}{filename} "
                    f'{Fore.WHITE}matched as {Fore.CYAN}"{parser.name}"\n'
                )

                if parser.deprecated:
                    sys.stderr.write(
                        f"{WARNING} This parser is deprecated, please use "
                        f'"{parser.deprecated.name}"\n'
                    )

                data_file = DataFile(parser, reader)
                data_file.parse(
                    filename=filename,
                    unconfirmed=args.unconfirmed,
                    cryptoasset=args.cryptoasset,
                )

                cls.consolidate_datafiles(data_file)
                break

        if parser is None:
            raise DataFormatUnrecognised(filename)

    @classmethod
    def read_csv_with_delimiter(cls, filename: str) -> Iterator[Iterator[List[str]]]:
        with io.open(filename, newline="", encoding="utf-8-sig") as csv_file:
            for delimiter in cls.CSV_DELIMITERS:
                if config.debug:
                    sys.stderr.write(f"{Fore.CYAN}conv: CSV delimiter='{delimiter}'\n")

                yield csv.reader(csv_file, delimiter=delimiter)
                csv_file.seek(0)

    @classmethod
    def consolidate_datafiles(cls, data_file: "DataFile") -> None:
        if (
            data_file.parser.consolidate_type is not ConsolidateType.NEVER
            and data_file in cls.data_files
        ):
            cls.data_files[data_file] += data_file
        else:
            cls.data_files[data_file] = data_file
            cls.data_files_ordered.append(data_file)

    @staticmethod
    def get_parser(reader: Iterator[List[str]]) -> Optional[DataParser]:
        parser = None
        # Header might not be on first line
        for row in range(14):
            try:
                parser = DataParser.match_header(next(reader), row)
            except KeyError:
                continue
            except StopIteration:
                pass
            except (UnicodeDecodeError, csv.Error):
                break
            else:
                break

        return parser
