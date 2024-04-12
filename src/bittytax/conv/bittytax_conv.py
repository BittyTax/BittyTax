# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import argparse
import errno
import glob
import hashlib
import os
import platform
import sys
from typing import Optional, Tuple

import colorama
from colorama import Fore

from ..config import config
from ..constants import FORMAT_CSV, FORMAT_EXCEL, FORMAT_RECAP
from ..version import __version__
from .datafile import DataFile
from .datamerge import DataMerge
from .dataparser import DataParser
from .exceptions import (
    DataFilenameError,
    DataFormatNotSupported,
    DataFormatUnrecognised,
    UnknownCryptoassetError,
    UnknownUsernameError,
)
from .output_csv import OutputCsv
from .output_excel import OutputExcel

if sys.stderr.encoding != "UTF-8":
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]


def main() -> None:
    colorama.init()
    parser = argparse.ArgumentParser(
        epilog=f"supported data file formats:\n{DataParser.format_parsers()}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("filename", type=str, nargs="+", help="filename of data file")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{parser.prog} v{__version__}",
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
        "--binance_statements_only",
        action="store_true",
        help="use only Binance Statements, for ALL transaction types, "
        "that includes deposits/withdrawals and trades, "
        "note this may not be as accurate as using individual files for these",
    )
    parser.add_argument(
        "--binance_multi_bnb_split_even",
        action="store_true",
        help="for BNB converts in Binance Statements, "
        "split the total BNB amount evenly across all the tokens converted in the same period",
    )
    parser.add_argument(
        "--duplicates",
        action="store_true",
        help="remove any duplicate input rows across data files",
    )
    parser.add_argument(
        "--format",
        choices=[FORMAT_EXCEL, FORMAT_CSV, FORMAT_RECAP],
        default=FORMAT_EXCEL,
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
    DataFile.remove_duplicates = args.duplicates

    if args.binance_statements_only:
        config.config["binance_statements_only"] = True

    if args.binance_multi_bnb_split_even:
        config.config["binance_multi_bnb_split_even"] = True

    if config.debug:
        sys.stderr.write(f"{Fore.YELLOW}{parser.prog} v{__version__}\n")
        sys.stderr.write(f"{Fore.GREEN}python: v{platform.python_version()}\n")
        sys.stderr.write(
            f"{Fore.GREEN}system: {platform.system()}, release: {platform.release()}\n"
        )
        config.output_config(sys.stderr)

    file_hashes = set()
    for filename in args.filename:
        pathnames = glob.glob(filename, recursive=True)
        if not pathnames:
            pathnames = [filename]

        for pathname in pathnames:
            if os.path.isdir(pathname):
                sys.stderr.write(_file_msg(pathname, None, msg="is a directory"))
                continue

            try:
                file_type, file_hash = _get_file_info(pathname)
                if file_hash in file_hashes:
                    sys.stderr.write(_file_msg(pathname, None, msg="skipping duplicate"))
                else:
                    file_hashes.add(file_hash)
                    _do_read_file(file_type, pathname, args)

            except UnknownCryptoassetError as e:
                sys.stderr.write(Fore.RESET)
                parser.error(f"{e}, please specify using the [-ca CRYPTOASSET] option")
            except UnknownUsernameError as e:
                sys.stderr.write(Fore.RESET)
                parser.exit(
                    message=f"{parser.prog}: error: {e}, please specify usernames in the "
                    f"{config.BITTYTAX_CONFIG} file\n"
                )
            except DataFilenameError as e:
                sys.stderr.write(Fore.RESET)
                parser.exit(message=f"{parser.prog}: error: {e}\n")
            except DataFormatUnrecognised:
                sys.stderr.write(_file_msg(pathname, None, msg="unrecognised"))
            except DataFormatNotSupported:
                sys.stderr.write(_file_msg(pathname, None, msg="format not supported"))
            except IOError as e:
                if e.errno == errno.ENOENT:
                    sys.stderr.write(_file_msg(pathname, None, msg="no such file or directory"))
                else:
                    sys.stderr.write(_file_msg(pathname, None, msg="read error"))

    if DataFile.data_files:
        DataMerge.match_merge(DataFile.data_files)

        if args.format == FORMAT_EXCEL:
            output_excel = OutputExcel(parser.prog, DataFile.data_files_ordered, args)
            output_excel.write_excel()
        else:
            output_csv = OutputCsv(DataFile.data_files_ordered, args)
            sys.stderr.write(Fore.RESET)
            sys.stderr.flush()
            output_csv.write_csv()
    else:
        sys.stderr.write(Fore.RESET)
        parser.exit(3, f"{parser.prog}: error: no data file(s) could be processed\n")


def _do_read_file(file_type: str, pathname: str, args: argparse.Namespace) -> None:
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


def _get_file_info(filename: str) -> Tuple[str, str]:
    file_type = ""

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


def _file_msg(filename: str, worksheet_name: Optional[str], msg: str) -> str:
    if worksheet_name:
        worksheet_str = f" '{worksheet_name}'"
    else:
        worksheet_str = ""

    return f"{Fore.WHITE}file: {Fore.YELLOW}{filename}{worksheet_str} {Fore.WHITE}{msg}\n"


if __name__ == "__main__":
    main()
