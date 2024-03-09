# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedContentError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "SwissBorg"


def parse_swissborg(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    tx_times: Dict[str, List["DataRow"]] = {}

    for dr in data_rows:
        if dr.row_dict["Time in UTC"] in tx_times:
            tx_times[dr.row_dict["Time in UTC"]].append(dr)
        else:
            tx_times[dr.row_dict["Time in UTC"]] = [dr]

    for data_row in data_rows:
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
            _parse_swissborg_row(tx_times, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_swissborg_row(
    tx_times: Dict[str, List["DataRow"]], parser: DataParser, data_row: "DataRow"
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time in UTC"])

    if row_dict["Type"] == "Deposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Gross amount"]),
            buy_asset=row_dict["Currency"],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Currency"],
            fee_value=Decimal(row_dict["Fee (GBP)"]) if row_dict["Currency"] != "GBP" else None,
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Net amount"]),
            sell_asset=row_dict["Currency"],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Currency"],
            fee_value=Decimal(row_dict["Fee (GBP)"]) if row_dict["Currency"] != "GBP" else None,
            wallet=WALLET,
        )
    elif row_dict["Type"] in ("Sell", "Buy"):
        _make_trade(tx_times[row_dict["Time in UTC"]], data_row, parser)
    elif row_dict["Type"] == "Payouts":
        if row_dict["Note"] == "Yield payouts":
            t_type = TrType.STAKING
        else:
            t_type = TrType.AIRDROP

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Gross amount"]),
            buy_asset=row_dict["Currency"],
            buy_value=(
                Decimal(row_dict["Gross amount (GBP)"]) if row_dict["Currency"] != "GBP" else None
            ),
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Currency"],
            fee_value=Decimal(row_dict["Fee (GBP)"]) if row_dict["Currency"] != "GBP" else None,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _make_trade(tx_times: List["DataRow"], data_row: "DataRow", parser: DataParser) -> None:
    buy_rows = [dr for dr in tx_times if dr.row_dict["Type"] == "Buy"]
    sell_rows = [dr for dr in tx_times if dr.row_dict["Type"] == "Sell"]

    if len(buy_rows) == 1 and len(sell_rows) == 1:
        if data_row == buy_rows[0]:
            sell_rows[0].timestamp = data_row.timestamp
            sell_rows[0].parsed = True
        else:
            buy_rows[0].timestamp = data_row.timestamp
            buy_rows[0].parsed = True

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(buy_rows[0].row_dict["Gross amount"]),
            buy_asset=buy_rows[0].row_dict["Currency"],
            buy_value=(
                Decimal(buy_rows[0].row_dict["Gross amount (GBP)"])
                if buy_rows[0].row_dict["Currency"] != "GBP"
                else None
            ),
            sell_quantity=Decimal(sell_rows[0].row_dict["Gross amount"]),
            sell_asset=sell_rows[0].row_dict["Currency"],
            sell_value=(
                Decimal(sell_rows[0].row_dict["Gross amount (GBP)"])
                if sell_rows[0].row_dict["Currency"] != "GBP"
                else None
            ),
            fee_quantity=Decimal(buy_rows[0].row_dict["Fee"]),
            fee_asset=buy_rows[0].row_dict["Currency"],
            fee_value=(
                Decimal(buy_rows[0].row_dict["Fee (GBP)"])
                if buy_rows[0].row_dict["Currency"] != "GBP"
                else None
            ),
            wallet=WALLET,
        )
    else:
        data_row.failure = UnexpectedContentError(
            parser.in_header.index("Type"), "Type", data_row.row_dict["Type"]
        )


DataParser(
    ParserType.EXCHANGE,
    "SwissBorg",
    [
        "Local time",
        "Time in UTC",
        "Type",
        "Currency",
        "Gross amount",
        "Gross amount (GBP)",
        "Fee",
        "Fee (GBP)",
        "Net amount",
        "Net amount (GBP)",
        "Note",
    ],
    worksheet_name="SwissBorg",
    all_handler=parse_swissborg,
)
