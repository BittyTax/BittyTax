# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019


class DataRowError(Exception):
    def __init__(self, col_num, col_name, value=None):
        super().__init__()
        self.col_num = col_num
        self.col_name = col_name
        self.value = value


class UnexpectedTypeError(DataRowError):
    def __str__(self):
        return f"Unrecognised {self.col_name}: '{self.value}'"


class UnexpectedContentError(DataRowError):
    def __str__(self):
        return f"Unexpected {self.col_name} content: '{self.value}'"


class MissingValueError(DataRowError):
    def __str__(self):
        return f"Missing value for '{self.col_name}'"


class MissingComponentError(DataRowError):
    def __str__(self):
        return f"Missing component data for {self.col_name}: '{self.value}'"


class UnexpectedTradingPairError(DataRowError):
    def __str__(self):
        return f"Unrecognised trading pair for {self.col_name}: '{self.value}'"


class DataParserError(Exception):
    def __init__(self, filename, worksheet=None):
        super().__init__()
        self.filename = filename
        self.worksheet = worksheet

    def format_filename(self):
        if self.worksheet:
            return f"{self.filename} '{self.worksheet}'"
        return self.filename


class UnknownCryptoassetError(DataParserError):
    def __str__(self):
        return f"Cryptoasset cannot be identified for data file: {self.format_filename()}"


class UnknownUsernameError(DataParserError):
    def __str__(self):
        return f"Username cannot be identified in data file: {self.format_filename()}"


class DataFormatUnrecognised(DataParserError):
    def __str__(self):
        return f"Data file format is unrecognised: {self.format_filename()}"


class DataFilenameError(DataParserError):
    def __init__(self, filename, component):
        super().__init__(filename)
        self.component = component

    def __str__(self):
        return f"{self.component} cannot be identified from filename: {self.filename}"
