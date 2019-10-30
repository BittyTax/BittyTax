# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import datetime

import dateutil.parser
import dateutil.tz

from ..config import config

TERM_WIDTH = 69

log = logging.getLogger()

class DataParser(object):
    TYPE_WALLET = "Wallets"
    TYPE_EXCHANGE = "Exchanges"
    TYPE_EXPLORER = "Explorers"
    TYPE_SHARES = "Stocks & Shares"

    LIST_ORDER = (TYPE_WALLET, TYPE_EXCHANGE, TYPE_EXPLORER, TYPE_SHARES)

    parsers = []

    def __init__(self, p_type, name, header, delimiter=',',
                 worksheet_name=None, row_handler=None, all_handler=None):
        self.p_type = p_type
        self.name = name
        self.header = header
        self.worksheet_name = worksheet_name if worksheet_name else name
        self.delimiter = delimiter
        self.row_handler = row_handler
        self.all_handler = all_handler
        self.args = []
        self.in_header = None
        self.in_header_row_num = None

        self.parsers.append(self)

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return self.name < other.name

    def format_header(self):
        header = []
        for col in self.header:
            if callable(col) or col is None:
                header.append('_')
            else:
                header.append(col)

        header_str = '\'' + str(self.delimiter).join(header) + '\''

        return header_str[:TERM_WIDTH] + '...' if len(header_str) > TERM_WIDTH else header_str

    @classmethod
    def parse_timestamp(cls, timestamp_str, tzinfos=None, tz=None, dayfirst=False):
        if isinstance(timestamp_str, int):
            timestamp = datetime.datetime.utcfromtimestamp(timestamp_str)
        else:
            timestamp = dateutil.parser.parse(timestamp_str, tzinfos=tzinfos, dayfirst=dayfirst)

        if tz:
            timestamp = timestamp.replace(tzinfo=dateutil.tz.gettz(tz))
            timestamp = timestamp.astimezone(config.TZ_UTC)
        elif timestamp.tzinfo is None:
            #default to UTC if no timezone is specified
            timestamp = timestamp.replace(tzinfo=config.TZ_UTC)
        else:
            timestamp = timestamp.astimezone(config.TZ_UTC)

        return timestamp

    @classmethod
    def match_header(cls, row, row_num):
        log.debug("Row[%s] TRY: %s", row_num+1, cls.format_row(row))
        parsers_reduced = [p for p in cls.parsers if len(p.header) == len(row)]
        for parser in parsers_reduced:
            match = False
            for i, row_field in enumerate(row):
                if callable(parser.header[i]):
                    match = parser.header[i](row_field)
                    parser.args.append(match)
                elif parser.header[i] is not None:
                    match = row_field == parser.header[i]

                if not match:
                    break

            if match:
                log.debug("Row[%s] MATCHED: %s '%s'",
                          row_num+1, cls.format_row(parser.header), parser.name)
                parser.in_header = row
                parser.in_header_row_num = row_num + 1
                return parser
            else:
                log.debug("Row[%s] NO MATCH: %s '%s'",
                          row_num+1, cls.format_row(parser.header), parser.name)

        raise KeyError

    @classmethod
    def format_parsers(cls):
        txt = ""
        for p_type in cls.LIST_ORDER:
            txt += ' ' * 2 + p_type + ':\n'
            prev_name = None
            for parser in sorted([parser for parser in cls.parsers if parser.p_type == p_type]):
                if parser.name != prev_name:
                    txt += ' ' * 4 + parser.name + '\n'
                txt += ' ' * 6 + parser.format_header() + '\n'

                prev_name = parser.name

        return txt

    @staticmethod
    def format_row(row):
        row_out = []
        for col in row:
            if callable(col):
                row_out.append('<lambda>')
            elif col is None:
                row_out.append('*')
            else:
                row_out.append('\'{}\''.format(col))

        return '[' + ', '.join(row_out) + ']'
