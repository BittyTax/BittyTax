# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import datetime

from colorama import Back

from .parsers import *
from ..config import config
from .exceptions import DataParserError

DEFAULT_TIMESTAMP = datetime.datetime(datetime.MINYEAR, 1, 1, tzinfo=config.TZ_UTC)

class DataRow(object):
    def __init__(self, line_num, in_row):
        self.line_num = line_num
        self.in_row = in_row
        self.timestamp = DEFAULT_TIMESTAMP
        self.t_record = None
        self.parsed = False
        self.failure = None

    def parse(self, parser, filename):
        try:
            parser.row_handler(self, parser, filename)
        except DataParserError as e:
            self.failure = e

    def __eq__(self, other):
        return self.in_row == other.in_row

    def __hash__(self):
        return hash(self.in_row)

    @staticmethod
    def parse_all(data_rows, parser, filename):
        parser.all_handler(data_rows, parser, filename)

    def __str__(self):
        if self.failure is not None:
            return '[' + ', '.join(["%s'%s'%s" % (Back.RED, data, Back.RESET)
                                    if self.failure.col_num == num
                                    else "'%s'" % data
                                    for num, data in enumerate(self.in_row)]) + ']'
        return '[' + "'%s'" % '\', \''.join(self.in_row) + ']'
