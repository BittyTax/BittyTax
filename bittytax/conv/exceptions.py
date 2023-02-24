# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019


class DataRowError(Exception):
    def __init__(self, col_num, col_name, value=None):
        super(DataRowError, self).__init__()
        self.col_num = col_num
        self.col_name = col_name
        self.value = value


class UnexpectedTypeError(DataRowError):
    def __str__(self):
        return "Unrecognised %s: '%s'" % (self.col_name, self.value)


class UnexpectedContentError(DataRowError):
    def __str__(self):
        return "Unexpected %s content: '%s'" % (self.col_name, self.value)


class MissingValueError(DataRowError):
    def __str__(self):
        return "Missing value for '%s'" % self.col_name


class MissingComponentError(DataRowError):
    def __str__(self):
        return "Missing component data for %s: '%s'" % (self.col_name, self.value)


class UnexpectedTradingPairError(DataRowError):
    def __str__(self):
        return "Unrecognised trading pair for %s: '%s'" % (self.col_name, self.value)


class DataParserError(Exception):
    def __init__(self, filename, worksheet=None):
        super(DataParserError, self).__init__()
        self.filename = filename
        self.worksheet = worksheet

    def format_filename(self):
        if self.worksheet:
            return "%s '%s'" % (self.filename, self.worksheet)
        return self.filename


class UnknownCryptoassetError(DataParserError):
    def __str__(self):
        return "Cryptoasset cannot be identified for data file: %s" % self.format_filename()


class UnknownUsernameError(DataParserError):
    def __str__(self):
        return "Username cannot be identified in data file: %s" % self.format_filename()


class DataFormatUnrecognised(DataParserError):
    def __str__(self):
        return "Data file format is unrecognised: %s" % self.format_filename()


class DataFilenameError(DataParserError):
    def __init__(self, filename, component):
        super(DataFilenameError, self).__init__(filename)
        self.component = component

    def __str__(self):
        return "%s cannot be identified from filename: %s" % (
            self.component,
            self.filename,
        )
