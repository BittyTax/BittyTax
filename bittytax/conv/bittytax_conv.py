# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import argparse
import sys
import codecs
import platform
import glob

import colorama
from colorama import Fore, Back
import xlrd

from ..version import __version__
from ..config import config
from .dataparser import DataParser
from .datafile import DataFile
from .output_csv import OutputCsv
from .output_excel import OutputExcel
from .exceptions import UnknownCryptoassetError, UnknownUsernameError, DataFilenameError, \
                        DataFormatUnrecognised

if sys.stderr.encoding != 'UTF-8':
    if sys.version_info[:2] >= (3, 7):
        sys.stderr.reconfigure(encoding='utf-8')
    elif sys.version_info[:2] >= (3, 1):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    else:
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr)

def main():
    colorama.init()
    parser = argparse.ArgumentParser(epilog="supported data file formats:\n" +
                                     DataParser.format_parsers(),
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('filename',
                        type=str,
                        nargs='+',
                        help="filename of data file")
    parser.add_argument('-v',
                        '--version',
                        action='version',
                        version='%s v%s' % (parser.prog, __version__))
    parser.add_argument('-d',
                        '--debug',
                        action='store_true',
                        help="enable debug logging")
    parser.add_argument('-uc',
                        '--unconfirmed',
                        action='store_true',
                        help="include unconfirmed transactions")
    parser.add_argument('-ca',
                        dest="cryptoasset",
                        type=str,
                        help="specify a cryptoasset symbol, if it cannot be identified "
                             "automatically")
    parser.add_argument('--duplicates',
                        action='store_true',
                        help="remove any duplicate input rows across data files")
    parser.add_argument('--format',
                        choices=[config.FORMAT_EXCEL, config.FORMAT_CSV, config.FORMAT_RECAP],
                        default=config.FORMAT_EXCEL,
                        type=str.upper,
                        help="specify the output format, default: EXCEL")
    parser.add_argument('-nh',
                        '--noheader',
                        action='store_true',
                        help="exclude header from CSV output")
    parser.add_argument('-a',
                        '--append',
                        action='store_true',
                        help="append original data as extra columns in the CSV output")
    parser.add_argument('-s',
                        '--sort',
                        action='store_true',
                        help="sort CSV output by timestamp")
    parser.add_argument('-o',
                        dest='output_filename',
                        type=str,
                        help="specify the output filename")

    args = parser.parse_args()
    config.debug = args.debug
    DataFile.remove_duplicates = args.duplicates

    if config.debug:
        sys.stderr.write("%s%s v%s\n" % (Fore.YELLOW, parser.prog, __version__))
        sys.stderr.write("%spython: v%s\n" % (Fore.GREEN, platform.python_version()))
        sys.stderr.write("%ssystem: %s, release: %s\n" % (
            Fore.GREEN, platform.system(), platform.release()))

    for filename in args.filename:
        for pathname in glob.iglob(filename):
            try:
                do_read_file(pathname, args)
            except UnknownCryptoassetError as e:
                sys.stderr.write(Fore.RESET)
                parser.error("%s, please specify using the [-ca CRYPTOASSET] option" % e)
            except UnknownUsernameError as e:
                sys.stderr.write(Fore.RESET)
                parser.exit("%s: error: %s, please specify usernames in the %s file" % (
                                parser.prog, e, config.BITTYTAX_CONFIG))
            except DataFilenameError as e:
                sys.stderr.write(Fore.RESET)
                parser.exit("%s: error: %s" % (parser.prog, e))
            except DataFormatUnrecognised as e:
                sys.stderr.write("%sWARNING%s %s\n" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, e))
            except IOError:
                sys.stderr.write("%sWARNING%s File could not be read: %s\n" % (
                Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, pathname))

    if DataFile.data_files:
        if args.format == config.FORMAT_EXCEL:
            output = OutputExcel(parser.prog, DataFile.data_files_ordered, args)
            output.write_excel()
        else:
            output = OutputCsv(DataFile.data_files_ordered, args)
            sys.stderr.write(Fore.RESET)
            sys.stderr.flush()
            output.write_csv()

def do_read_file(pathname, args):
    try:
        for (worksheet, datemode) in DataFile.read_excel(pathname):
            try:
                DataFile.read_worksheet(worksheet, datemode, pathname, args)
            except DataFormatUnrecognised as e:
                sys.stderr.write("%sWARNING%s %s\n" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, e))
    except xlrd.XLRDError:
        DataFile.read_csv(pathname, args)
