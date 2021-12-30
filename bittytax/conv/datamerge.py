# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import sys

from colorama import Fore

class DataMerge(object):
    OPT = 'Optional'
    MAN = 'Mandatory'

    SEPARATOR_AND = '"' + Fore.WHITE + ' & ' + Fore.CYAN + '"'

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

            man_tot = len([p for p in data_merge.parsers
                           if data_merge.parsers[p]['req'] == cls.MAN])
            man_cnt = 0
            opt_cnt = 0

            for parser in data_merge.parsers:
                data_file = cls._match_datafile(data_files, data_merge.parsers[parser])

                if data_file:
                    matched_data_files[parser] = data_file
                    if data_merge.parsers[parser]['req'] == cls.MAN:
                        man_cnt += 1
                    elif data_merge.parsers[parser]['req'] == cls.OPT:
                        opt_cnt += 1

            if man_cnt == 1 and opt_cnt > 0 or man_cnt > 1 and man_cnt == man_tot:
                sys.stderr.write("%smerge: \"%s\"\n" % (Fore.WHITE, data_merge.name))

                merge = data_merge.merge_handler(matched_data_files)
                if merge:
                    parsers = [matched_data_files[data_file].parser.name
                               for data_file in matched_data_files]
                    sys.stderr.write("%smerge: successfully merged %s\"%s\"\n" % (
                        Fore.WHITE, Fore.CYAN, cls.SEPARATOR_AND.join(parsers)))

                    for match in matched_data_files:
                        del data_files[matched_data_files[match]]
                else:
                    sys.stderr.write("%smerge: nothing to merge\n" % Fore.YELLOW)

    @classmethod
    def _match_datafile(cls, data_files, parser):
        for data_file in data_files:
            if (data_file.parser.row_handler, data_file.parser.all_handler) == \
                   (parser['obj'].row_handler, parser['obj'].all_handler):
                return data_file
        return None

class MergeDataRow(object):
    def __init__(self, data_row, data_file, data_file_id):
        self.data_row = data_row
        self.data_file = data_file
        self.data_file_id = data_file_id
