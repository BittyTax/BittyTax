# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2025

import copy
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, List

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import DataRowError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Changelly"


def parse_changelly(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    for row_index, data_row in enumerate(data_rows):
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f"row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if data_row.parsed:
            continue

        try:
            _parse_changelly_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_changelly_row(
    data_rows: List["DataRow"], parser: DataParser, data_row: "DataRow", row_index: int
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"], tz=config.local_timezone)
    data_row.tx_raw = TxRawPos(tx_dest_pos=parser.in_header.index("Receiver"))
    data_row.parsed = True

    data_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Exchange amount"]),
        buy_asset=row_dict["Currency from"].upper(),
        wallet=WALLET,
    )

    dup_data_row = copy.copy(data_row)
    dup_data_row.row = []
    dup_data_row.t_record = TransactionOutRecord(
        TrType.TRADE,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount received"]) + Decimal(row_dict["Total fee"]),
        buy_asset=row_dict["Currency to"].upper(),
        sell_quantity=Decimal(row_dict["Exchange amount"]),
        sell_asset=row_dict["Currency from"].upper(),
        fee_quantity=Decimal(row_dict["Total fee"]),
        fee_asset=row_dict["Currency to"].upper(),
        wallet=WALLET,
    )
    data_rows.insert(row_index + 1, dup_data_row)

    dup_data_row = copy.copy(data_row)
    dup_data_row.row = []
    dup_data_row.t_record = TransactionOutRecord(
        TrType.WITHDRAWAL,
        data_row.timestamp,
        sell_quantity=Decimal(row_dict["Amount received"]),
        sell_asset=row_dict["Currency to"].upper(),
        wallet=WALLET,
    )
    data_rows.insert(row_index + 2, dup_data_row)


DataParser(
    ParserType.EXCHANGE,
    "Changelly",
    [
        "Currency from",
        "Currency to",
        "Status",
        "Date",
        "Exchange amount",
        "Total fee",
        "Exchange rate",
        "Receiver",
        "Amount received",
    ],
    worksheet_name="Changelly",
    all_handler=parse_changelly,
)
