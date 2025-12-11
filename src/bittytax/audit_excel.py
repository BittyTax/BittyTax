# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import os
import platform
import re
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

import xlsxwriter
from colorama import Fore

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
        self.format_text_grey_link = self.workbook.add_format(
            {"font_size": FONT_SIZE, "font_color": self.FONT_COLOR_GREY, "underline": True}
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
                for audit_log_entry in self.audit_log[asset]:
                    worksheet.add_row(asset, audit_log_entry)

                worksheet.make_table(asset)
                if not config.large_data:
                    # Lots of conditional formatting can slow down Excel
                    worksheet.conditional_formatting()
                worksheet.worksheet.autofit()
                worksheet.worksheet.set_column(
                    self.AUDIT_HEADER.index("Timestamp"), self.AUDIT_HEADER.index("Timestamp"), 23
                )

            self.workbook.close()

        sys.stdout.write(
            f"{Fore.WHITE}EXCEL audit log created: "
            f"{Fore.YELLOW}{os.path.abspath(self.filename)}\n"
        )


class Worksheet:
    SHEETNAME_MAX_LEN = 31
    MAX_COL_WIDTH = 30

    sheet_names: Dict[str, int] = {}
    table_names: Dict[str, int] = {}

    def __init__(self, output: AuditLogExcel, asset: AssetSymbol) -> None:
        self.output = output
        self.worksheet = output.workbook.add_worksheet(self._sheet_name(asset))
        self.col_width: Dict[int, int] = {}
        self.row_num = 1
        self.worksheet.freeze_panes(1, 0)

    def add_row(self, asset: AssetSymbol, audit_log_entry: AuditLogEntry) -> None:
        self._xl_text_black(asset, self.row_num, 0)
        self._xl_text_black(audit_log_entry.wallet, self.row_num, 1)
        self._xl_balance(audit_log_entry.balance, self.row_num, 2)
        self._xl_change(audit_log_entry.change, self.row_num, 3)
        self._xl_change(audit_log_entry.fee, self.row_num, 4)
        self._xl_balance(audit_log_entry.total, self.row_num, 5)

        link_name = self._make_linkname(audit_log_entry.t_record.t_type, audit_log_entry.tr_part)
        if audit_log_entry.t_record.t_row.filename:
            if not audit_log_entry.t_record.t_row.worksheet_name:
                # For a CSV file the worksheet name will be the same as the filename
                sheet_name = self._sheet_name_validate(
                    Path(audit_log_entry.t_record.t_row.filename).stem
                )
            else:
                sheet_name = audit_log_entry.t_record.t_row.worksheet_name
            self._xl_hyperlink(
                audit_log_entry.t_record.t_row, sheet_name, link_name, self.row_num, 6
            )
        else:
            self._xl_text_grey(link_name, self.row_num, 6)

        self._xl_timestamp(audit_log_entry.t_record.timestamp, self.row_num, 7)
        self._xl_text_grey(audit_log_entry.t_record.note, self.row_num, 8)
        if audit_log_entry.t_record.t_row.tx_raw:
            self._xl_text_grey(audit_log_entry.t_record.t_row.tx_raw.tx_hash, self.row_num, 9)
            self._xl_text_grey(audit_log_entry.t_record.t_row.tx_raw.tx_src, self.row_num, 10)
            self._xl_text_grey(audit_log_entry.t_record.t_row.tx_raw.tx_dest, self.row_num, 11)

        self.row_num += 1

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

    def _xl_text_black(self, text: str, row_num: int, col_num: int) -> None:
        self.worksheet.write_string(row_num, col_num, text)

    def _xl_text_grey(self, text: str, row_num: int, col_num: int) -> None:
        self.worksheet.write_string(row_num, col_num, text, self.output.format_text_grey)

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
        elif timestamp.microsecond:
            self.worksheet.write_datetime(
                row_num, col_num, utc_timestamp, self.output.format_timestamp_ms
            )
        else:
            self.worksheet.write_datetime(
                row_num, col_num, utc_timestamp, self.output.format_timestamp
            )

    def _xl_hyperlink(
        self,
        t_row: TransactionRow,
        sheet_name: str,
        link_name: str,
        row_num: int,
        col_num: int,
    ) -> None:
        self.worksheet.write_url(
            row_num,
            col_num,
            f"external:{t_row.filename}#'{sheet_name}'!A{t_row.row_num}:M{t_row.row_num}",
            self.output.format_text_grey_link,
            string=link_name,
        )

    def _make_linkname(self, t_type: TrType, tr_part: TrRecordPart) -> str:
        if t_type is TrType.TRADE:
            return f"{t_type.value} ({tr_part.value})"
        if t_type in BUY_TYPES and tr_part is not TrRecordPart.BUY:
            return f"{t_type.value} ({tr_part.value})"
        if t_type in SELL_TYPES and tr_part is not TrRecordPart.SELL:
            return f"{t_type.value} ({tr_part.value})"
        return f"{t_type.value}"

    def conditional_formatting(self) -> None:
        self._format_integer(1, 2, self.output.format_num_int_unsigned)
        self._format_integer(1, 3, self.output.format_num_int_signed)
        self._format_integer(1, 4, self.output.format_num_int_signed)
        self._format_integer(1, 5, self.output.format_num_int_unsigned)

    def _format_integer(
        self, row_num: int, col_num: int, ws_format: xlsxwriter.worksheet.Format
    ) -> None:
        cell = xlsxwriter.utility.xl_rowcol_to_cell(row_num, col_num, col_abs=True)
        self.worksheet.conditional_format(
            row_num,
            col_num,
            self.row_num - 1,
            col_num,
            {
                "type": "formula",
                "criteria": f"=INT({cell})={cell}",
                "format": ws_format,
            },
        )

    def make_table(self, asset: AssetSymbol) -> None:
        self.worksheet.add_table(
            0,
            0,
            self.row_num - 1,
            len(self.output.AUDIT_HEADER) - 1,
            {
                "autofilter": True,
                "style": "Table Style Medium 14",
                "columns": self._get_columns(asset),
                "name": self._table_name(asset),
            },
        )

    def _get_columns(self, asset: AssetSymbol) -> List[Dict[str, str]]:
        return [
            {
                "header": header.replace("{{asset}}", asset),
                "header_format": self.output.format_header,
            }
            for header in self.output.AUDIT_HEADER
        ]

    def _sheet_name(self, name: str) -> str:
        name = self._sheet_name_validate(name)
        base_name = name

        if name.lower() not in self.sheet_names:
            self.sheet_names[name.lower()] = 1
            sheet_name = name
        else:
            # Find next available counter
            counter = self.sheet_names[base_name.lower()] + 1
            sheet_name = f"{base_name}({counter})"

            # Truncate base name if combined name is too long
            if len(sheet_name) > self.SHEETNAME_MAX_LEN:
                max_base_len = self.SHEETNAME_MAX_LEN - len(f"({counter})")
                sheet_name = f"{base_name[:max_base_len]}({counter})"

            # Ensure the generated name is unique
            while sheet_name.lower() in self.sheet_names:
                counter += 1
                sheet_name = f"{base_name}({counter})"
                if len(sheet_name) > self.SHEETNAME_MAX_LEN:
                    max_base_len = self.SHEETNAME_MAX_LEN - len(f"({counter})")
                    sheet_name = f"{base_name[:max_base_len]}({counter})"

            self.sheet_names[base_name.lower()] = counter
            # Also register the actual generated name to prevent collisions
            self.sheet_names[sheet_name.lower()] = 1

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
