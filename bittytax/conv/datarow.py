# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import datetime
import logging

from .parsers import *
from ..config import config
from .exceptions import UnknownCryptoassetError, DataParserError

DEFAULT_TIMESTAMP = datetime.datetime(datetime.MINYEAR, 1, 1, tzinfo=config.TZ_UTC)

log = logging.getLogger()

class DataRow(object):
    def __init__(self, line_num, in_row):
        self.line_num = line_num
        self.in_row = in_row
        self.timestamp = DEFAULT_TIMESTAMP
        self.t_record = None
        self.parsed = False
        self.failure = None

    def parse(self, parser):
        try:
            parser.row_handler(self, parser)
        except UnknownCryptoassetError:
            raise
        except DataParserError as e:
            self.failure = e

    def __eq__(self, other):
        return self.in_row == other.in_row

    def __hash__(self):
        return hash(self.in_row)

    @staticmethod
    def parse_all(data_rows, parser):
        parser.all_handler(data_rows, parser)
