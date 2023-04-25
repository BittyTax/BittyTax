# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import datetime

from colorama import Back, Fore

from ..config import config
from ..constants import TZ_UTC
from .exceptions import DataRowError
from .mergers import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .parsers import *  # pylint: disable=wildcard-import, unused-wildcard-import

DEFAULT_TIMESTAMP = datetime.datetime(datetime.MINYEAR, 1, 1, tzinfo=TZ_UTC)


class DataRow:
    def __init__(self, line_num, row, in_header):
        self.line_num = line_num
        self.row = row
        self.row_dict = dict(zip(in_header, row))
        self.timestamp = DEFAULT_TIMESTAMP
        self.t_record = None
        self.parsed = False
        self.failure = None

    def parse(self, parser, **kwargs):
        try:
            parser.row_handler(self, parser, **kwargs)
        except DataRowError as e:
            self.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            self.failure = e

    def __eq__(self, other):
        return self.row == other.row

    def __hash__(self):
        return hash(self.row)

    @staticmethod
    def parse_all(data_rows, parser, **kwargs):
        parser.all_handler(data_rows, parser, **kwargs)

    def __str__(self):
        if self.failure and isinstance(self.failure, DataRowError):
            row_str = ", ".join(
                [
                    f"{Back.RED}'{data}'{Back.RESET}"
                    if self.failure.col_num == num
                    else f"'{data}'"
                    for num, data in enumerate(self.row)
                ]
            )
            return f"[{row_str}]"

        row_str = "', '".join(self.row)
        if self.failure:
            return f"{Fore.RED}['{row_str}']"
        return f"['{row_str}']"
