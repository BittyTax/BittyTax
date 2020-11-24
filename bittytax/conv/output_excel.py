# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
import platform
import re

from colorama import Fore
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

from ..version import __version__
from ..config import config
from .out_record import TransactionOutRecord
from .output_csv import OutputBase

if platform.system() == 'Darwin':
    # Default size for MacOS
    FONT_SIZE = 12
else:
    FONT_SIZE = 11

class OutputExcel(OutputBase):
    FILE_EXTENSION = 'xlsx'
    DATE_FORMAT = 'yyyy-mm-dd hh:mm:ss'
    DATE_FORMAT_MS = 'yyyy-mm-dd hh:mm:ss.000' # Excel can only display 3 digits of microseconds
    FONT_COLOR_IN_DATA = '#808080'
    TITLE = 'BittyTax Records'
    PROJECT_URL = 'https://github.com/BittyTax/BittyTax'

    def __init__(self, progname, data_files):
        super(OutputExcel, self).__init__(data_files)
        self.filename = self.get_output_filename(self.FILE_EXTENSION)
        self.workbook = xlsxwriter.Workbook(self.filename)
        self.workbook.set_size(1800, 1200)
        self.workbook.formats[0].set_font_size(FONT_SIZE)
        self.workbook.set_properties({'title': self.TITLE,
                                      'author': '%s v%s' % (progname, __version__),
                                      'comments': self.PROJECT_URL})

        self.format_out_header = self.workbook.add_format({'font_size': FONT_SIZE,
                                                           'font_color': 'white',
                                                           'bold': True,
                                                           'bg_color': 'black'})
        self.format_in_header = self.workbook.add_format({'font_size': FONT_SIZE,
                                                          'font_color': 'white',
                                                          'bold': True,
                                                          'bg_color': self.FONT_COLOR_IN_DATA})
        self.format_out_data = self.workbook.add_format({'font_size': FONT_SIZE,
                                                         'font_color': 'black'})
        self.format_in_data = self.workbook.add_format({'font_size': FONT_SIZE,
                                                        'font_color': self.FONT_COLOR_IN_DATA})
        self.format_in_data_err = self.workbook.add_format({'font_size': FONT_SIZE,
                                                            'font_color': self.FONT_COLOR_IN_DATA,
                                                            'diag_type': 3,
                                                            'diag_border': 7,
                                                            'diag_color': 'red'})
        self.format_num_float = self.workbook.add_format({'font_size': FONT_SIZE,
                                                          'font_color': 'black',
                                                          'num_format': '#,##0.' + '#' * 30})
        self.format_num_int = self.workbook.add_format({'num_format': '#,##0'})
        self.format_num_string = self.workbook.add_format({'font_size': FONT_SIZE,
                                                           'font_color': 'black',
                                                           'align': 'right'})
        self.format_currency = self.workbook.add_format({'font_size': FONT_SIZE,
                                                         'font_color': 'black',
                                                         'num_format': '"' + config.sym() +
                                                                       '"#,##0.00'})
        self.format_timestamp = self.workbook.add_format({'font_size': FONT_SIZE,
                                                          'font_color': 'black',
                                                          'num_format': self.DATE_FORMAT})
        self.format_timestamp_ms = self.workbook.add_format({'font_size': FONT_SIZE,
                                                             'font_color': 'black',
                                                             'num_format': self.DATE_FORMAT_MS})

    def write_excel(self):
        data_files = sorted(self.data_files, key=lambda df: df.parser.worksheet_name, reverse=False)
        for data_file in data_files:
            worksheet = Worksheet(self, data_file)

            data_rows = sorted(data_file.data_rows, key=lambda dr: dr.timestamp, reverse=False)
            for i, data_row in enumerate(data_rows):
                worksheet.add_row(data_row, i + 1)

            if data_rows:
                worksheet.make_table(len(data_rows), data_file.parser.worksheet_name)
            else:
                # Just add headings
                for i, columns in enumerate(worksheet.columns):
                    worksheet.worksheet.write(0, i, columns['header'], columns['header_format'])

            worksheet.autofit()

        self.workbook.close()
        sys.stderr.write("%soutput EXCEL file created: %s%s\n" % (
            Fore.WHITE, Fore.YELLOW, self.filename))

class Worksheet(object):
    BUY_LIST = (TransactionOutRecord.TYPE_DEPOSIT,
                TransactionOutRecord.TYPE_MINING,
                TransactionOutRecord.TYPE_STAKING,
                TransactionOutRecord.TYPE_INTEREST,
                TransactionOutRecord.TYPE_DIVIDEND,
                TransactionOutRecord.TYPE_INCOME,
                TransactionOutRecord.TYPE_GIFT_RECEIVED)

    SELL_LIST = (TransactionOutRecord.TYPE_WITHDRAWAL,
                 TransactionOutRecord.TYPE_SPEND,
                 TransactionOutRecord.TYPE_GIFT_SENT,
                 TransactionOutRecord.TYPE_GIFT_SPOUSE,
                 TransactionOutRecord.TYPE_CHARITY_SENT)
    SHEETNAME_MAX_LEN = 31
    MAX_COL_WIDTH = 30

    sheet_names = {}
    table_names = {}

    def __init__(self, output, data_file):
        self.output = output
        self.worksheet = output.workbook.add_worksheet(self._sheet_name( \
                                                       data_file.parser.worksheet_name))
        self.col_width = {}
        self.columns = self._make_columns(data_file.parser.in_header)

        self.worksheet.freeze_panes(1, len(self.output.BITTYTAX_OUT_HEADER))

    def _sheet_name(self, parser_name):
        # Remove special characters
        name = re.sub(r'[/\\\?\*\[\]:]', '', parser_name)
        name = name[:self.SHEETNAME_MAX_LEN] if len(name) > self.SHEETNAME_MAX_LEN else name

        if name.lower() not in self.sheet_names:
            self.sheet_names[name.lower()] = 1
            sheet_name = name
        else:
            self.sheet_names[name.lower()] += 1
            sheet_name = '%s(%s)' % (name, self.sheet_names[name.lower()])
            if len(sheet_name) > self.SHEETNAME_MAX_LEN:
                sheet_name = '%s(%s)' % (name[:len(name) - (len(sheet_name)
                                                            - self.SHEETNAME_MAX_LEN)],
                                         self.sheet_names[name.lower()])

        return sheet_name

    def _table_name(self, parser_name):
        # Remove characters which are not allowed
        name = parser_name.replace(' ', '_')
        name = re.sub(r'[^a-zA-Z0-9\._]', '', name)

        if name.lower() not in self.table_names:
            self.table_names[name.lower()] = 1
        else:
            self.table_names[name.lower()] += 1
            name += str(self.table_names[name.lower()])

        return name

    def _make_columns(self, in_header):
        if sys.version_info[0] < 3:
            in_header = [h.decode('utf8') for h in in_header]

        col_names = {}
        columns = []

        for col_num, col_name in enumerate(self.output.BITTYTAX_OUT_HEADER + in_header):
            if col_name.lower() not in col_names:
                col_names[col_name.lower()] = 1
            else:
                col_names[col_name.lower()] += 1
                col_name += str(col_names[col_name.lower()])

            if col_num < len(self.output.BITTYTAX_OUT_HEADER):
                columns.append({'header': col_name, 'header_format': self.output.format_out_header})
            else:
                columns.append({'header': col_name, 'header_format': self.output.format_in_header})

            self._autofit_calc(col_num, len(col_name))

        return columns

    def add_row(self, data_row, row_num):
        self.worksheet.set_row(row_num, None, self.output.format_out_data)

        # Add transaction record
        if data_row.t_record:
            self._xl_type(data_row.t_record.t_type, row_num, 0)
            self._xl_quantity(data_row.t_record.buy_quantity, row_num, 1)
            self._xl_asset(data_row.t_record.buy_asset, row_num, 2)
            self._xl_value(data_row.t_record.buy_value, row_num, 3)
            self._xl_quantity(data_row.t_record.sell_quantity, row_num, 4)
            self._xl_asset(data_row.t_record.sell_asset, row_num, 5)
            self._xl_value(data_row.t_record.sell_value, row_num, 6)
            self._xl_quantity(data_row.t_record.fee_quantity, row_num, 7)
            self._xl_asset(data_row.t_record.fee_asset, row_num, 8)
            self._xl_value(data_row.t_record.fee_value, row_num, 9)
            self._xl_wallet(data_row.t_record.wallet, row_num, 10)
            self._xl_timestamp(data_row.t_record.timestamp, row_num, 11)

        if sys.version_info[0] < 3:
            in_row = [r.decode('utf8') for r in data_row.in_row]
        else:
            in_row = data_row.in_row

        # Add original data
        for col_num, col_data in enumerate(in_row):
            if data_row.failure and data_row.failure.col_num == col_num:
                self.worksheet.write(row_num, 12 + col_num, col_data,
                                     self.output.format_in_data_err)
            else:
                self.worksheet.write(row_num, 12 + col_num, col_data,
                                     self.output.format_in_data)

            self._autofit_calc(12 + col_num, len(col_data))

    def _xl_type(self, t_type, row_num, col_num):
        if t_type in self.BUY_LIST:
            self.worksheet.data_validation(row_num, col_num, row_num, col_num,
                                           {'validate': 'list',
                                            'source': list(self.BUY_LIST)})
        elif t_type in self.SELL_LIST:
            self.worksheet.data_validation(row_num, col_num, row_num, col_num,
                                           {'validate': 'list',
                                            'source': list(self.SELL_LIST)})
        else:
            self.worksheet.data_validation(row_num, col_num, row_num, col_num,
                                           {'validate': 'list',
                                            'source': [TransactionOutRecord.TYPE_TRADE]})

        self.worksheet.write_string(row_num, col_num, t_type)
        self._autofit_calc(col_num, len(t_type))

    def _xl_quantity(self, quantity, row_num, col_num):
        if quantity is not None:
            if len(quantity.normalize().as_tuple().digits) > OutputBase.EXCEL_PRECISION:
                self.worksheet.write_string(row_num, col_num,
                                            '{0:f}'.format(quantity.normalize()),
                                            self.output.format_num_string)
            else:
                self.worksheet.write_number(row_num, col_num,
                                            quantity.normalize(), self.output.format_num_float)
                cell = xl_rowcol_to_cell(row_num, col_num)
                self.worksheet.conditional_format(row_num, col_num, row_num, col_num,
                                                  {'type': 'formula',
                                                   'criteria': '=INT(' + cell + ')=' + cell,
                                                   'format':  self.output.format_num_int})
            self._autofit_calc(col_num, len('{:0,f}'.format(quantity.normalize())))

    def _xl_asset(self, asset, row_num, col_num):
        self.worksheet.write_string(row_num, col_num, asset)
        self._autofit_calc(col_num, len(asset))

    def _xl_value(self, value, row_num, col_num):
        if value is not None:
            self.worksheet.write_number(row_num, col_num, value.normalize(),
                                        self.output.format_currency)
            self._autofit_calc(col_num, len('£{:0,.2f}'.format(value)))
        else:
            self.worksheet.write_blank(row_num, col_num, None, self.output.format_currency)

    def _xl_wallet(self, wallet, row_num, col_num):
        self.worksheet.write_string(row_num, col_num, wallet)
        self._autofit_calc(col_num, len(wallet))

    def _xl_timestamp(self, timestamp, row_num, col_num):
        utc_timestamp = timestamp.astimezone(config.TZ_UTC)
        utc_timestamp = timestamp.replace(tzinfo=None)

        if utc_timestamp.time().microsecond:
            self.worksheet.write_datetime(row_num, col_num, utc_timestamp,
                                          self.output.format_timestamp_ms)
            self._autofit_calc(col_num, len(self.output.DATE_FORMAT_MS))
        else:
            self.worksheet.write_datetime(row_num, col_num, utc_timestamp,
                                          self.output.format_timestamp)
            self._autofit_calc(col_num, len(self.output.DATE_FORMAT))

    def _autofit_calc(self, col_num, width):
        if width > self.MAX_COL_WIDTH:
            width = self.MAX_COL_WIDTH

        if col_num in self.col_width:
            if width > self.col_width[col_num]:
                self.col_width[col_num] = width
        else:
            self.col_width[col_num] = width

    def autofit(self):
        for col_num in self.col_width:
            self.worksheet.set_column(col_num, col_num, self.col_width[col_num])

    def make_table(self, rows, parser_name):
        self.worksheet.add_table(0, 0, rows, len(self.columns) - 1,
                                 {'autofilter': False,
                                  'style': 'Table Style Medium 13',
                                  'columns': self.columns,
                                  'name': self._table_name(parser_name)})
