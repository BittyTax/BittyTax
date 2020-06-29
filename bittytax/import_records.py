# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import sys
import csv
from decimal import Decimal, InvalidOperation

import dateutil.parser
import xlrd

from .config import config
from .transactions import Buy, Sell
from .record import TransactionRecord
from .exceptions import TransactionParserError, UnexpectedTransactionTypeError, \
                        TimestampParserError, DataValueError, MissingDataError, \
                        UnexpectedDataError

log = logging.getLogger()

class ImportRecords(object):
    def __init__(self):
        self.t_rows = []

    def import_excel(self, filename):
        workbook = xlrd.open_workbook(filename)
        log.info("==IMPORT TRANSACTION RECORDS FROM EXCEL FILE: %s ==", filename)

        for worksheet in workbook.sheets():
            for row_num in range(1, worksheet.nrows):
                row = [self.convert_cell(worksheet.cell(row_num, cell_num), workbook)
                       for cell_num in range(0, worksheet.ncols)]

                t_row = TransactionRow(row[:len(TransactionRow.HEADER)], row_num+1, worksheet.name)
                try:
                    t_row.parse()
                except TransactionParserError as e:
                    t_row.failure = e

                if t_row.failure:
                    log.error("%s", t_row)
                    log.error("%s", t_row.failure)

                self.t_rows.append(t_row)

        workbook.release_resources()
        del workbook

    @staticmethod
    def convert_cell(cell, workbook):
        if cell.ctype == xlrd.XL_CELL_DATE:
            value = xlrd.xldate.xldate_as_datetime(cell.value, workbook.datemode). \
                         strftime('%Y-%m-%d %H:%M:%S')
        elif cell.ctype == xlrd.XL_CELL_NUMBER:
            # repr is required to ensure no precision is lost
            value = repr(cell.value)
        else:
            if sys.version_info[0] >= 3:
                value = str(cell.value)
            else:
                value = cell.value.encode('utf-8')

        return value

    def import_csv(self, import_file):
        log.info("==IMPORT TRANSACTION RECORDS FROM CSV FILE: %s ==", import_file.name)

        if sys.version_info[0] < 3:
            # Special handling required for utf-8 encoded csv files
            reader = csv.reader(self.utf_8_encoder(import_file))
        else:
            reader = csv.reader(import_file)

        next(reader, None) # skip headers
        for row in reader:
            t_row = TransactionRow(row[:len(TransactionRow.HEADER)], reader.line_num)
            try:
                t_row.parse()
            except TransactionParserError as e:
                t_row.failure = e

            if t_row.failure:
                log.error("%s", t_row)
                log.error("%s", t_row.failure)

            self.t_rows.append(t_row)

    @staticmethod
    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode('utf-8')

    def failures(self):
        return bool([t_row for t_row in self.t_rows if t_row.failure is not None])

    def get_records(self):
        transaction_records = [t_row.t_record for t_row in self.t_rows if t_row.t_record]

        transaction_records.sort()
        for t_record in transaction_records:
            t_record.set_tid()

        for t_row in self.t_rows:
            log.debug("%s", t_row)

        log.info("Total transaction records=%s", len(transaction_records))
        return transaction_records

class TransactionRow(object):
    HEADER = ['Type',
              'Buy Quantity', 'Buy Asset', 'Buy Value',
              'Sell Quantity', 'Sell Asset', 'Sell Value',
              'Fee Quantity', 'Fee Asset', 'Fee Value',
              'Wallet', 'Timestamp']

    BUY_TYPES = (TransactionRecord.TYPE_DEPOSIT,
                 TransactionRecord.TYPE_MINING,
                 TransactionRecord.TYPE_INCOME,
                 TransactionRecord.TYPE_GIFT_RECEIVED)
    SELL_TYPES = (TransactionRecord.TYPE_WITHDRAWAL,
                  TransactionRecord.TYPE_SPEND,
                  TransactionRecord.TYPE_GIFT_SENT,
                  TransactionRecord.TYPE_CHARITY_SENT)

    TRANSFER_TYPES = (TransactionRecord.TYPE_DEPOSIT,
                      TransactionRecord.TYPE_WITHDRAWAL)

    cnt = 0

    def __init__(self, row, row_num, worksheet_name=None):
        self.row = row
        self.row_num = row_num
        self.worksheet_name = worksheet_name
        self.t_record = None
        self.failure = None

    def parse(self):
        if all(not self.row[i] for i in range(len(self.row))):
            # Skip empty rows
            return

        buy = sell = fee = None
        buy_asset = sell_asset = fee_asset = None

        t_type = self.row[0]
        if t_type in self.BUY_TYPES:
            buy_quantity, buy_asset, buy_value = self.validate_buy(self.row)
            self.validate_no_sell(self.row)
            fee_quantity, fee_asset, fee_value = self.validate_fee(self.row)
        elif t_type in self.SELL_TYPES:
            self.validate_no_buy(self.row)
            sell_quantity, sell_asset, sell_value = self.validate_sell(self.row)
            fee_quantity, fee_asset, fee_value = self.validate_fee(self.row)
        elif t_type == TransactionRecord.TYPE_TRADE:
            buy_quantity, buy_asset, buy_value = self.validate_buy(self.row)
            sell_quantity, sell_asset, sell_value = self.validate_sell(self.row)
            fee_quantity, fee_asset, fee_value = self.validate_fee(self.row)
        else:
            raise UnexpectedTransactionTypeError(0, self.HEADER[0], t_type)

        if buy_asset:
            buy = Buy(t_type, buy_quantity, buy_asset, buy_value)
        if sell_asset:
            sell = Sell(t_type, sell_quantity, sell_asset, sell_value)
        if fee_asset:
            # Fees are added as a separate spend transaction
            fee = Sell(TransactionRecord.TYPE_SPEND, fee_quantity, fee_asset, fee_value)
            if t_type in self.TRANSFER_TYPES:
                # A fee spend is normally a disposal unless it's part of a transfer
                fee.disposal = False

        self.t_record = TransactionRecord(t_type, buy, sell, fee, self.row[10],
                                          self.parse_timestamp(self.row[11]))

    @staticmethod
    def parse_timestamp(timestamp_str):
        try:
            timestamp = dateutil.parser.parse(timestamp_str, tzinfos=config.TZ_INFOS)
        except ValueError:
            raise TimestampParserError(11, TransactionRow.HEADER[11], timestamp_str)

        if timestamp.tzinfo is None:
            # Default to UTC if no timezone is specified
            timestamp = timestamp.replace(tzinfo=config.TZ_UTC)

        return timestamp

    @staticmethod
    def validate_buy(row):
        if row[1]:
            try:
                buy_quantity = Decimal(TransactionRow.strip_non_digits(row[1]))
            except InvalidOperation:
                raise DataValueError(1, TransactionRow.HEADER[1], row[1])

            if buy_quantity < 0:
                raise DataValueError(1, TransactionRow.HEADER[1], buy_quantity)
        else:
            raise MissingDataError(1, TransactionRow.HEADER[1])

        if row[2]:
            buy_asset = row[2]
        else:
            raise MissingDataError(2, TransactionRow.HEADER[2])

        if row[3]:
            try:
                buy_value = Decimal(TransactionRow.strip_non_digits(row[3]))
            except InvalidOperation:
                raise DataValueError(3, TransactionRow.HEADER[3], row[3])

            if buy_value < 0:
                raise DataValueError(3, TransactionRow.HEADER[3], buy_value)

            if buy_asset == config.CCY and buy_value != buy_quantity:
                raise DataValueError(3, TransactionRow.HEADER[3], buy_value)
        else:
            buy_value = None

        return buy_quantity, buy_asset, buy_value

    @staticmethod
    def validate_no_buy(row):
        if row[1]:
            raise UnexpectedDataError(1, TransactionRow.HEADER[1], row[1])

        if row[2]:
            raise UnexpectedDataError(2, TransactionRow.HEADER[2], row[2])

        if row[3]:
            raise UnexpectedDataError(3, TransactionRow.HEADER[3], row[3])

    @staticmethod
    def validate_sell(row):
        if row[4]:
            try:
                sell_quantity = Decimal(TransactionRow.strip_non_digits(row[4]))
            except InvalidOperation:
                raise DataValueError(4, TransactionRow.HEADER[4], row[4])

            if sell_quantity < 0:
                raise DataValueError(4, TransactionRow.HEADER[4], sell_quantity)
        else:
            raise MissingDataError(4, TransactionRow.HEADER[4])

        if row[5]:
            sell_asset = row[5]
        else:
            raise MissingDataError(5, TransactionRow.HEADER[5])

        if row[6]:
            try:
                sell_value = Decimal(TransactionRow.strip_non_digits(row[6]))
            except InvalidOperation:
                raise DataValueError(6, TransactionRow.HEADER[6], row[6])

            if sell_value < 0:
                raise DataValueError(6, TransactionRow.HEADER[6], sell_value)

            if sell_asset == config.CCY and sell_value != sell_quantity:
                raise DataValueError(6, TransactionRow.HEADER[6], sell_value)
        else:
            sell_value = None

        return sell_quantity, sell_asset, sell_value

    @staticmethod
    def validate_no_sell(row):
        if row[4]:
            raise UnexpectedDataError(4, TransactionRow.HEADER[4], row[4])

        if row[5]:
            raise UnexpectedDataError(5, TransactionRow.HEADER[5], row[5])

        if row[6]:
            raise UnexpectedDataError(6, TransactionRow.HEADER[6], row[6])

    @staticmethod
    def validate_fee(row):
        if row[7]:
            try:
                fee_quantity = Decimal(TransactionRow.strip_non_digits(row[7]))
            except InvalidOperation:
                raise DataValueError(7, TransactionRow.HEADER[7], row[7])

            if fee_quantity < 0:
                raise DataValueError(7, TransactionRow.HEADER[7], fee_quantity)
        else:
            fee_quantity = None

        if row[8]:
            fee_asset = row[8]
        else:
            fee_asset = None

        if row[9]:
            try:
                fee_value = Decimal(TransactionRow.strip_non_digits(row[9]))
            except InvalidOperation:
                raise DataValueError(9, TransactionRow.HEADER[9], row[9])

            if fee_value < 0:
                raise DataValueError(9, TransactionRow.HEADER[9], fee_value)

            if fee_asset == config.CCY and fee_value != fee_quantity:
                raise DataValueError(9, TransactionRow.HEADER[9], fee_value)
        else:
            fee_value = None

        if fee_quantity is not None and not fee_asset:
            raise MissingDataError(8, TransactionRow.HEADER[8])
        elif fee_quantity is None and fee_asset:
            raise MissingDataError(7, TransactionRow.HEADER[7])

        return fee_quantity, fee_asset, fee_value

    @staticmethod
    def strip_non_digits(string):
        return string.strip('£€$').replace(',', '')

    def __str__(self):
        if self.t_record and self.t_record.tid:
            tid_str = " TID:" + str(self.t_record.tid[0])
        else:
            tid_str = ""

        if self.worksheet_name:
            return "'" + self.worksheet_name + \
                   "' Row[" + str(self.row_num) + "]: " + \
                   '[' + '\'{0}\''.format('\', \''.join(self.row)) + ']' + \
                   tid_str

        return "Row[" + str(self.row_num) + "]: " + \
               '[' + '\'{0}\''.format('\', \''.join(self.row)) + ']' + \
               tid_str
