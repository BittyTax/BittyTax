# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

import re
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...config import config
from ...types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import (
    DataRowError,
    MissingComponentError,
    UnexpectedContentError,
    UnexpectedTypeError,
)
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "CoinList"


def parse_coinlist(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"][:-4], tz="US/Eastern")
    amount = Decimal(row_dict["Amount"].replace(",", ""))

    if "Deposit" in row_dict["Description"]:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    elif "Withdrawal" in row_dict["Description"]:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(amount),
            sell_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    elif "Staking" in row_dict["Description"]:
        data_row.t_record = TransactionOutRecord(
            TrType.STAKING,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    elif "Distribution" in row_dict["Description"]:
        data_row.t_record = TransactionOutRecord(
            TrType.AIRDROP,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    elif "Sold" in row_dict["Description"]:
        buy_quantity, buy_asset = _get_buy_quantity(row_dict["Description"])
        if buy_quantity is None:
            raise UnexpectedContentError(
                parser.in_header.index("Description"),
                "Description",
                row_dict["Description"],
            )

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            sell_quantity=abs(amount),
            sell_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    elif "Transfer" in row_dict["Description"]:
        # Skip internal transfers
        return
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Description"),
            "Description",
            row_dict["Description"],
        )


def _get_buy_quantity(description: str) -> Tuple[Optional[Decimal], str]:
    match = re.match(r"^Sold ([\d|,]*\.\d+) (\w+) for (\$?[\d|,]*\.\d+) ?(\w+)?$", description)
    if match:
        if match.group(4):
            return Decimal(match.group(3)), match.group(4)
        return Decimal(match.group(3).strip("$")), "USD"
    return None, ""


def parse_coinlist_pro(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    tx_times: Dict[str, List["DataRow"]] = {}
    for dr in data_rows:
        if dr.row_dict["time"] in tx_times:
            tx_times[dr.row_dict["time"]].append(dr)
        else:
            tx_times[dr.row_dict["time"]] = [dr]

    for data_row in data_rows:
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f"row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        try:
            _parse_coinlist_pro_row(tx_times, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_coinlist_pro_row(
    tx_times: Dict[str, List["DataRow"]], parser: DataParser, data_row: "DataRow"
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])

    if row_dict["type"] in ("match", "fee"):
        buy, sell = _get_buy_sell(data_row, "match", tx_times[row_dict["time"]])
        fee = _get_fee(data_row, tx_times[row_dict["time"]])
        if buy is None or sell is None or fee is None:
            raise MissingComponentError(parser.in_header.index("time"), "time", row_dict["time"])

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(buy.row_dict["amount"]),
            buy_asset=buy.row_dict["balance"],
            sell_quantity=abs(Decimal(sell.row_dict["amount"])),
            sell_asset=sell.row_dict["balance"],
            fee_quantity=abs(Decimal(fee.row_dict["amount"])),
            fee_asset=fee.row_dict["balance"],
            wallet=WALLET,
        )
    elif row_dict["type"] == "admin":
        buy, sell = _get_buy_sell(data_row, "admin", tx_times[row_dict["time"]])
        if buy is None or sell is None:
            raise MissingComponentError(parser.in_header.index("time"), "time", row_dict["time"])

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(buy.row_dict["amount"]),
            buy_asset=buy.row_dict["balance"],
            sell_quantity=abs(Decimal(sell.row_dict["amount"])),
            sell_asset=sell.row_dict["balance"],
            wallet=WALLET,
        )
    elif row_dict["type"] in ("deposit", "withdrawal"):
        # Skip internal transfers
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def _get_buy_sell(
    data_row: "DataRow", tx_type: str, tx_times: List["DataRow"]
) -> Tuple[Optional["DataRow"], Optional["DataRow"]]:
    t_rows = [dr for dr in tx_times if dr.row_dict["type"] == tx_type]
    buys = [dr for dr in t_rows if Decimal(dr.row_dict["amount"]) > 0]
    sells = [dr for dr in t_rows if Decimal(dr.row_dict["amount"]) < 0]

    if len(buys) == 1 and len(sells) == 1:
        buys[0].timestamp = data_row.timestamp
        buys[0].parsed = True
        sells[0].timestamp = data_row.timestamp
        sells[0].parsed = True
        return buys[0], sells[0]
    return None, None


def _get_fee(data_row: "DataRow", tx_times: List["DataRow"]) -> Optional["DataRow"]:
    fees = [dr for dr in tx_times if dr.row_dict["type"] == "fee"]

    if len(fees) == 1:
        fees[0].timestamp = data_row.timestamp
        fees[0].parsed = True
        return fees[0]
    return None


DataParser(
    ParserType.EXCHANGE,
    "CoinList",
    ["Date", "Description", "Asset", "Amount", "Balance"],
    worksheet_name="CoinList",
    row_handler=parse_coinlist,
)

DataParser(
    ParserType.EXCHANGE,
    "CoinList Pro",
    [
        "portfolio",
        "type",
        "time",
        "amount",
        "balance",
        "amount/balance unit",
        "transaction_id",
    ],
    worksheet_name="CoinList Pro",
    all_handler=parse_coinlist_pro,
)
