# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import argparse
import platform
import re
import sys
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union

import xlsxwriter
from colorama import Fore
from typing_extensions import TypedDict
from xlsxwriter.utility import xl_rowcol_to_cell

from ..config import config
from ..constants import TZ_UTC
from ..types import BUY_TYPES, SELL_TYPES, TrType, UnmappedType
from ..version import __version__
from .datafile import DataFile
from .datarow import DataRow
from .exceptions import DataRowError
from .out_record import TransactionOutRecord
from .output_csv import OutputBase

if platform.system() == "Darwin":
    # Default size for MacOS
    FONT_SIZE = 12
else:
    FONT_SIZE = 11


class Column(TypedDict):  # pylint: disable=too-few-public-methods
    header: str
    header_format: xlsxwriter.worksheet.Format


class OutputExcel(OutputBase):  # pylint: disable=too-many-instance-attributes
    FILE_EXTENSION = "xlsx"
    DATE_FORMAT = "yyyy-mm-dd hh:mm:ss"
    DATE_FORMAT_MS = "yyyy-mm-dd hh:mm:ss.000"  # Excel can only display milliseconds
    STR_FORMAT_MS = "%Y-%m-%dT%H:%M:%S.%f"
    FONT_COLOR_IN_DATA = "#808080"
    TITLE = "BittyTax Records"
    PROJECT_URL = "https://github.com/BittyTax/BittyTax"

    def __init__(self, progname: str, data_files: List[DataFile], args: argparse.Namespace) -> None:
        super().__init__(data_files)
        self.filename = self.get_output_filename(args.output_filename, self.FILE_EXTENSION)
        self.workbook = xlsxwriter.Workbook(self.filename)
        self.workbook.set_size(1800, 1200)
        self.workbook.formats[0].set_font_size(FONT_SIZE)
        self.workbook.set_properties(
            {
                "title": self.TITLE,
                "author": f"{progname} v{__version__}",
                "comments": self.PROJECT_URL,
            }
        )

        self.format_out_header = self.workbook.add_format(
            {
                "font_size": FONT_SIZE,
                "font_color": "white",
                "bold": True,
                "bg_color": "black",
            }
        )
        self.format_in_header = self.workbook.add_format(
            {
                "font_size": FONT_SIZE,
                "font_color": "white",
                "bold": True,
                "bg_color": self.FONT_COLOR_IN_DATA,
            }
        )
        self.format_out_data = self.workbook.add_format(
            {"font_size": FONT_SIZE, "font_color": "black"}
        )
        self.format_out_data_err = self.workbook.add_format(
            {"font_size": FONT_SIZE, "font_color": "red"}
        )
        self.format_in_data = self.workbook.add_format(
            {"font_size": FONT_SIZE, "font_color": self.FONT_COLOR_IN_DATA}
        )
        self.format_in_data_col_err = self.workbook.add_format(
            {
                "font_size": FONT_SIZE,
                "font_color": self.FONT_COLOR_IN_DATA,
                "diag_type": 3,
                "diag_border": 7,
                "diag_color": "red",
            }
        )
        self.format_in_data_err = self.workbook.add_format(
            {"font_size": FONT_SIZE, "font_color": "red"}
        )
        self.format_num_float = self.workbook.add_format(
            {
                "font_size": FONT_SIZE,
                "font_color": "black",
                "num_format": "#,##0." + "#" * 30,
            }
        )
        self.format_num_int = self.workbook.add_format({"num_format": "#,##0"})
        self.format_num_string = self.workbook.add_format(
            {"font_size": FONT_SIZE, "font_color": "black", "align": "right"}
        )
        self.format_currency = self.workbook.add_format(
            {
                "font_size": FONT_SIZE,
                "font_color": "black",
                "num_format": '"' + config.sym() + '"#,##0.00',
            }
        )
        self.format_timestamp = self.workbook.add_format(
            {
                "font_size": FONT_SIZE,
                "font_color": "black",
                "num_format": self.DATE_FORMAT,
            }
        )
        self.format_timestamp_ms = self.workbook.add_format(
            {
                "font_size": FONT_SIZE,
                "font_color": "black",
                "num_format": self.DATE_FORMAT_MS,
            }
        )

    def write_excel(self) -> None:
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
                    worksheet.worksheet.write(0, i, columns["header"], columns["header_format"])

            worksheet.autofit()

        self.workbook.close()
        sys.stderr.write(f"{Fore.WHITE}output EXCEL file created: {Fore.YELLOW}{self.filename}\n")


class Worksheet:
    SHEETNAME_MAX_LEN = 31
    MAX_COL_WIDTH = 30

    sheet_names: Dict[str, int] = {}
    table_names: Dict[str, int] = {}

    def __init__(self, output: OutputExcel, data_file: DataFile) -> None:
        self.output = output
        self.worksheet = output.workbook.add_worksheet(
            self._sheet_name(data_file.parser.worksheet_name)
        )
        self.col_width: Dict[int, int] = {}
        self.columns = self._make_columns(data_file.parser.in_header)
        self.microseconds, self.milliseconds = self._is_microsecond_timestamp(data_file.data_rows)

        self.worksheet.freeze_panes(1, len(self.output.BITTYTAX_OUT_HEADER))

    def _sheet_name(self, parser_name: str) -> str:
        # Remove special characters
        name = re.sub(r"[/\\\?\*\[\]:]", "", parser_name)
        name = name[: self.SHEETNAME_MAX_LEN] if len(name) > self.SHEETNAME_MAX_LEN else name

        if name.lower() not in self.sheet_names:
            self.sheet_names[name.lower()] = 1
            sheet_name = name
        else:
            self.sheet_names[name.lower()] += 1
            sheet_name = f"{name}({self.sheet_names[name.lower()]})"
            if len(sheet_name) > self.SHEETNAME_MAX_LEN:
                sheet_name = (
                    f"{name[: len(name) - (len(sheet_name) - self.SHEETNAME_MAX_LEN)]}"
                    f"({self.sheet_names[name.lower()]})"
                )

        return sheet_name

    def _table_name(self, parser_name: str) -> str:
        # Remove characters which are not allowed
        name = parser_name.replace(" ", "_")
        name = re.sub(r"[^a-zA-Z0-9\._]", "", name)

        if name.lower() not in self.table_names:
            self.table_names[name.lower()] = 1
        else:
            self.table_names[name.lower()] += 1
            name += str(self.table_names[name.lower()])

        return name

    def _make_columns(self, in_header: List[str]) -> List[Column]:
        col_names = {}
        columns = []

        for col_num, col_name in enumerate(self.output.BITTYTAX_OUT_HEADER + in_header):
            if col_name.lower() not in col_names:
                col_names[col_name.lower()] = 1
            else:
                col_names[col_name.lower()] += 1
                col_name += str(col_names[col_name.lower()])

            if col_num < len(self.output.BITTYTAX_OUT_HEADER):
                columns.append(
                    Column({"header": col_name, "header_format": self.output.format_out_header})
                )
            else:
                columns.append(
                    Column({"header": col_name, "header_format": self.output.format_in_header})
                )

            self._autofit_calc(col_num, len(col_name))

        return columns

    @staticmethod
    def _is_microsecond_timestamp(data_rows: List[DataRow]) -> Tuple[bool, bool]:
        milliseconds = bool(
            [
                dr.t_record.timestamp
                for dr in data_rows
                if dr.t_record and dr.t_record.timestamp.microsecond % 1000
            ]
        )
        microseconds = bool(
            [
                dr.t_record.timestamp
                for dr in data_rows
                if dr.t_record and dr.t_record.timestamp.microsecond
            ]
        )

        return milliseconds, microseconds

    def add_row(self, data_row: DataRow, row_num: int) -> None:
        self.worksheet.set_row(row_num, None, self.output.format_out_data)

        # Add transaction record
        if data_row.t_record:
            self._xl_type(data_row.t_record.t_type, row_num, 0, data_row.t_record)
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
            self._xl_note(data_row.t_record.note, row_num, 12)

        # Add original data
        for col_num, col_data in enumerate(data_row.row):
            if (
                data_row.failure
                and isinstance(data_row.failure, DataRowError)
                and data_row.failure.col_num == col_num
            ):
                cell_format = self.output.format_in_data_col_err
            elif data_row.failure and not isinstance(data_row.failure, DataRowError):
                cell_format = self.output.format_in_data_err
            else:
                cell_format = self.output.format_in_data

            self.worksheet.write(
                row_num,
                len(self.output.BITTYTAX_OUT_HEADER) + col_num,
                col_data,
                cell_format,
            )

            self._autofit_calc(len(self.output.BITTYTAX_OUT_HEADER) + col_num, len(col_data))

    def _xl_type(
        self,
        t_type: Union[TrType, UnmappedType],
        row_num: int,
        col_num: int,
        t_record: TransactionOutRecord,
    ) -> None:
        if t_type is TrType.TRADE or t_record.buy_asset and t_record.sell_asset:
            self.worksheet.data_validation(
                row_num,
                col_num,
                row_num,
                col_num,
                {"validate": "list", "source": [TrType.TRADE.value]},
            )
        elif t_type in BUY_TYPES or t_record.buy_asset and not t_record.sell_asset:
            self.worksheet.data_validation(
                row_num,
                col_num,
                row_num,
                col_num,
                {"validate": "list", "source": [t.value for t in BUY_TYPES]},
            )
        elif t_type in SELL_TYPES or t_record.sell_asset and not t_record.buy_asset:
            self.worksheet.data_validation(
                row_num,
                col_num,
                row_num,
                col_num,
                {"validate": "list", "source": [t.value for t in SELL_TYPES]},
            )
        if isinstance(t_type, TrType):
            self.worksheet.write_string(row_num, col_num, t_type.value)
            self._autofit_calc(col_num, len(t_type.value))
        else:
            self.worksheet.write_string(row_num, col_num, t_type)
            self._autofit_calc(col_num, len(t_type))

            self.worksheet.conditional_format(
                row_num,
                col_num,
                row_num,
                col_num,
                {
                    "type": "text",
                    "criteria": "begins with",
                    "value": "_",
                    "format": self.output.format_out_data_err,
                },
            )

    def _xl_quantity(self, quantity: Optional[Decimal], row_num: int, col_num: int) -> None:
        if quantity is not None:
            if len(quantity.normalize().as_tuple().digits) > OutputBase.EXCEL_PRECISION:
                self.worksheet.write_string(
                    row_num,
                    col_num,
                    f"{quantity.normalize():0f}",
                    self.output.format_num_string,
                )
            else:
                self.worksheet.write_number(
                    row_num, col_num, quantity.normalize(), self.output.format_num_float
                )
                cell = xl_rowcol_to_cell(row_num, col_num)
                self.worksheet.conditional_format(
                    row_num,
                    col_num,
                    row_num,
                    col_num,
                    {
                        "type": "formula",
                        "criteria": f"=INT({cell})={cell}",
                        "format": self.output.format_num_int,
                    },
                )
            self._autofit_calc(col_num, len(f"{quantity.normalize():0,f}"))

    def _xl_asset(self, asset: str, row_num: int, col_num: int) -> None:
        self.worksheet.write_string(row_num, col_num, asset)
        self._autofit_calc(col_num, len(asset))

    def _xl_value(self, value: Optional[Decimal], row_num: int, col_num: int) -> None:
        if value is not None:
            self.worksheet.write_number(
                row_num, col_num, value.normalize(), self.output.format_currency
            )
            self._autofit_calc(col_num, len(f"£{value:0,.2f}"))
        else:
            self.worksheet.write_blank(row_num, col_num, None, self.output.format_currency)

    def _xl_wallet(self, wallet: str, row_num: int, col_num: int) -> None:
        self.worksheet.write_string(row_num, col_num, wallet)
        self._autofit_calc(col_num, len(wallet))

    def _xl_timestamp(self, timestamp: datetime, row_num: int, col_num: int) -> None:
        utc_timestamp = timestamp.astimezone(TZ_UTC)
        utc_timestamp = timestamp.replace(tzinfo=None)

        if self.microseconds:
            # Excel datetime can only display milliseconds
            self.worksheet.write_string(
                row_num,
                col_num,
                f"{utc_timestamp:{self.output.STR_FORMAT_MS}}",
                self.output.format_num_string,
            )
            self._autofit_calc(col_num, len(f"{utc_timestamp:{self.output.STR_FORMAT_MS}}"))
        elif self.milliseconds:
            self.worksheet.write_datetime(
                row_num, col_num, utc_timestamp, self.output.format_timestamp_ms
            )
            self._autofit_calc(col_num, len(self.output.DATE_FORMAT_MS))
        else:
            self.worksheet.write_datetime(
                row_num, col_num, utc_timestamp, self.output.format_timestamp
            )
            self._autofit_calc(col_num, len(self.output.DATE_FORMAT))

    def _xl_note(self, note: str, row_num: int, col_num: int) -> None:
        self.worksheet.write_string(row_num, col_num, note)
        self._autofit_calc(col_num, len(note) if note else self.MAX_COL_WIDTH)

    def _autofit_calc(self, col_num: int, width: int) -> None:
        if width > self.MAX_COL_WIDTH:
            width = self.MAX_COL_WIDTH

        if col_num in self.col_width:
            if width > self.col_width[col_num]:
                self.col_width[col_num] = width
        else:
            self.col_width[col_num] = width

    def autofit(self) -> None:
        for col_num, col_width in self.col_width.items():
            self.worksheet.set_column(col_num, col_num, col_width)

    def make_table(self, rows: int, parser_name: str) -> None:
        self.worksheet.add_table(
            0,
            0,
            rows,
            len(self.columns) - 1,
            {
                "autofilter": False,
                "style": "Table Style Medium 13",
                "columns": self.columns,
                "name": self._table_name(parser_name),
            },
        )
