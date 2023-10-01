# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

import sys
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...config import config
from ...types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, MissingComponentError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Coinmetro"


def parse_coinmetro(
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
            _parse_coinmetro_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_coinmetro_row(
    data_rows: List["DataRow"], parser: DataParser, data_row: "DataRow", row_index: int
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])
    data_row.parsed = True

    if "Deposit" in row_dict["Description"]:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]) + Decimal(row_dict["Fee"]),
            buy_asset=row_dict["Asset"],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    elif "Withdrawal" in row_dict["Description"]:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=row_dict["Asset"],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    elif "Order" in row_dict["Description"]:
        if Decimal(row_dict["Amount"]) > 0:
            sell_quantity, sell_asset = _get_sell(data_rows, row_index, row_dict["Description"])

            if sell_quantity is None:
                raise MissingComponentError(
                    parser.in_header.index("Description"),
                    "Description",
                    row_dict["Description"],
                )

            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount"]),
                buy_asset=row_dict["Asset"],
                sell_quantity=sell_quantity,
                sell_asset=sell_asset,
                fee_quantity=Decimal(row_dict["Fee"]),
                fee_asset=row_dict["Asset"],
                wallet=WALLET,
            )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Description"),
            "Description",
            row_dict["Description"],
        )


def _get_sell(
    data_rows: List["DataRow"], row_index: int, order_id: str
) -> Tuple[Optional[Decimal], str]:
    data_row = data_rows[row_index + 1]
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])
    data_row.parsed = True

    if row_dict["Description"] == order_id:
        return abs(Decimal(row_dict["Amount"])), row_dict["Asset"]
    return None, ""


DataParser(
    ParserType.EXCHANGE,
    "Coinmetro",
    [
        "Asset",
        "Date",
        "Description",
        "Amount",
        "Fee",
        "Price",
        "Pair",
        "Other Currency",
        "Other Amount",
        "IBAN",
        "Transaction Hash",
        "Address",
        "Tram",
        "Additional Info",
        "Reference Note",
        "Comment",
    ],
    worksheet_name="Coinmetro",
    all_handler=parse_coinmetro,
)
