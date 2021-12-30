# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal
from datetime import datetime

from colorama import Fore, Style
import dateutil.parser
import dateutil.tz

from ..config import config
from ..price.pricedata import PriceData

TERM_WIDTH = 69

class DataParser(object):
    TYPE_WALLET = 'Wallets'
    TYPE_EXCHANGE = 'Exchanges'
    TYPE_SAVINGS = 'Savings & Loans'
    TYPE_EXPLORER = 'Explorers'
    TYPE_ACCOUNTING = 'Accounting'
    TYPE_SHARES = 'Stocks & Shares'
    TYPE_GENERIC = 'Generic'

    LIST_ORDER = (TYPE_WALLET, TYPE_EXCHANGE, TYPE_SAVINGS, TYPE_EXPLORER, TYPE_ACCOUNTING,
                  TYPE_SHARES)

    price_data = PriceData(config.data_source_fiat)
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
    def parse_timestamp(cls, timestamp_str, tzinfos=None, tz=None, dayfirst=False, fuzzy=False):
        if isinstance(timestamp_str, int):
            timestamp = datetime.utcfromtimestamp(timestamp_str)
        else:
            timestamp = dateutil.parser.parse(timestamp_str,
                                              tzinfos=tzinfos, dayfirst=dayfirst, fuzzy=fuzzy)

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
    def convert_currency(cls, value, from_currency, timestamp):
        if from_currency not in config.fiat_list:
            return None

        if not value or value is None:
            return None

        if not Decimal(value):
            return Decimal(0)

        if config.ccy == from_currency:
            return Decimal(value)

        if timestamp.date() >= datetime.now().date():
            rate_ccy, _, _ = cls.price_data.get_latest(from_currency, config.ccy)
        else:
            rate_ccy, _, _, _ = cls.price_data.get_historical(from_currency, config.ccy, timestamp)

        value_in_ccy = Decimal(value) * rate_ccy

        if config.debug:
            print("%sprice: %s, 1 %s=%s %s, %s %s=%s%s %s%s" % (
                Fore.YELLOW,
                timestamp.strftime('%Y-%m-%d'),
                from_currency,
                config.sym() + '{:0,.2f}'.format(rate_ccy),
                config.ccy,
                '{:0,f}'.format(Decimal(value).normalize()),
                from_currency,
                Style.BRIGHT,
                config.sym() + '{:0,.2f}'.format(value_in_ccy),
                config.ccy,
                Style.NORMAL))

        return value_in_ccy

    @classmethod
    def match_header(cls, row, row_num):
        row = [col.strip() for col in row]
        if config.debug:
            sys.stderr.write("%sheader: row[%s] TRY: %s\n" % (
                Fore.YELLOW, row_num+1, cls.format_row(row)))

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
                if config.debug:
                    sys.stderr.write("%sheader: row[%s] MATCHED: %s as '%s'\n" % (
                        Fore.CYAN, row_num+1, cls.format_row(parser.header), parser.name))
                parser.in_header = row
                parser.in_header_row_num = row_num + 1
                return parser

            if config.debug:
                sys.stderr.write("%sheader: row[%s] NO MATCH: %s '%s'\n" % (
                    Fore.BLUE, row_num+1, cls.format_row(parser.header), parser.name))

        raise KeyError

    @classmethod
    def format_parsers(cls):
        txt = ''
        for p_type in cls.LIST_ORDER:
            txt += ' ' * 2 + p_type.upper() + ':\n'
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
                row_out.append('\'%s\'' %col)

        return '[' + ', '.join(row_out) + ']'
