# w -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

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
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow


def parse_cointracker(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    # Remove any blank lines and footer comment first
    for i in range(len(data_rows) - 1, -1, -1):
        if not data_rows[i].row or data_rows[i].row[0] == "...":
            del data_rows[i]

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
            _parse_cointracker_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_cointracker_row(
    data_rows: List["DataRow"], parser: DataParser, data_row: "DataRow", row_index: int
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])
    data_row.parsed = True

    if row_dict["Fee Amount"]:
        fee_quantity = Decimal(row_dict["Fee Amount"])
    else:
        fee_quantity = None

    if row_dict["Type"] in ("Buy", "Sell", "Trade"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Received Quantity"]),
            buy_asset=row_dict["Received Currency"],
            sell_quantity=Decimal(row_dict["Sent Quantity"]),
            sell_asset=row_dict["Sent Currency"],
            fee_quantity=fee_quantity,
            fee_asset=row_dict["Fee Currency"],
            wallet=_wallet_name(row_dict["Received Wallet"]),
            note=row_dict["Received Comment"],
        )
    elif row_dict["Type"] == "Receive":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Received Quantity"]),
            buy_asset=row_dict["Received Currency"],
            fee_quantity=fee_quantity,
            fee_asset=row_dict["Fee Currency"],
            wallet=_wallet_name(row_dict["Received Wallet"]),
            note=row_dict["Received Comment"],
        )
    elif row_dict["Type"] == "Send":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Sent Quantity"]),
            sell_asset=row_dict["Sent Currency"],
            fee_quantity=fee_quantity,
            fee_asset=row_dict["Fee Currency"],
            wallet=_wallet_name(row_dict["Sent Wallet"]),
            note=row_dict["Sent Comment"],
        )
    elif row_dict["Type"] == "Transfer":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Sent Quantity"]),
            sell_asset=row_dict["Sent Currency"],
            fee_quantity=fee_quantity,
            fee_asset=row_dict["Fee Currency"],
            wallet=_wallet_name(row_dict["Sent Wallet"]),
            note=row_dict["Sent Comment"],
        )
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []
        dup_data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Received Quantity"]),
            buy_asset=row_dict["Received Currency"],
            fee_quantity=fee_quantity,
            fee_asset=row_dict["Fee Currency"],
            wallet=_wallet_name(row_dict["Received Wallet"]),
            note=row_dict["Received Comment"],
        )
        data_rows.insert(row_index + 1, dup_data_row)
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _wallet_name(wallet: str) -> str:
    return wallet.split(" - ")[0]


DataParser(
    ParserType.ACCOUNTING,
    "CoinTracker",
    [
        "Date",
        "Type",
        "Transaction ID",
        "Received Quantity",
        "Received Currency",
        lambda c: re.match(r"Received Cost Basis \((\w{3})\)?", c),
        "Received Wallet",
        "Received Address",
        "Received Tag",
        "Received Comment",
        "Sent Quantity",
        "Sent Currency",
        lambda c: re.match(r"Sent Cost Basis \((\w{3})\)?", c),
        "Sent Wallet",
        "Sent Address",
        "Sent Tag",
        "Sent Comment",
        "Fee Amount",
        "Fee Currency",
        lambda c: re.match(r"Realized Return \((\w{3})\)?", c),
        "Ignored",
    ],
    worksheet_name="CoinTracker",
    all_handler=parse_cointracker,
)
