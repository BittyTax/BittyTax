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
    CSV_DELIMITERS = (',', ';')

    remove_duplicates = False
    data_files = {}
    data_files_ordered = []

    def __init__(self, parser, reader):
        self.parser = parser
        self.data_rows = [DataRow(line_num + 1, row, parser.in_header)
                          for line_num, row in enumerate(reader)]
        self.failures = []

    def __eq__(self, other):
        return (self.parser.row_handler, self.parser.all_handler) == \
               (other.parser.row_handler, other.parser.all_handler)

    def __hash__(self):
        return hash((self.parser.row_handler, self.parser.all_handler))

    def __iadd__(self, other):
        if len(other.parser.header) > len(self.parser.header):
            self.parser = other.parser

        if self.remove_duplicates:
            self.data_rows += [data_row
                               for data_row in other.data_rows if data_row not in self.data_rows]
        else:
            self.data_rows += other.data_rows

        return self

    def parse(self, **kwargs):
        if self.parser.row_handler:
            for data_row in self.data_rows:
                if config.debug:
                    sys.stderr.write("%sconv: row[%s] %s\n" % (
                        Fore.YELLOW, self.parser.in_header_row_num + data_row.line_num, data_row))

                data_row.parse(self.parser, **kwargs)
        else:
            # all rows handled together
            DataRow.parse_all(self.data_rows, self.parser, **kwargs)

        self.failures = [data_row for data_row in self.data_rows if data_row.failure is not None]

    @classmethod
    def read_excel(cls, filename):
        with xlrd.open_workbook(filename) as workbook:
            if config.debug:
                sys.stderr.write("%sconv: EXCEL\n" % Fore.CYAN)

            for worksheet in workbook.sheets():
                yield (worksheet, workbook.datemode)

    @classmethod
    def read_worksheet(cls, worksheet, datemode, filename, args):
        reader = cls.get_cell_values(worksheet.get_rows(), datemode)
        parser = cls.get_parser(reader)

        if parser is None:
            raise DataFormatUnrecognised(filename, worksheet.name)

        sys.stderr.write("%sfile: %s%s '%s' %smatched as %s\"%s\"\n" % (
            Fore.WHITE, Fore.YELLOW, filename, worksheet.name,
            Fore.WHITE, Fore.CYAN, parser.worksheet_name))

        data_file = DataFile(parser, reader)
        data_file.parse(filename=filename,
                        worksheet=worksheet.name,
                        unconfirmed=args.unconfirmed,
                        cryptoasset=args.cryptoasset)

        if data_file.failures:
            sys.stderr.write("%sWARNING%s Parser failure for Excel file: %s '%s'\n" % (
                Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, filename, worksheet.name))
            for data_row in data_file.failures:
                sys.stderr.write("%srow[%s] %s\n" % (
                    Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
                sys.stderr.write("%sERROR%s %s\n" % (
                    Back.RED+Fore.BLACK, Back.RESET+Fore.RED, data_row.failure))

        cls.consolidate_datafiles(data_file)

    @staticmethod
    def get_cell_values(rows, datemode):
        for row in rows:
            yield [DataFile.convert_cell(cell, datemode) for cell in row]

    @staticmethod
    def convert_cell(cell, datemode):
        if cell.ctype == xlrd.XL_CELL_DATE:
            value = xlrd.xldate.xldate_as_datetime(cell.value, datemode). \
                         strftime('%Y-%m-%dT%H:%M:%S.%f %Z')
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
    def read_csv(cls, filename, args):
        for reader in cls.read_csv_with_delimiter(filename):
            parser = cls.get_parser(reader)

            if parser is not None:
                sys.stderr.write("%sfile: %s%s %smatched as %s\"%s\"\n" % (
                    Fore.WHITE, Fore.YELLOW, filename, Fore.WHITE,
                    Fore.CYAN, parser.worksheet_name))

                data_file = DataFile(parser, reader)
                data_file.parse(filename=filename,
                                unconfirmed=args.unconfirmed,
                                cryptoasset=args.cryptoasset)

                if data_file.failures:
                    sys.stderr.write("%sWARNING%s Parser failure for CSV file: %s\n" % (
                        Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, filename))
                    for data_row in data_file.failures:
                        sys.stderr.write("%srow[%s] %s\n" % (
                            Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
                        sys.stderr.write("%sERROR%s %s\n" % (
                            Back.RED+Fore.BLACK, Back.RESET+Fore.RED, data_row.failure))

                cls.consolidate_datafiles(data_file)
                break

        if parser is None:
            raise DataFormatUnrecognised(filename)

    @classmethod
    def read_csv_with_delimiter(cls, filename):
        with io.open(filename, newline='', encoding='utf-8-sig') as csv_file:
            for delimiter in cls.CSV_DELIMITERS:
                if config.debug:
                    sys.stderr.write("%sconv: CSV delimiter='%s'\n" % (Fore.CYAN, delimiter))

                if sys.version_info[0] < 3:
                    # special handling required for utf-8 encoded csv files
                    reader = csv.reader(cls.utf_8_encoder(csv_file), delimiter=delimiter)
                else:
                    reader = csv.reader(csv_file, delimiter=delimiter)

                yield reader
                csv_file.seek(0)

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
