# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019
# $Id: parser.py,v 1.5 2019/05/16 20:17:42 scottgreen Exp $

import datetime

import dateutil.parser
import dateutil.tz

from .config import config

TERM_WIDTH = 69

class DataParser(object):
    TYPE_WALLET = "Wallets"
    TYPE_EXCHANGE = "Exchanges"
    TYPE_EXPLORER = "Explorers"
    TYPE_SHARES = "Stocks & Shares"

    LIST_ORDER = (TYPE_WALLET, TYPE_EXCHANGE, TYPE_EXPLORER, TYPE_SHARES)

    parsers = []

    def __init__(self, p_type, name, header, row_handler=None, all_handler=None):
        self.p_type = p_type
        self.name = name
        self.header = header
        self.row_handler = row_handler
        self.all_handler = all_handler
        self.args = []

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

        header_str = '"' + ','.join(header) + '"'

        return header_str[:TERM_WIDTH] + '...' if len(header_str) > TERM_WIDTH else header_str

    @classmethod
    def parse_timestamp(cls, timestamp_str, tzinfos=None, tz=None):
        if isinstance(timestamp_str, int):
            timestamp = datetime.datetime.utcfromtimestamp(timestamp_str)
        else:
            timestamp = dateutil.parser.parse(timestamp_str, tzinfos=tzinfos)

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
    def match_header(cls, row):
        for parser in cls.parsers:
            match = False
            for i, col in enumerate(parser.header):
                if i >= len(row):
                    break
                if callable(col):
                    match = col(row[i])
                    parser.args.append(match)
                elif col is not None:
                    match = col == row[i]

                if not match:
                    break

            if match:
                parser.in_header = row
                return parser

        raise KeyError

    @classmethod
    def format_parsers(cls):
        txt = ""
        for p_type in cls.LIST_ORDER:
            txt += ' ' * 2 + p_type + ':\n'
            for parser in sorted([parser for parser in cls.parsers if parser.p_type == p_type]):
                txt += ' ' * 4 + parser.name + '\n'
                txt += ' ' * 6 + parser.format_header() + '\n'

        return txt
