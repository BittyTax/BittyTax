# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import csv
import sys
import io

from colorama import Fore, Back
import xlrd

from ..config import config
from .dataparser import DataParser
from .datarow import DataRow
from .exceptions import DataFormatUnrecognised

class DataFile(object):
    FORMAT_EXCEL = 'Excel'
    FORMAT_CSV = 'CSV'

    CSV_DELIMITERS = (',', ';')

    data_files = {}
    data_files_ordered = []

    def __init__(self, file_format, filename, parser, reader):
        self.parser = parser
        self.data_rows = [DataRow(line_num + 1, in_row) for line_num, in_row in enumerate(reader)]

        if parser.row_handler:
            for data_row in self.data_rows:
                if config.args.debug:
                    sys.stderr.write("%sconv: row[%s] %s\n" % (
                        Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))

                data_row.parse(parser, filename)
        else:
            # all rows handled together
            DataRow.parse_all(self.data_rows, parser, filename)

        failures = [data_row for data_row in self.data_rows if data_row.failure is not None]
        if failures:
            sys.stderr.write("%sWARNING%s Parser failure for %s file: %s\n" % (
                Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, file_format, filename))
            for data_row in failures:
                sys.stderr.write("%srow[%s] %s\n" % (
                    Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
                sys.stderr.write("%sERROR%s %s\n" % (
                    Back.RED+Fore.BLACK, Back.RESET+Fore.RED, data_row.failure))

    def __eq__(self, other):
        return (self.parser.row_handler, self.parser.all_handler) == \
               (other.parser.row_handler, other.parser.all_handler)

    def __hash__(self):
        return hash((self.parser.row_handler, self.parser.all_handler))

    def __iadd__(self, other):
        if len(other.parser.header) > len(self.parser.header):
            self.parser = other.parser

        if config.args.duplicates:
            self.data_rows += [data_row
                               for data_row in other.data_rows if data_row not in self.data_rows]
        else:
            self.data_rows += other.data_rows

        return self

    @classmethod
    def read_excel(cls, filename):
        workbook = xlrd.open_workbook(filename)
        if config.args.debug:
            sys.stderr.write("%sconv: EXCEL\n" % Fore.CYAN)

        sheet = workbook.sheet_by_index(0)
        reader = cls.get_cell_values(sheet.get_rows(), workbook)
        parser = cls.get_parser(reader)

        if parser is not None:
            sys.stderr.write("%sfile: %s%s %smatched as %s\"%s\"\n" % (
                Fore.WHITE, Fore.YELLOW, filename, Fore.WHITE, Fore.CYAN, parser.worksheet_name))
            data_file = DataFile(cls.FORMAT_EXCEL, filename, parser, reader)
            cls.consolidate_datafiles(data_file)
        else:
            raise DataFormatUnrecognised

        workbook.release_resources()
        del workbook

    @staticmethod
    def get_cell_values(rows, workbook):
        for row in rows:
            yield [DataFile.convert_cell(cell, workbook) for cell in row]

    @staticmethod
    def convert_cell(cell, workbook):
        if cell.ctype == xlrd.XL_CELL_DATE:
            value = xlrd.xldate.xldate_as_datetime(cell.value, workbook.datemode). \
                         strftime('%Y-%m-%dT%H:%M:%S %Z')
        elif cell.ctype in (xlrd.XL_CELL_NUMBER, xlrd.XL_CELL_BOOLEAN, xlrd.XL_CELL_ERROR):
            # repr is required to ensure no precision is lost
            value = repr(cell.value)
        else:
            if sys.version_info[0] >= 3:
                value = str(cell.value)
            else:
                value = cell.value.encode('utf-8')

        return value

    @classmethod
    def read_csv(cls, filename):
        with io.open(filename, newline='', encoding='utf-8-sig') as csv_file:
            for delimiter in cls.CSV_DELIMITERS:
                if config.args.debug:
                    sys.stderr.write("%sconv: CSV delimiter='%s'\n" % (Fore.CYAN, delimiter))

                if sys.version_info[0] < 3:
                    # special handling required for utf-8 encoded csv files
                    reader = csv.reader(cls.utf_8_encoder(csv_file), delimiter=delimiter)
                else:
                    reader = csv.reader(csv_file, delimiter=delimiter)

                parser = cls.get_parser(reader)
                if parser is not None:
                    sys.stderr.write("%sfile: %s%s %smatched as %s\"%s\"\n" % (
                        Fore.WHITE, Fore.YELLOW, filename, Fore.WHITE,
                        Fore.CYAN, parser.worksheet_name))
                    data_file = DataFile(cls.FORMAT_CSV, filename, parser, reader)
                    cls.consolidate_datafiles(data_file)
                    break
                else:
                    csv_file.seek(0)

        if parser is None:
            raise DataFormatUnrecognised

    @classmethod
    def consolidate_datafiles(cls, data_file):
        if data_file in cls.data_files:
            cls.data_files[data_file] += data_file
        else:
            cls.data_files[data_file] = data_file
            cls.data_files_ordered.append(data_file)

    @staticmethod
    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode('utf-8')

    @staticmethod
    def get_parser(reader):
        parser = None
        # header might not be on first line
        for row in range(8):
            try:
                parser = DataParser.match_header(next(reader), row)
            except KeyError:
                continue
            except StopIteration:
                pass
            except UnicodeDecodeError:
                break
            else:
                break

        return parser
