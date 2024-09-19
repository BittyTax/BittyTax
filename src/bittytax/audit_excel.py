# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import os
import platform
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

import xlsxwriter
from colorama import Fore
from typing_extensions import TypedDict
from xlsxwriter.utility import xl_rowcol_to_cell

from .audit import AuditLogEntry
from .bt_types import BUY_TYPES, SELL_TYPES, AssetSymbol, TrRecordPart, TrType
from .config import config
from .constants import EXCEL_PRECISION, PROJECT_URL, TZ_UTC
from .report import ProgressSpinner
from .t_row import TransactionRow
from .version import __version__

if platform.system() == "Darwin":
    # Default size for MacOS
    FONT_SIZE = 12
else:
    FONT_SIZE = 11


class Column(TypedDict):  # pylint: disable=too-few-public-methods
    header: str
    header_format: xlsxwriter.worksheet.Format


class AuditLogExcel:  # pylint: disable=too-few-public-methods, too-many-instance-attributes
    DEFAULT_FILENAME = "BittyTax_Audit_Log"
    FILE_EXTENSION = "xlsx"
    AUDIT_HEADER = [
        "Asset",
        "Wallet",
        "Balance",
        "Change",
        "Fee",
        "Total ({{asset}})",
        "Type",
        "Timestamp",
        "Note",
        "TxHash",
        "TxSrc",
        "TxDest",
    ]

    DATE_FORMAT = "yyyy-mm-dd hh:mm:ss"
    DATE_FORMAT_MS = "yyyy-mm-dd hh:mm:ss.000"  # Excel can only display milliseconds
    STR_FORMAT_MS = "%Y-%m-%dT%H:%M:%S.%f"
    FONT_COLOR_GREY = "#808080"
    FONT_COLOR_BLUE = "#29477C"

    TITLE = "BittyTax Audit"

    def __init__(self, progname: str, audit_log: Dict[AssetSymbol, List[AuditLogEntry]]) -> None:
        self.audit_log = audit_log
        self.filename = self._get_output_filename()
        self.workbook = xlsxwriter.Workbook(self.filename)
        self.workbook.set_size(1800, 1200)
        self.workbook.formats[0].set_font_size(FONT_SIZE)
        self.workbook.set_properties(
            {
                "title": self.TITLE,
                "author": f"{progname} v{__version__}",
                "comments": PROJECT_URL,
            }
        )

        self.format_header = self.workbook.add_format(
            {
                "font_size": FONT_SIZE,
                "font_color": "white",
                "bold": True,
                "bg_color": "black",
                "border": 1,
                "border_color": "white",
            }
        )
        self.format_text_grey = self.workbook.add_format(
            {"font_size": FONT_SIZE, "font_color": self.FONT_COLOR_GREY}
        )
        self.format_num_float_unsigned = self.workbook.add_format(
            {
                "font_size": FONT_SIZE,
                "font_color": "black",
                "num_format": "#,##0." + "#" * 30,
            }
        )
        self.format_num_float_unsigned_red = self.workbook.add_format(
            {
                "font_size": FONT_SIZE,
                "font_color": "red",
                "num_format": "#,##0." + "#" * 30,
            }
        )
        self.format_num_float_signed = self.workbook.add_format(
            {
                "font_size": FONT_SIZE,
                "font_color": self.FONT_COLOR_BLUE,
                "num_format": "+#,##0." + "#" * 30 + ";-#,##0." + "#" * 30 + ";0",
            }
        )
        self.format_num_int_unsigned = self.workbook.add_format({"num_format": "#,##0"})
        self.format_num_int_signed = self.workbook.add_format({"num_format": "+#,##0;-#,##0;0"})
        self.format_num_string_unsigned = self.workbook.add_format(
            {"font_size": FONT_SIZE, "font_color": "black", "align": "right"}
        )
        self.format_num_string_unsigned_red = self.workbook.add_format(
            {"font_size": FONT_SIZE, "font_color": "red", "align": "right"}
        )
        self.format_num_string_signed = self.workbook.add_format(
            {"font_size": FONT_SIZE, "font_color": self.FONT_COLOR_BLUE, "align": "right"}
        )
        self.format_timestamp = self.workbook.add_format(
            {
                "font_size": FONT_SIZE,
                "font_color": self.FONT_COLOR_GREY,
                "num_format": self.DATE_FORMAT,
            }
        )
        self.format_timestamp_ms = self.workbook.add_format(
            {
                "font_size": FONT_SIZE,
                "font_color": self.FONT_COLOR_GREY,
                "num_format": self.DATE_FORMAT_MS,
            }
        )
        self.format_timestamp_string = self.workbook.add_format(
            {"font_size": FONT_SIZE, "font_color": self.FONT_COLOR_GREY, "align": "right"}
        )

    def _get_output_filename(self) -> str:
        filepath = self.DEFAULT_FILENAME + "." + self.FILE_EXTENSION

        if not os.path.exists(filepath):
            return filepath

        filepath, file_extension = os.path.splitext(filepath)
        i = 2
        new_fname = f"{filepath}-{i}{file_extension}"
        while os.path.exists(new_fname):
            i += 1
            new_fname = f"{filepath}-{i}{file_extension}"

        return new_fname

    def write_excel(self) -> None:
        with ProgressSpinner(f"{Fore.CYAN}generating EXCEL audit log{Fore.GREEN}: "):
            for asset in sorted(self.audit_log):
                worksheet = Worksheet(self, asset)
                for i, audit_log_entry in enumerate(self.audit_log[asset]):
                    worksheet.add_row(asset, audit_log_entry, i + 1)

                worksheet.make_table(len(self.audit_log[asset]), asset)
                worksheet.autofit()

            self.workbook.close()

        print(f"{Fore.WHITE}EXCEL audit log created: {Fore.YELLOW}{os.path.abspath(self.filename)}")


class Worksheet:
    SHEETNAME_MAX_LEN = 31
    MAX_COL_WIDTH = 30

    sheet_names: Dict[str, int] = {}
    table_names: Dict[str, int] = {}

    def __init__(self, output: AuditLogExcel, asset: AssetSymbol) -> None:
        self.output = output
        self.worksheet = output.workbook.add_worksheet(self._sheet_name(asset))
        self.col_width: Dict[int, int] = {}
        self.columns = self._make_columns(asset)
        self.worksheet.freeze_panes(1, 0)

    def _make_columns(self, asset: AssetSymbol) -> List[Column]:
        columns = []

        for col_num, col_name in enumerate(self.output.AUDIT_HEADER):
            col_name = col_name.replace("{{asset}}", asset)
            columns.append(Column({"header": col_name, "header_format": self.output.format_header}))
            self._autofit_calc(col_num, len(col_name))

        return columns

    def add_row(self, asset: AssetSymbol, audit_log_entry: AuditLogEntry, row_num: int) -> None:
        self._xl_text_black(asset, row_num, 0)
        self._xl_text_black(audit_log_entry.wallet, row_num, 1)
        self._xl_balance(audit_log_entry.balance, row_num, 2)
        self._xl_change(audit_log_entry.change, row_num, 3)
        self._xl_change(audit_log_entry.fee, row_num, 4)
        self._xl_balance(audit_log_entry.total, row_num, 5)

        link_name = self._make_linkname(audit_log_entry.t_record.t_type, audit_log_entry.tr_part)
        if audit_log_entry.t_record.t_row.filename:
            if not audit_log_entry.t_record.t_row.worksheet_name:
                # For a CSV file the worksheet name will be the same as the filename
                sheet_name = self._sheet_name_validate(
                    Path(audit_log_entry.t_record.t_row.filename).stem
                )
            else:
                sheet_name = audit_log_entry.t_record.t_row.worksheet_name
            self._xl_hyperlink(audit_log_entry.t_record.t_row, sheet_name, link_name, row_num, 6)
        else:
            self._xl_text_grey(link_name, row_num, 6)

        self._xl_timestamp(audit_log_entry.t_record.timestamp, row_num, 7)
        self._xl_text_grey(audit_log_entry.t_record.note, row_num, 8)
        if audit_log_entry.t_record.t_row.tx_raw:
            self._xl_text_grey(audit_log_entry.t_record.t_row.tx_raw.tx_hash, row_num, 9)
            self._xl_text_grey(audit_log_entry.t_record.t_row.tx_raw.tx_src, row_num, 10)
            self._xl_text_grey(audit_log_entry.t_record.t_row.tx_raw.tx_dest, row_num, 11)

    def _xl_balance(self, balance: Decimal, row_num: int, col_num: int) -> None:
        if len(balance.normalize().as_tuple().digits) > EXCEL_PRECISION:
            if balance < 0:
                wb_format = self.output.format_num_string_unsigned_red
            else:
                wb_format = self.output.format_num_string_unsigned

            self.worksheet.write_string(row_num, col_num, f"{balance.normalize():0,f}", wb_format)
        else:
            if balance < 0:
                wb_format = self.output.format_num_float_unsigned_red
            else:
                wb_format = self.output.format_num_float_unsigned

            self.worksheet.write_number(row_num, col_num, balance.normalize(), wb_format)
            cell = xl_rowcol_to_cell(row_num, col_num)

            if not config.large_data:
                # Lots of conditional formatting can slow down Excel
                self.worksheet.conditional_format(
                    row_num,
                    col_num,
                    row_num,
                    col_num,
                    {
                        "type": "formula",
                        "criteria": f"=INT({cell})={cell}",
                        "format": self.output.format_num_int_unsigned,
                    },
                )

        self._autofit_calc(col_num, len(f"{balance.normalize():0,f}"))

    def _xl_change(self, change: Optional[Decimal], row_num: int, col_num: int) -> None:
        if change is not None:
            if len(change.normalize().as_tuple().digits) > EXCEL_PRECISION:
                if change > 0:
                    change_str = f"+{change.normalize():0,f}"
                else:
                    change_str = f"{change.normalize():0,f}"

                self.worksheet.write_string(
                    row_num,
                    col_num,
                    change_str,
                    self.output.format_num_string_signed,
                )
            else:
                self.worksheet.write_number(
                    row_num, col_num, change.normalize(), self.output.format_num_float_signed
                )
                cell = xl_rowcol_to_cell(row_num, col_num)

                if not config.large_data:
                    # Lots of conditional formatting can slow down Excel
                    self.worksheet.conditional_format(
                        row_num,
                        col_num,
                        row_num,
                        col_num,
                        {
                            "type": "formula",
                            "criteria": f"=INT({cell})={cell}",
                            "format": self.output.format_num_int_signed,
                        },
                    )

            self._autofit_calc(col_num, len(f"{change.normalize():0,f}"))

    def _xl_text_black(self, text: str, row_num: int, col_num: int) -> None:
        self.worksheet.write_string(row_num, col_num, text)
        self._autofit_calc(col_num, len(text) if text else self.MAX_COL_WIDTH)

    def _xl_text_grey(self, text: str, row_num: int, col_num: int) -> None:
        self.worksheet.write_string(row_num, col_num, text, self.output.format_text_grey)
        self._autofit_calc(col_num, len(text) if text else self.MAX_COL_WIDTH)

    def _xl_timestamp(self, timestamp: datetime, row_num: int, col_num: int) -> None:
        utc_timestamp = timestamp.astimezone(TZ_UTC)
        utc_timestamp = timestamp.replace(tzinfo=None)

        if timestamp.microsecond % 1000:
            # Excel datetime can only display milliseconds
            self.worksheet.write_string(
                row_num,
                col_num,
                f"{utc_timestamp:{self.output.STR_FORMAT_MS}}",
                self.output.format_timestamp_string,
            )
            self._autofit_calc(col_num, len(f"{utc_timestamp:{self.output.STR_FORMAT_MS}}"))
        elif timestamp.microsecond:
            self.worksheet.write_datetime(
                row_num, col_num, utc_timestamp, self.output.format_timestamp_ms
            )
            self._autofit_calc(col_num, len(self.output.DATE_FORMAT_MS))
        else:
            self.worksheet.write_datetime(
                row_num, col_num, utc_timestamp, self.output.format_timestamp
            )
            self._autofit_calc(col_num, len(self.output.DATE_FORMAT))

    def _xl_hyperlink(
        self,
        t_row: TransactionRow,
        sheet_name: str,
        link_name: str,
        row_num: int,
        col_num: int,
    ) -> None:
        hyperlink = (
            f"=HYPERLINK(\"[{t_row.filename}]'{sheet_name}'"
            f'!A{t_row.row_num}:M{t_row.row_num}","{link_name}")'
        )
        self.worksheet.write_formula(row_num, col_num, hyperlink, self.output.format_text_grey)
        self._autofit_calc(col_num, len(link_name))

    def _make_hyperlink(self, filename: str, sheet_name: str, row_num: int, name: str) -> str:
        return f'=HYPERLINK("[{filename}]\'{sheet_name}\'!A{row_num}:M{row_num}","{name}")'

    def _make_linkname(self, t_type: TrType, tr_part: TrRecordPart) -> str:
        if t_type is TrType.TRADE:
            return f"{t_type.value} ({tr_part.value})"
        if t_type in BUY_TYPES and tr_part is not TrRecordPart.BUY:
            return f"{t_type.value} ({tr_part.value})"
        if t_type in SELL_TYPES and tr_part is not TrRecordPart.SELL:
            return f"{t_type.value} ({tr_part.value})"
        return f"{t_type.value}"

    def _autofit_calc(self, col_num: int, width: int) -> None:
        width = min(width, self.MAX_COL_WIDTH)

        if col_num in self.col_width:
            if width > self.col_width[col_num]:
                self.col_width[col_num] = width
        else:
            self.col_width[col_num] = width

    def autofit(self) -> None:
        for col_num, col_width in self.col_width.items():
            self.worksheet.set_column(col_num, col_num, col_width + 3)

    def make_table(self, rows: int, table_name: str) -> None:
        self.worksheet.add_table(
            0,
            0,
            rows,
            len(self.columns) - 1,
            {
                "autofilter": True,
                "style": "Table Style Medium 14",
                "columns": self.columns,
                "name": self._table_name(table_name),
                # "total_row": True,
            },
        )

    def _sheet_name(self, name: str) -> str:
        name = self._sheet_name_validate(name)

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

    def _sheet_name_validate(self, name: str) -> str:
        # Remove special characters
        name = re.sub(r"[/\\\?\*\[\]:]", "", name)
        name = name[: self.SHEETNAME_MAX_LEN] if len(name) > self.SHEETNAME_MAX_LEN else name

        return name

    def _table_name(self, name: str) -> str:
        # Remove characters which are not allowed
        name = name.replace(" ", "_")
        name = re.sub(r"[^a-zA-Z0-9\._]", "", name)

        # Add backslash to prevent xlsxwriter warnings
        name = f"\\{name}"

        if name.lower() not in self.table_names:
            self.table_names[name.lower()] = 1
        else:
            self.table_names[name.lower()] += 1
            name += str(self.table_names[name.lower()])

        return name
