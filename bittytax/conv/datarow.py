# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import datetime

from colorama import Back

from .parsers import *
from ..config import config
from .exceptions import DataParserError

DEFAULT_TIMESTAMP = datetime.datetime(datetime.MINYEAR, 1, 1, tzinfo=config.TZ_UTC)

class DataRow(object):
    def __init__(self, line_num, row, in_header):
        self.line_num = line_num
        self.row = row
        self.row_dict = dict(zip(in_header, row))
        self.timestamp = DEFAULT_TIMESTAMP
        self.t_record = None
        self.parsed = False
        self.failure = None

    def parse(self, parser, filename, args):
        try:
            parser.row_handler(self, parser, filename, args)
        except DataParserError as e:
            self.failure = e

    def __eq__(self, other):
        return self.row == other.row

    def __hash__(self):
        return hash(self.row)

    @staticmethod
    def parse_all(data_rows, parser, filename, args):
        parser.all_handler(data_rows, parser, filename, args)

    def __str__(self):
        if self.failure is not None:
            return '[' + ', '.join(["%s'%s'%s" % (Back.RED, data, Back.RESET)
                                    if self.failure.col_num == num
                                    else "'%s'" % data
                                    for num, data in enumerate(self.row)]) + ']'
        return '[' + "'%s'" % '\', \''.join(self.row) + ']'
