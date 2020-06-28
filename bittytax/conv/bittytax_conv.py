# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import argparse
import sys

import xlrd

from ..version import __version__
from ..config import config
from .dataparser import DataParser
from .datafile import DataFile
from .output_csv import OutputCsv
from .output_excel import OutputExcel
from .exceptions import UnknownCryptoassetError, UnknownUsernameError, DataFormatUnrecognised

if sys.version_info[0] >= 3:
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(stream=sys.stderr,
                    level=logging.INFO,
                    format='[%(asctime)s.%(msecs)03d] %(levelname)s -- : %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S')
log = logging.getLogger()

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
    parser.add_argument("--duplicates",
                        action='store_true',
                        help="remove any duplicate input rows across data files")
    parser.add_argument("--format",
                        choices=[config.FORMAT_EXCEL, config.FORMAT_CSV, config.FORMAT_RECAP],
                        default=config.FORMAT_EXCEL,
                        type=str.upper,
                        help="specify the output format")
    parser.add_argument("-nh",
                        "--noheader",
                        action='store_true',
                        help="exclude header from CSV output")
    parser.add_argument("-a",
                        "--append",
                        action='store_true',
                        help="append original data as extra columns in the CSV output")
    parser.add_argument("-s",
                        "--sort",
                        action='store_true',
                        help="sort CSV output by timestamp")
    parser.add_argument("-o",
                        dest='output_filename',
                        type=str,
                        help="specify the output filename")

    config.args = parser.parse_args()

    if config.args.debug:
        log.setLevel(logging.DEBUG)
        config.output_config(parser.prog)

    for filename in config.args.filename:
        try:
            try:
                DataFile.read_excel(filename)
            except xlrd.XLRDError:
                DataFile.read_csv(filename)
        except UnknownCryptoassetError:
            parser.error("cryptoasset cannot be identified for data file: {}, "
                         "please specify using the [-ca CRYPTOASSET] option".format(filename))
        except UnknownUsernameError:
            parser.exit("{}: error: username cannot be identified in data file: {}, "
                        "please specify usernames in the {} file"
                        .format(parser.prog, filename, config.BITTYTAX_CONFIG))
        except DataFormatUnrecognised:
            log.warning("Data file format unrecognised: %s", filename)
        except IOError:
            log.warning("File could not be read: %s", filename)

    if DataFile.data_files:
        if config.args.format == config.FORMAT_EXCEL:
            output = OutputExcel(parser.prog, DataFile.data_files_ordered)
            output.write_excel()
        else:
            output = OutputCsv(DataFile.data_files_ordered)
            output.write_csv()
