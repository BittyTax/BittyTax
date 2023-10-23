# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from typing import Any

from .bt_types import TrType


class TransactionParserError(Exception):
    def __init__(self, col_num: int, col_name: str, value: Any = ""):
        super().__init__()
        self.col_num = col_num
        self.col_name = col_name
        self.value = value


class UnexpectedTransactionTypeError(TransactionParserError):
    def __str__(self) -> str:
        return (
            f"Invalid Transaction Type: '{self.value}', use "
            f"{{{','.join(t_type.value for t_type in TrType)}}}"
        )


class TimestampParserError(TransactionParserError):
    def __str__(self) -> str:
        return f"Invalid Timestamp: '{self.value}', use format YYYY-MM-DDTHH:MM:SS ZZZ"


class DataValueError(TransactionParserError):
    def __str__(self) -> str:
        return f"Invalid data for {self.col_name}: '{repr(self.value)}'"


class UnexpectedDataError(TransactionParserError):
    def __str__(self) -> str:
        return f"Unexpected data in {self.col_name}: '{self.value}'"


class MissingDataError(TransactionParserError):
    def __str__(self) -> str:
        return f"Missing data for {self.col_name}"


class ImportFailureError(Exception):
    def __str__(self) -> str:
        return "Import failure"
