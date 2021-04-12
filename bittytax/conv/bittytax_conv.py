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
                        help="specify the output format")
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

    config.args = parser.parse_args()

    if config.args.debug:
        sys.stderr.write("%s%s v%s\n" % (Fore.YELLOW, parser.prog, __version__))
        sys.stderr.write("%spython: v%s\n" % (Fore.GREEN, platform.python_version()))
        sys.stderr.write("%ssystem: %s, release: %s\n" % (
            Fore.GREEN, platform.system(), platform.release()))

    for filename in config.args.filename:
        for pathname in glob.iglob(filename):
            try:
                try:
                    DataFile.read_excel(pathname)
                except xlrd.XLRDError:
                    DataFile.read_csv(pathname)
            except UnknownCryptoassetError:
                sys.stderr.write(Fore.RESET)
                parser.error("cryptoasset cannot be identified for data file: %s, "
                             "please specify using the [-ca CRYPTOASSET] option" % pathname)
            except UnknownUsernameError:
                sys.stderr.write(Fore.RESET)
                parser.exit("%s: error: username cannot be identified in data file: %s, "
                            "please specify usernames in the %s file" % (
                                parser.prog, pathname, config.BITTYTAX_CONFIG))
            except DataFilenameError as e:
                sys.stderr.write(Fore.RESET)
                parser.exit("%s: error: %s" % (parser.prog, e))
            except DataFormatUnrecognised:
                sys.stderr.write("%sWARNING%s File format is unrecognised: %s\n" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, pathname))
            except IOError:
                sys.stderr.write("%sWARNING%s File could not be read: %s\n" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, pathname))

    if DataFile.data_files:
        if config.args.format == config.FORMAT_EXCEL:
            output = OutputExcel(parser.prog, DataFile.data_files_ordered)
            output.write_excel()
        else:
            output = OutputCsv(DataFile.data_files_ordered)
            sys.stderr.write(Fore.RESET)
            sys.stderr.flush()
            output.write_csv()
