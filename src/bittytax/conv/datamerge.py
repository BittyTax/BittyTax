# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import sys
from decimal import Decimal

from colorama import Fore

from ..config import config
from ..constants import ERROR


class DataMerge:  # pylint: disable=too-few-public-methods
    OPT = "Optional"
    MAN = "Mandatory"

    SEPARATOR_AND = f'"{Fore.WHITE} & {Fore.CYAN}"'

    mergers = []

    def __init__(self, name, parsers, merge_handler):
        self.name = name
        self.parsers = parsers
        self.merge_handler = merge_handler

        self.mergers.append(self)

    @classmethod
    def match_merge(cls, data_files):
        for data_merge in cls.mergers:
            matched_data_files = {}

            man_tot = len(
                [p for p in data_merge.parsers if data_merge.parsers[p]["req"] == cls.MAN]
            )
            man_cnt = 0
            opt_cnt = 0

            for parser in data_merge.parsers:
                data_file = cls._match_datafile(data_files, data_merge.parsers[parser])

                if data_file:
                    matched_data_files[parser] = data_file
                    if data_merge.parsers[parser]["req"] == cls.MAN:
                        man_cnt += 1
                    elif data_merge.parsers[parser]["req"] == cls.OPT:
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
    def _match_datafile(cls, data_files, parser):
        for data_file in data_files:
            if (data_file.parser.row_handler, data_file.parser.all_handler) == (
                parser["obj"].row_handler,
                parser["obj"].all_handler,
            ):
                return data_file
        return None


class MergeDataRow:  # pylint: disable=too-few-public-methods
    def __init__(self, data_row, data_file, data_file_id):
        self.data_row = data_row
        self.data_file = data_file
        self.data_file_id = data_file_id
        self.quantity = Decimal(0)
