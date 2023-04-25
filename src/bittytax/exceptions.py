# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from .record import TransactionRecord


class TransactionParserError(Exception):
    def __init__(self, col_num, col_name, value=None):
        super().__init__()
        self.col_num = col_num
        self.col_name = col_name
        self.value = value


class UnexpectedTransactionTypeError(TransactionParserError):
    def __str__(self):
        return (
            f"Invalid Transaction Type: '{self.value}', use "
            f"{{{','.join(TransactionRecord.ALL_TYPES)}}}"
        )


class TimestampParserError(TransactionParserError):
    def __str__(self):
        return f"Invalid Timestamp: '{self.value}', use format YYYY-MM-DDTHH:MM:SS ZZZ"


class DataValueError(TransactionParserError):
    def __str__(self):
        return f"Invalid data for {self.col_name}: '{self.value}'"


class UnexpectedDataError(TransactionParserError):
    def __str__(self):
        return f"Unexpected data in {self.col_name}: '{self.value}'"


class MissingDataError(TransactionParserError):
    def __str__(self):
        return f"Missing data for {self.col_name}"


class ImportFailureError(Exception):
    def __str__(self):
        return "Import failure"
