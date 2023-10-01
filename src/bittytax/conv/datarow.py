# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import datetime
from typing import List, Optional

from colorama import Back, Fore
from typing_extensions import Unpack

from ..config import config
from ..constants import TZ_UTC
from .dataparser import DataParser, ParserArgs
from .exceptions import DataRowError
from .mergers import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .out_record import TransactionOutRecord
from .parsers import *  # type: ignore[no-redef] # pylint: disable=wildcard-import, unused-wildcard-import # noqa: E501

DEFAULT_TIMESTAMP = datetime.datetime(datetime.MINYEAR, 1, 1, tzinfo=TZ_UTC)


class DataRow:
    def __init__(self, line_num: int, row: List[str], in_header: List[str]) -> None:
        self.line_num = line_num
        self.row = row
        self.row_dict = dict(zip(in_header, row))
        self.timestamp = DEFAULT_TIMESTAMP
        self.t_record: Optional[TransactionOutRecord] = None
        self.parsed = False
        self.failure: Optional[Exception] = None

    def parse(self, parser: DataParser, **kwargs: Unpack["ParserArgs"]) -> None:
        if not parser.row_handler:
            raise RuntimeError("Missing row_handler")

        try:
            parser.row_handler(self, parser, **kwargs)
        except DataRowError as e:
            self.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            self.failure = e

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DataRow):
            return NotImplemented
        return self.row == other.row

    def __hash__(self) -> int:
        return hash(self.row)

    @staticmethod
    def parse_all(
        data_rows: List["DataRow"], parser: DataParser, **kwargs: Unpack["ParserArgs"]
    ) -> None:
        if not parser.all_handler:
            raise RuntimeError("Missing all_handler")

        parser.all_handler(data_rows, parser, **kwargs)

    def __str__(self) -> str:
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
