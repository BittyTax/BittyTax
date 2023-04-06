# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import argparse
import codecs
import errno
import glob
import hashlib
import platform
import sys

import colorama
from colorama import Fore

from ..config import config
from ..version import __version__
from .datafile import DataFile
from .datamerge import DataMerge
from .dataparser import DataParser
from .exceptions import (
    DataFilenameError,
    DataFormatUnrecognised,
    UnknownCryptoassetError,
    UnknownUsernameError,
)
from .output_csv import OutputCsv
from .output_excel import OutputExcel

if sys.stderr.encoding != "UTF-8":
    if sys.version_info[:2] >= (3, 7):
        sys.stderr.reconfigure(encoding="utf-8")
    elif sys.version_info[:2] >= (3, 1):
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    else:
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr)


def main():
    colorama.init()
    parser = argparse.ArgumentParser(
        epilog="supported data file formats:\n" + DataParser.format_parsers(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("filename", type=str, nargs="+", help="filename of data file")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%s v%s" % (parser.prog, __version__),
    )
    parser.add_argument("-d", "--debug", action="store_true", help="enable debug logging")
    parser.add_argument(
        "-uc",
        "--unconfirmed",
        action="store_true",
        help="include unconfirmed transactions",
    )
    parser.add_argument(
        "-ca",
        dest="cryptoasset",
        type=str,
        help="specify a cryptoasset symbol, if it cannot be identified automatically",
    )
    parser.add_argument(
        "--duplicates",
        action="store_true",
        help="remove any duplicate input rows across data files",
    )
    parser.add_argument(
        "--format",
        choices=[str(config.FORMAT_EXCEL), str(config.FORMAT_CSV), str(config.FORMAT_RECAP)],
        default=str(config.FORMAT_EXCEL),
        type=str.upper,
        help="specify the output format, default: EXCEL",
    )
    parser.add_argument(
        "-nh", "--noheader", action="store_true", help="exclude header from CSV output"
    )
    parser.add_argument(
        "-a",
        "--append",
        action="store_true",
        help="append original data as extra columns in the CSV output",
    )
    parser.add_argument("-s", "--sort", action="store_true", help="sort CSV output by timestamp")
    parser.add_argument("-o", dest="output_filename", type=str, help="specify the output filename")

    args = parser.parse_args()
    config.debug = args.debug
    config.output = sys.stderr
    DataFile.remove_duplicates = args.duplicates

    if config.debug:
        sys.stderr.write("%s%s v%s\n" % (Fore.YELLOW, parser.prog, __version__))
        sys.stderr.write("%spython: v%s\n" % (Fore.GREEN, platform.python_version()))
        sys.stderr.write(
            "%ssystem: %s, release: %s\n" % (Fore.GREEN, platform.system(), platform.release())
        )
        config.output_config()

    file_hashes = set()
    for filename in args.filename:
        pathnames = glob.glob(filename)
        if not pathnames:
            pathnames = [filename]

        for pathname in pathnames:
            try:
                file_type, file_hash = _get_file_info(pathname)
                if file_hash in file_hashes:
                    sys.stderr.write(_file_msg(pathname, None, msg="skipping duplicate"))
                else:
                    file_hashes.add(file_hash)
                    _do_read_file(file_type, pathname, args)

            except UnknownCryptoassetError as e:
                sys.stderr.write(Fore.RESET)
                parser.error("%s, please specify using the [-ca CRYPTOASSET] option" % e)
            except UnknownUsernameError as e:
                sys.stderr.write(Fore.RESET)
                parser.exit(
                    "%s: error: %s, please specify usernames in the %s file"
                    % (parser.prog, e, config.BITTYTAX_CONFIG),
                )
            except DataFilenameError as e:
                sys.stderr.write(Fore.RESET)
                parser.exit("%s: error: %s" % (parser.prog, e))
            except DataFormatUnrecognised as e:
                sys.stderr.write(_file_msg(pathname, None, msg="unrecognised"))
            except IOError as e:
                if e.errno == errno.ENOENT:
                    sys.stderr.write(_file_msg(pathname, None, msg="no such file or directory"))
                elif e.errno == errno.EISDIR:
                    sys.stderr.write(_file_msg(pathname, None, msg="is a directory"))
                else:
                    sys.stderr.write(_file_msg(pathname, None, msg="read error"))

    if DataFile.data_files:
        DataMerge.match_merge(DataFile.data_files)

        if args.format == config.FORMAT_EXCEL:
            output = OutputExcel(parser.prog, DataFile.data_files_ordered, args)
            output.write_excel()
        else:
            output = OutputCsv(DataFile.data_files_ordered, args)
            sys.stderr.write(Fore.RESET)
            sys.stderr.flush()
            output.write_csv()
    else:
        sys.stderr.write(Fore.RESET)
        parser.exit(3, "%s: error: no data files could be processed\n" % parser.prog)


def _do_read_file(file_type, pathname, args):
    if file_type == "zip":
        for worksheet in DataFile.read_excel_xlsx(pathname):
            try:
                DataFile.read_worksheet_xlsx(worksheet, pathname, args)
            except DataFormatUnrecognised:
                sys.stderr.write(_file_msg(pathname, worksheet.title, msg="unrecognised"))
    elif file_type == "xls":
        for worksheet, datemode in DataFile.read_excel_xls(pathname):
            try:
                DataFile.read_worksheet_xls(worksheet, datemode, pathname, args)
            except (DataFormatUnrecognised, ValueError):
                sys.stderr.write(_file_msg(pathname, worksheet.name, msg="unrecognised"))
    else:
        DataFile.read_csv(pathname, args)


def _get_file_info(filename):
    file_type = None

    with open(filename, "rb") as df:
        file_hash = hashlib.sha1()
        chunk = df.read(8192)
        if chunk[0:8] == b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1":
            file_type = "xls"
        elif chunk[0:4] == b"\x50\x4B\x03\x04":
            # xlsx is a zip file, let openpyxl unpack and check
            file_type = "zip"

        while chunk:
            file_hash.update(chunk)
            chunk = df.read(8192)

    return file_type, file_hash.hexdigest()


def _file_msg(filename, worksheet_name, msg):
    if worksheet_name:
        worksheet_str = " '%s'" % worksheet_name
    else:
        worksheet_str = ""

    return "%sfile: %s%s%s %s%s\n" % (
        Fore.WHITE,
        Fore.YELLOW,
        filename,
        worksheet_str,
        Fore.WHITE,
        msg,
    )


if __name__ == "__main__":
    main()
