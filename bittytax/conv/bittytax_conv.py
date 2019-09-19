# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import argparse
import csv
import sys
import io

import xlrd
from future.utils import raise_from

from ..version import __version__
from ..config import config
from .dataparser import DataParser
from .parsers import *
from .out_record import TransactionOutRecord

CSV_DELIMITERS = (',', ';')

if sys.version_info[0] >= 3:
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(stream=sys.stderr,
                    level=logging.INFO,
                    format='[%(asctime)s.%(msecs)03d] %(levelname)s -- : %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S')
log = logging.getLogger()

def _open_excel_file(workbook):
    sheet = workbook.sheet_by_index(0)

    reader = _get_cell_values(sheet.get_rows(), workbook)
    all_in_row, t_records, in_header = _parse_file(reader)
    TransactionOutRecord.csv_file(all_in_row, t_records, in_header)
    workbook.release_resources()
    del workbook

def _get_cell_values(rows, workbook):
    for row in rows:
        yield [_convert_cell(cell, workbook) for cell in row]

def _convert_cell(cell, workbook):
    if cell.ctype == xlrd.XL_CELL_DATE:
        value = xlrd.xldate.xldate_as_datetime(cell.value, workbook.datemode). \
                    strftime('%Y-%m-%dT%H:%M:%S %Z')
    elif cell.ctype == xlrd.XL_CELL_NUMBER:
        # repr is required to ensure no precision is lost
        value = repr(cell.value)
    else:
        value = str(cell.value)

    return value

def _open_csv_file(filename, delimiter):
    with io.open(filename, newline='', encoding='utf-8-sig') as data_file:
        if sys.version_info[0] < 3:
            # special handling required for utf-8 encoded csv files
            reader = csv.reader(_utf_8_encoder(data_file), delimiter=delimiter)
        else:
            reader = csv.reader(data_file, delimiter=delimiter)

        all_in_row, t_records, in_header = _parse_file(reader)
        TransactionOutRecord.csv_file(all_in_row, t_records, in_header)

    data_file.close()

def _utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')

def _parse_file(reader):
    parser = None
    # header might not be on first line
    for row in range(5):
        try:
            log.debug("Row:%d", row)
            parser = DataParser.match_header(next(reader))
        except KeyError:
            continue
        except StopIteration:
            pass
        else:
            break

    if parser is None:
        raise KeyError("Data file format unrecognised")

    if parser.row_handler:
        all_in_row = []
        t_records = []

        for in_row in reader:
            all_in_row.append(in_row)
            t_records.append(parser.row_handler(in_row, *parser.args))
    else:
        # all rows handled together
        all_in_row = list(reader)
        t_records = parser.all_handler(all_in_row, *parser.args)

    return all_in_row, t_records, parser.in_header

def main():
    parser = argparse.ArgumentParser(epilog="supported data file formats:\n" + \
                                     DataParser.format_parsers(),
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("filename",
                        type=str,
                        nargs='+',
                        help="filename of data file")
    parser.add_argument("-v",
                        "--version",
                        action='version',
                        version='%(prog)s {version}'.format(version=__version__))
    parser.add_argument("-d",
                        "--debug",
                        action='store_true',
                        help="enabled debug logging")
    parser.add_argument("-uc",
                        "--unconfirmed",
                        action='store_true',
                        help="include unconfirmed transactions")
    parser.add_argument("-ca",
                        dest="cryptoasset",
                        type=str,
                        help="specify a cryptoasset symbol, if it cannot be identified "
                             "automatically")
    parser.add_argument("-nh",
                        "--noheader",
                        action='store_true',
                        help="exclude header from CSV output")
    parser.add_argument("-a",
                        "--append",
                        action='store_true',
                        help="append original data as extra columns in the CSV output")
    parser.add_argument("--format",
                        choices=['CSV', 'RECAP'],
                        default='CSV',
                        type=str.upper,
                        help="specify the output format")
    parser.add_argument("-s",
                        "--sort",
                        action='store_true',
                        help="sort output by timestamp")

    config.args = parser.parse_args()

    if config.args.debug:
        log.setLevel(logging.DEBUG)
        config.output_config(parser.prog)

    for filename in config.args.filename:
        try:
            log.debug("EXCEL")
            workbook = xlrd.open_workbook(filename)
        except xlrd.XLRDError:
            for delimiter in CSV_DELIMITERS:
                log.debug("CSV, delimiter='%s'", delimiter)
                try:
                    key_error = None
                    _open_csv_file(filename, delimiter=delimiter)
                except KeyError as e:
                    # Try with next delimiter
                    key_error = e
                    continue
                else:
                    break

            if key_error is not None:
                raise_from(key_error, None)
        else:
            _open_excel_file(workbook)

        config.args.noheader = True
