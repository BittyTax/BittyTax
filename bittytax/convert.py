# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import argparse
import csv
import sys
import io

import xlrd

from .version import __version__
from .config import config, log
from .parser import DataParser
from .parsers import *

CSV_DELIMITERS = (',', ';')
OUT_HEADER = ['Type',
              'Buy Quantity', 'Buy Asset', 'Buy Value',
              'Sell Quantity', 'Sell Asset', 'Sell Value',
              'Fee Quantity', 'Fee Asset', 'Fee Value',
              'Wallet', 'Timestamp']

def _open_excel_file(workbook):
    sheet = workbook.sheet_by_index(0)

    reader = _get_cell_values(sheet.get_rows(), workbook)
    _parse_file(reader)
    workbook.release_resources()
    del workbook

def _get_cell_values(rows, workbook):
    for row in rows:
        yield [_convert_cell(cell, workbook) for cell in row]

def _convert_cell(cell, workbook):
    if cell.ctype == xlrd.XL_CELL_DATE:
        value = xlrd.xldate.xldate_as_datetime(cell.value, workbook.datemode). \
                    strftime('%Y-%m-%dT%H:%M:%S %Z')
    else:
        value = str(cell.value)

    return value

def _open_csv_file(filename, delimiter):
    with io.open(filename, newline='', encoding='utf-8-sig') as data_file:
        if sys.version_info[0] < 3:
            # special handling required for utf-8 encoded csv files
            reader = csv.reader(utf_8_encoder(data_file), delimiter=delimiter)
        else:
            reader = csv.reader(data_file, delimiter)
        _parse_file(reader)

    data_file.close()

def utf_8_encoder(unicode_csv_data):
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

    out_rows = []
    if parser.row_handler:
        for in_row in reader:
            t_record = parser.row_handler(in_row, *parser.args)
            out_row = t_record.to_csv() if t_record else []
            if config.args.append:
                out_rows.append(in_row + out_row)
            elif out_row:
                out_rows.append(out_row)
    else:
        # all rows handled together
        all_in_row = list(reader)
        out_rows = parser.all_handler(all_in_row, *parser.args)

    writer = csv.writer(sys.stdout, lineterminator='\n')

    if not config.args.noheader:
        if config.args.append:
            writer.writerow(parser.in_header + OUT_HEADER)
        else:
            writer.writerow(OUT_HEADER)

    if config.args.sort:
        out_rows.sort(key=lambda c: c[-1], reverse=False)

    writer.writerows(out_rows)

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
    parser.add_argument("-a",
                        "--append",
                        action='store_true',
                        help="append output as new columns to the input data file")
    parser.add_argument("-nh",
                        "--noheader",
                        action='store_true',
                        help="exclude header from CSV output")
    parser.add_argument("-s",
                        "--sort",
                        action='store_true',
                        help="sort output by timestamp")
    parser.add_argument("-uc",
                        "--unconfirmed",
                        action='store_true',
                        help="include unconfirmed transactions")
    parser.add_argument("-ca",
                        dest="cryptoasset",
                        type=str,
                        help="specify a cryptoasset symbol, if it cannot be identified "
                             "automatically")

    config.args = parser.parse_args()

    if config.args.debug:
        config.debug_logging_enable()
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
                except KeyError as key_error:
                    # Try with next delimiter
                    continue
                else:
                    break

            if key_error is not None:
                raise
        else:
            _open_excel_file(workbook)

        config.args.noheader = True
