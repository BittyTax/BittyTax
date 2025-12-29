# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2025

import copy
import re
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, List

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, MissingValueError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Jupiter"

PRECISION = Decimal("0.00")


def parse_jupiter_futures(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    for row_index, data_row in enumerate(data_rows):
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f" row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if data_row.parsed:
            continue

        try:
            _parse_jupiter_futures_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_jupiter_futures_row(
    data_rows: List["DataRow"], _parser: DataParser, data_row: "DataRow", row_index: int
) -> None:
    row_dict = data_row.row_dict

    if not row_dict["Date"]:
        # Delete empty rows
        del data_rows[row_index]
        return

    data_row.timestamp = DataParser.parse_timestamp(_get_timestamp(row_dict["Date"]), dayfirst=True)
    data_row.parsed = True

    if data_row.row[12] == "P&L":
        pnl = DataParser.convert_currency(data_row.row[13], "USD", data_row.timestamp)

        if pnl is None:
            raise MissingValueError(13, "P&L", data_row.row[13])
    else:
        return

    if data_row.row[14] == "P&L Less Fees":
        fee = DataParser.convert_currency(data_row.row[15], "USD", data_row.timestamp)

        if fee is None:
            raise MissingValueError(15, "P&L Less Fees", data_row.row[15])

        # Round the fee as the cell formula can sometimes give precision errors
        fee = (pnl - fee).quantize(PRECISION)
    else:
        return

    if pnl > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_GAIN,
            data_row.timestamp,
            buy_quantity=pnl,
            buy_asset=config.ccy,
            wallet=WALLET,
            note=row_dict["Position"],
        )
    elif pnl < 0:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_LOSS,
            data_row.timestamp,
            sell_quantity=abs(pnl),
            sell_asset=config.ccy,
            wallet=WALLET,
            note=row_dict["Position"],
        )
    elif fee > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=fee,
            sell_asset=config.ccy,
            wallet=WALLET,
            note=row_dict["Position"],
        )

    if pnl != 0 and fee != 0:
        # Insert extra row to contain the MARGIN_FEE in addition to a MARGIN_GAIN/LOSS
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []
        dup_data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=fee,
            sell_asset=config.ccy,
            wallet=WALLET,
            note=row_dict["Position"],
        )
        data_rows.insert(row_index + 1, dup_data_row)


def _get_timestamp(date: str) -> str:
    match = re.match(r"^(\d{1,2}:\d{2}) (\d{2}/\d{2}/\d{4}) \(([-+]\d{2})\)$", date)

    if match:
        time = match.group(1)
        date = match.group(2)
        utc_offset = match.group(3)
        return f"{time} {date} UTC{utc_offset}:00"
    return ""


DataParser(
    ParserType.EXCHANGE,
    "Jupiter Futures",
    [
        "",
        "Position",
        "Date",
        "Action",
        "Solana Entered/Returned",
        "Order Type",
        "Deposit/Withdraw",
        "Price",
        "Size",
        "PNL",
        "Fee",
        "Solana Gain/(Loss)",
        "",
        "",
        "",
        "",
    ],
    worksheet_name="Jupiter F",
    all_handler=parse_jupiter_futures,
)
