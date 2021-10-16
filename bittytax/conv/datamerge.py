# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import sys

from colorama import Fore

class DataMerge(object):
    SEPARATOR = '"' + Fore.WHITE + ' & ' + Fore.CYAN + '"'

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
            missing_data_files = []

            for parser in data_merge.parsers:
                data_file = cls._match_datafile(data_files, data_merge.parsers[parser])

                if data_file:
                    matched_data_files[parser] = data_file
                else:
                    missing_data_files.append(data_merge.parsers[parser].name)

            if matched_data_files:
                sys.stderr.write("%smerge: \"%s\"\n" % (
                    Fore.WHITE, data_merge.name))

            if len(matched_data_files) == len(data_merge.parsers):
                merge = data_merge.merge_handler(matched_data_files)
                if merge:
                    parsers = [matched_data_files[data_file].parser.name
                               for data_file in matched_data_files]
                    sys.stderr.write("%smerge: successfully merged %s\"%s\"\n" % (
                        Fore.WHITE, Fore.CYAN, cls.SEPARATOR.join(parsers)))

                    for match in matched_data_files:
                        del data_files[matched_data_files[match]]
                else:
                    sys.stderr.write("%smerge: nothing to merge\n" % Fore.YELLOW)

            elif len(matched_data_files) != 0:
                sys.stderr.write("%smerge: requires file(s) %s\"%s\"\n" % (
                    Fore.YELLOW, Fore.CYAN, cls.SEPARATOR.join(missing_data_files)))

    @classmethod
    def _match_datafile(cls, data_files, parser):
        for data_file in data_files:
            if (data_file.parser.row_handler, data_file.parser.all_handler) == \
                   (parser.row_handler, parser.all_handler):
                return data_file
        return None
