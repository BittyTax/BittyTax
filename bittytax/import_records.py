# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import sys
import csv
from decimal import Decimal, InvalidOperation

import dateutil.parser
import xlrd

from .config import config
from .record import TransactionInRecord
from .exceptions import TransactionParserError, UnexpectedTransactionTypeError, \
                        TimestampParserError, DataValueError, MissingDataError, \
                        UnexpectedDataError, FeeAssetMismatchError

log = logging.getLogger()

class ImportRecords(object):
    def __init__(self):
        self.data_rows = []

    def import_excel(self, filename):
        workbook = xlrd.open_workbook(filename)
        log.info("==IMPORT TRANSACTION RECORDS FROM EXCEL FILE: %s ==", filename)

        for worksheet in workbook.sheets():
            for row_num in range(1, worksheet.nrows):
                row = [self.convert_cell(worksheet.cell(row_num, cell_num), workbook)
                       for cell_num in range(0, len(DataRow.HEADER))]

                data_row = DataRow(row, row_num+1, worksheet.name)
                try:
                    data_row.parse()
                except TransactionParserError as e:
                    data_row.failure = e

                if data_row.failure:
                    log.error("%s", data_row)
                    log.error("%s", data_row.failure)

                self.data_rows.append(data_row)

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
            value = str(cell.value)

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
            data_row = DataRow(row[:len(DataRow.HEADER)], reader.line_num)
            try:
                data_row.parse()
            except TransactionParserError as e:
                data_row.failure = e

            if data_row.failure:
                log.error("%s", data_row)
                log.error("%s", data_row.failure)

            self.data_rows.append(data_row)

    @staticmethod
    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode('utf-8')

    def failures(self):
        return bool([data_row for data_row in self.data_rows if data_row.failure is not None])

    def get_records(self):
        transaction_records = [dr.t_record for dr in self.data_rows if dr.t_record]

        transaction_records.sort()
        for tr in transaction_records:
            tr.set_tid()
            if tr.fee_quantity:
                tr.include_fees()

        for dr in self.data_rows:
            log.debug("%s", dr)

        log.info("Total transaction records=%s", len(transaction_records))
        return transaction_records

class DataRow(object):
    HEADER = ['Type',
              'Buy Quantity', 'Buy Asset', 'Buy Value',
              'Sell Quantity', 'Sell Asset', 'Sell Value',
              'Fee Quantity', 'Fee Asset', 'Fee Value',
              'Wallet', 'Timestamp']

    def __init__(self, row, row_num, worksheet_name=None):
        self.row = row
        self.row_num = row_num
        self.worksheet_name = worksheet_name
        self.t_record = None
        self.failure = None

    def parse(self):
        if all(not self.row[i] for i in range(len(DataRow.HEADER))):
            # Skip empty rows
            return

        timestamp = self.parse_timestamp(self.row[11])

        if self.row[0] in TransactionInRecord.BUY_TYPES:
            buy_quantity, buy_asset, buy_value = self.validate_buy(self.row)
            self.validate_no_sell(self.row)
            fee_quantity, fee_asset, fee_value = self.validate_fee(self.row, buy_asset)

            self.t_record = TransactionInRecord(self.row[0],
                                                timestamp,
                                                buy_quantity=buy_quantity,
                                                buy_asset=buy_asset,
                                                buy_value=buy_value,
                                                fee_quantity=fee_quantity,
                                                fee_asset=fee_asset,
                                                fee_value=fee_value,
                                                wallet=self.row[10])
        elif self.row[0] in TransactionInRecord.SELL_TYPES:
            self.validate_no_buy(self.row)
            sell_quantity, sell_asset, sell_value = self.validate_sell(self.row)
            fee_quantity, fee_asset, fee_value = self.validate_fee(self.row, sell_asset)

            self.t_record = TransactionInRecord(self.row[0],
                                                timestamp,
                                                sell_quantity=sell_quantity,
                                                sell_asset=sell_asset,
                                                sell_value=sell_value,
                                                fee_quantity=fee_quantity,
                                                fee_asset=fee_asset,
                                                fee_value=fee_value,
                                                wallet=self.row[10])
        elif self.row[0] == TransactionInRecord.TYPE_TRADE:
            buy_quantity, buy_asset, buy_value = self.validate_buy(self.row)
            sell_quantity, sell_asset, sell_value = self.validate_sell(self.row)
            fee_quantity, fee_asset, fee_value = self.validate_fee(self.row, buy_asset, sell_asset)

            self.t_record = TransactionInRecord(self.row[0],
                                                timestamp,
                                                buy_quantity=buy_quantity,
                                                buy_asset=buy_asset,
                                                buy_value=buy_value,
                                                sell_quantity=sell_quantity,
                                                sell_asset=sell_asset,
                                                sell_value=sell_value,
                                                fee_quantity=fee_quantity,
                                                fee_asset=fee_asset,
                                                fee_value=fee_value,
                                                wallet=self.row[10])

        else:
            raise UnexpectedTransactionTypeError(0, DataRow.HEADER[0], self.row[0])

    @staticmethod
    def parse_timestamp(timestamp_str):
        try:
            timestamp = dateutil.parser.parse(timestamp_str, tzinfos=config.TZ_INFOS)
        except ValueError:
            raise TimestampParserError(11, DataRow.HEADER[11], timestamp_str)

        if timestamp.tzinfo is None:
            # Default to UTC if no timezone is specified
            timestamp = timestamp.replace(tzinfo=config.TZ_UTC)

        # Convert to local time
        timestamp = timestamp.astimezone(config.TZ_LOCAL)

        return timestamp

    @staticmethod
    def validate_buy(row):
        if row[1]:
            try:
                buy_quantity = Decimal(DataRow.strip_non_digits(row[1]))
            except InvalidOperation:
                raise DataValueError(1, DataRow.HEADER[1], row[1])

            if buy_quantity < 0:
                raise DataValueError(1, DataRow.HEADER[1], buy_quantity)
        else:
            raise MissingDataError(1, DataRow.HEADER[1])

        if row[2]:
            buy_asset = row[2]
        else:
            raise MissingDataError(2, DataRow.HEADER[2])

        if row[3]:
            try:
                buy_value = Decimal(DataRow.strip_non_digits(row[3]))
            except InvalidOperation:
                raise DataValueError(3, DataRow.HEADER[3], row[3])

            if buy_value < 0:
                raise DataValueError(3, DataRow.HEADER[3], buy_value)

            if buy_asset == config.CCY and buy_value != buy_quantity:
                raise DataValueError(3, DataRow.HEADER[3], buy_value)
        else:
            buy_value = None

        return buy_quantity, buy_asset, buy_value

    @staticmethod
    def validate_no_buy(row):
        if row[1]:
            raise UnexpectedDataError(1, DataRow.HEADER[1], row[1])

        if row[2]:
            raise UnexpectedDataError(2, DataRow.HEADER[2], row[2])

        if row[3]:
            raise UnexpectedDataError(3, DataRow.HEADER[3], row[3])

    @staticmethod
    def validate_sell(row):
        if row[4]:
            try:
                sell_quantity = Decimal(DataRow.strip_non_digits(row[4]))
            except InvalidOperation:
                raise DataValueError(4, DataRow.HEADER[4], row[4])

            if sell_quantity < 0:
                raise DataValueError(4, DataRow.HEADER[4], sell_quantity)
        else:
            raise MissingDataError(4, DataRow.HEADER[4])

        if row[5]:
            sell_asset = row[5]
        else:
            raise MissingDataError(5, DataRow.HEADER[5])

        if row[6]:
            try:
                sell_value = Decimal(DataRow.strip_non_digits(row[6]))
            except InvalidOperation:
                raise DataValueError(6, DataRow.HEADER[6], row[6])

            if sell_value < 0:
                raise DataValueError(6, DataRow.HEADER[6], sell_value)

            if sell_asset == config.CCY and sell_value != sell_quantity:
                raise DataValueError(6, DataRow.HEADER[6], sell_value)
        else:
            sell_value = None

        return sell_quantity, sell_asset, sell_value

    @staticmethod
    def validate_no_sell(row):
        if row[4]:
            raise UnexpectedDataError(4, DataRow.HEADER[4], row[4])

        if row[5]:
            raise UnexpectedDataError(5, DataRow.HEADER[5], row[5])

        if row[6]:
            raise UnexpectedDataError(6, DataRow.HEADER[6], row[6])

    @staticmethod
    def validate_fee(row, buy_asset=None, sell_asset=None):
        if row[7]:
            try:
                fee_quantity = Decimal(DataRow.strip_non_digits(row[7]))
            except InvalidOperation:
                raise DataValueError(7, DataRow.HEADER[7], row[7])

            if fee_quantity < 0:
                raise DataValueError(7, DataRow.HEADER[7], fee_quantity)
        else:
            fee_quantity = None

        if row[8]:
            fee_asset = row[8]
        else:
            fee_asset = None

        if row[9]:
            try:
                fee_value = Decimal(DataRow.strip_non_digits(row[9]))
            except InvalidOperation:
                raise DataValueError(9, DataRow.HEADER[9], row[9])

            if fee_value < 0:
                raise DataValueError(9, DataRow.HEADER[9], fee_value)

            if fee_asset == config.CCY and fee_value != fee_quantity:
                raise DataValueError(9, DataRow.HEADER[9], fee_value)
        else:
            fee_value = None

        if fee_quantity is not None and not fee_asset:
            raise MissingDataError(8, DataRow.HEADER[8])
        elif fee_quantity is None and fee_asset:
            raise MissingDataError(7, DataRow.HEADER[7])

        if fee_asset and (fee_asset != buy_asset and fee_asset != sell_asset):
            raise FeeAssetMismatchError(8, DataRow.HEADER[8], fee_asset)

        return fee_quantity, fee_asset, fee_value

    @staticmethod
    def strip_non_digits(string):
        return string.strip('£€$').replace(',', '')

    def __str__(self):
        if self.t_record and self.t_record.tid:
            tid_str = " TID:" + str(self.t_record.tid)
        else:
            tid_str = ""

        if self.worksheet_name:
            return "'" + self.worksheet_name + \
                   "' Row[" + str(self.row_num) + "]: " + \
                   '[' + '\'{0}\''.format('\', \''.join(self.row)) + ']' + \
                   tid_str
        else:
            return "Row[" + str(self.row_num) + "]: " + \
                   '[' + '\'{0}\''.format('\', \''.join(self.row)) + ']' + \
                   tid_str
