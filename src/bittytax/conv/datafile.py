# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import csv
import io
import sys
import warnings

import xlrd
from colorama import Fore
from openpyxl import load_workbook

from ..config import config
from ..constants import ERROR, WARNING
from .dataparser import DataParser
from .datarow import DataRow
from .exceptions import DataFormatUnrecognised, DataRowError


class DataFile:
    CSV_DELIMITERS = (",", ";")

    remove_duplicates = False
    data_files = {}
    data_files_ordered = []

    def __init__(self, parser, reader):
        self.parser = parser
        self.data_rows = [
            DataRow(line_num + 1, row, parser.in_header) for line_num, row in enumerate(reader)
        ]
        self.failures = []

    def __eq__(self, other):
        return (self.parser.row_handler, self.parser.all_handler) == (
            other.parser.row_handler,
            other.parser.all_handler,
        )

    def __hash__(self):
        return hash((self.parser.row_handler, self.parser.all_handler))

    def __iadd__(self, other):
        if len(other.parser.header) > len(self.parser.header):
            self.parser = other.parser

        if self.remove_duplicates:
            self.data_rows += [dr for dr in other.data_rows if dr not in self.data_rows]
        else:
            if [dr for dr in other.data_rows if dr in self.data_rows]:
                sys.stderr.write(
                    f'{WARNING} Duplicate rows detected for "{self.parser.name}", '
                    f"use the [--duplicates] option to remove them (use with care)\n"
                )
            self.data_rows += other.data_rows

        return self

    def parse(self, **kwargs):
        if self.parser.row_handler:
            for data_row in self.data_rows:
                if config.debug:
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
                sys.stderr.write(
                    f"{Fore.YELLOW}"
                    f"row[{self.parser.in_header_row_num + data_row.line_num}] {data_row}\n"
                )
                if isinstance(data_row.failure, DataRowError):
                    sys.stderr.write(f"{ERROR} {data_row.failure}\n")
                else:
                    sys.stderr.write(f'{ERROR} Unexpected error: "{data_row.failure}"\n')

    @classmethod
    def read_excel_xlsx(cls, filename):
        warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
        with open(filename, "rb") as df:
            try:
                workbook = load_workbook(df, read_only=False, data_only=True)

                if config.debug:
                    sys.stderr.write(f"{Fore.CYAN}conv: EXCEL\n")

                for sheet_name in workbook.sheetnames:
                    yield workbook[sheet_name]

                workbook.close()
                del workbook
            except (IOError, KeyError) as e:
                raise DataFormatUnrecognised(filename) from e

    @classmethod
    def read_worksheet_xlsx(cls, worksheet, filename, args):
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
    def read_excel_xls(cls, filename):
        try:
            with xlrd.open_workbook(filename) as workbook:
                if config.debug:
                    sys.stderr.write(f"{Fore.CYAN}conv: EXCEL\n")

                for worksheet in workbook.sheets():
                    yield worksheet, workbook.datemode
        except (xlrd.XLRDError, xlrd.compdoc.CompDocError) as e:
            raise DataFormatUnrecognised(filename) from e

    @classmethod
    def read_worksheet_xls(cls, worksheet, datemode, filename, args):
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
    def get_cell_values_xlsx(rows):
        for row in rows:
            yield [DataFile.convert_cell_xlsx(cell) for cell in row]

    @staticmethod
    def convert_cell_xlsx(cell):
        if cell.value is None:
            return ""

        return str(cell.value)

    @staticmethod
    def get_cell_values_xls(rows, datemode):
        for row in rows:
            yield [DataFile.convert_cell_xls(cell, datemode) for cell in row]

    @staticmethod
    def convert_cell_xls(cell, datemode):
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
    def read_csv(cls, filename, args):
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
    def read_csv_with_delimiter(cls, filename):
        with io.open(filename, newline="", encoding="utf-8-sig") as csv_file:
            for delimiter in cls.CSV_DELIMITERS:
                if config.debug:
                    sys.stderr.write(f"{Fore.CYAN}conv: CSV delimiter='{delimiter}'\n")

                yield csv.reader(csv_file, delimiter=delimiter)
                csv_file.seek(0)

    @classmethod
    def consolidate_datafiles(cls, data_file):
        if data_file.parser.p_type != DataParser.TYPE_GENERIC and data_file in cls.data_files:
            cls.data_files[data_file] += data_file
        else:
            cls.data_files[data_file] = data_file
            cls.data_files_ordered.append(data_file)

    @staticmethod
    def get_parser(reader):
        parser = None
        # Header might not be on first line
        for row in range(8):
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
