# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from datetime import datetime


class DataRowError(Exception):
    def __init__(self, col_num: int, col_name: str, value: str = "") -> None:
        super().__init__()
        self.col_num = col_num
        self.col_name = col_name
        self.value = value


class UnexpectedTypeError(DataRowError):
    def __str__(self) -> str:
        return f"Unrecognised {self.col_name}: '{self.value}'"


class UnexpectedContentError(DataRowError):
    def __str__(self) -> str:
        return f"Unexpected {self.col_name} content: '{self.value}'"


class MissingValueError(DataRowError):
    def __str__(self) -> str:
        return f"Missing value for '{self.col_name}'"


class MissingComponentError(DataRowError):
    def __str__(self) -> str:
        return f"Missing component data for {self.col_name}: '{self.value}'"


class UnexpectedTradingPairError(DataRowError):
    def __str__(self) -> str:
        return f"Unrecognised trading pair for {self.col_name}: '{self.value}'"


class DataParserError(Exception):
    def __init__(self, filename: str, worksheet: str = "") -> None:
        super().__init__()
        self.filename = filename
        self.worksheet = worksheet

    def format_filename(self) -> str:
        if self.worksheet:
            return f"{self.filename} '{self.worksheet}'"
        return self.filename


class UnknownCryptoassetError(DataParserError):
    def __str__(self) -> str:
        return f"Cryptoasset cannot be identified for data file: {self.format_filename()}"


class UnknownUsernameError(DataParserError):
    def __str__(self) -> str:
        return f"Username cannot be identified in data file: {self.format_filename()}"


class DataFormatUnrecognised(DataParserError):
    def __str__(self) -> str:
        return f"Data file format is unrecognised: {self.format_filename()}"


class DataFormatNotSupported(DataParserError):
    def __str__(self) -> str:
        return f"Data file format not supported: {self.format_filename()}"


class DataFilenameError(DataParserError):
    def __init__(self, filename: str, component: str) -> None:
        super().__init__(filename)
        self.component = component

    def __str__(self) -> str:
        return f"{self.component} cannot be identified from filename: {self.filename}"


class CurrencyConversionError(Exception):
    def __init__(self, from_currency: str, to_currency: str, timestamp: datetime) -> None:
        super().__init__()
        self.from_currency = from_currency
        self.to_currency = to_currency
        self.timestamp = timestamp

    def __str__(self) -> str:
        return (
            f"Conversion error: {self.from_currency}->{self.to_currency} "
            f"for {self.timestamp:%Y-%m-%d}"
        )
