# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

class DataParserError(Exception):
    def __init__(self, col_num, col_name, value=None):
        super(DataParserError, self).__init__()
        self.col_num = col_num
        self.col_name = col_name
        self.value = value

class UnexpectedTypeError(DataParserError):
    def __str__(self):
        return 'Unrecognised {}: \'{}\''.format(self.col_name, self.value)

class MissingValueError(DataParserError):
    def __str__(self):
        return 'Missing value for \'{}\''.format(self.col_name)

class MissingComponentError(DataParserError):
    def __str__(self):
        return 'Missing component data for {}: \'{}\''.format(self.col_name, self.value)

class UnexpectedTradingPairError(DataParserError):
    def __str__(self):
        return 'Unrecognised trading pair for {}: \'{}\''.format(self.col_name, self.value)

class UnknownCryptoassetError(Exception):
    def __str__(self):
        return 'Cryptoasset cannot be identified'

class UnknownUsernameError(Exception):
    def __str__(self):
        return 'Username cannot be identified'

class DataFormatUnrecognised(Exception):
    def __str__(self):
        return 'Data file format unrecognised'
