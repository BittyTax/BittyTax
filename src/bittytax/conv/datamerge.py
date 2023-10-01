# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import sys
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

from colorama import Fore
from typing_extensions import Protocol, TypedDict

from ..config import config
from ..constants import ERROR
from ..types import FileId
from .dataparser import DataParser

if TYPE_CHECKING:
    from .datafile import DataFile
    from .datarow import DataRow


class ParserRequired(Enum):
    OPTIONAL = "Optional"
    MANDATORY = "Mandatory"


class Parser(TypedDict):
    req: ParserRequired
    obj: DataParser


class MergeHandler(Protocol):  # pylint: disable=too-few-public-methods
    def __call__(self, data_files: Dict[FileId, "DataFile"]) -> bool:
        ...


class DataMerge:  # pylint: disable=too-few-public-methods
    SEPARATOR_AND = f'"{Fore.WHITE} & {Fore.CYAN}"'

    mergers: List["DataMerge"] = []

    def __init__(
        self, name: str, parsers: Dict[FileId, Parser], merge_handler: MergeHandler
    ) -> None:
        self.name = name
        self.parsers = parsers
        self.merge_handler = merge_handler

        self.mergers.append(self)

    @classmethod
    def match_merge(cls, data_files: Dict["DataFile", "DataFile"]) -> None:
        for data_merge in cls.mergers:
            matched_data_files: Dict[FileId, "DataFile"] = {}

            man_tot = len(
                [
                    p
                    for p in data_merge.parsers
                    if data_merge.parsers[p]["req"] == ParserRequired.MANDATORY
                ]
            )
            man_cnt = 0
            opt_cnt = 0

            for parser in data_merge.parsers:
                data_file = cls._match_datafile(data_files, data_merge.parsers[parser])

                if data_file:
                    matched_data_files[parser] = data_file
                    if data_merge.parsers[parser]["req"] == ParserRequired.MANDATORY:
                        man_cnt += 1
                    elif data_merge.parsers[parser]["req"] == ParserRequired.OPTIONAL:
                        opt_cnt += 1

            if man_cnt == 1 and opt_cnt > 0 or man_cnt > 1 and man_cnt == man_tot:
                sys.stderr.write(f'{Fore.WHITE}merge: "{data_merge.name}"\n')

                try:
                    merge = data_merge.merge_handler(matched_data_files)
                except (ValueError, ArithmeticError) as e:
                    if config.debug:
                        raise

                    sys.stderr.write(f'{ERROR} Unexpected error: "{e}"\n')
                else:
                    if merge:
                        parsers = [df.parser.name for _, df in matched_data_files.items()]
                        sys.stderr.write(
                            f"{Fore.WHITE}merge: successfully merged "
                            f'{Fore.CYAN}"{cls.SEPARATOR_AND.join(parsers)}"\n'
                        )

                        for _, df in matched_data_files.items():
                            del data_files[df]
                    else:
                        sys.stderr.write(f"{Fore.YELLOW}merge: nothing to merge\n")

    @classmethod
    def _match_datafile(
        cls, data_files: Dict["DataFile", "DataFile"], parser: Parser
    ) -> Optional["DataFile"]:
        for data_file in data_files:
            if (data_file.parser.row_handler, data_file.parser.all_handler) == (
                parser["obj"].row_handler,
                parser["obj"].all_handler,
            ):
                return data_file
        return None


class MergeDataRow:  # pylint: disable=too-few-public-methods
    def __init__(self, data_row: "DataRow", data_file: "DataFile", data_file_id: str):
        self.data_row = data_row
        self.data_file = data_file
        self.data_file_id = data_file_id
        self.quantity = Decimal(0)
