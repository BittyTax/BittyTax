# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from .record import TransactionRecord


class TransactionParserError(Exception):
    def __init__(self, col_num, col_name, value=None):
        super(TransactionParserError, self).__init__()
        self.col_num = col_num
        self.col_name = col_name
        self.value = value


class UnexpectedTransactionTypeError(TransactionParserError):
    def __str__(self):
        return "Invalid Transaction Type: '%s', use {%s}" % (
            self.value,
            ",".join(TransactionRecord.ALL_TYPES),
        )


class TimestampParserError(TransactionParserError):
    def __str__(self):
        return "Invalid Timestamp: '%s', use format YYYY-MM-DDTHH:MM:SS ZZZ" % self.value


class DataValueError(TransactionParserError):
    def __str__(self):
        return "Invalid data for %s: '%s'" % (self.col_name, self.value)


class UnexpectedDataError(TransactionParserError):
    def __str__(self):
        return "Unexpected data in %s: '%s'" % (self.col_name, self.value)


class MissingDataError(TransactionParserError):
    def __str__(self):
        return "Missing data for %s" % self.col_name


class ImportFailureError(Exception):
    def __str__(self):
        return "Import failure"
