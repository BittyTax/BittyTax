# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Tuple, Optional

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ...constants import WARNING
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Celsius"


def parse_celsius(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    datetimes: Dict[str, List["DataRow"]] = {}
    for dr in data_rows:
        if dr.row_dict["Date and time"] in datetimes:
            datetimes[dr.row_dict["Date and time"]].append(dr)
        else:
            datetimes[dr.row_dict["Date and time"]] = [dr]

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
            parse_celsius_row(
                datetimes=datetimes,
                parser=parser,
                data_row=data_row,
                unconfirmed_arg=_kwargs["unconfirmed"],
            )
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def parse_celsius_row(
    datetimes: Dict[str, List["DataRow"]],
    parser: DataParser,
    data_row: "DataRow",
    unconfirmed_arg: bool,
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date and time"])

    if row_dict["Confirmed"] != "Yes" and unconfirmed_arg is False:
        if parser.in_header_row_num is None:
            raise RuntimeError("Missing in_header_row_num")

        sys.stderr.write(
            f"{Fore.YELLOW}row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            f"{WARNING} Skipping unconfirmed transaction, use the [-uc] option to include it\n"
        )
        return

    if row_dict["Transaction type"] in (
        "deposit",
        "Deposit",
        "inbound_transfer",
        "Inbound Transfer",
        "Transfer",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Coin amount"]),
            buy_asset=row_dict["Coin type"],
            wallet=WALLET,
        )
    elif row_dict["Transaction type"] in (
        "withdrawal",
        "Withdrawal",
        "outbound_transfer",
        "Outbound Transfer",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Coin amount"])),
            sell_asset=row_dict["Coin type"],
            wallet=WALLET,
        )
    elif row_dict["Transaction type"] in ("interest", "Interest", "reward", "Reward"):
        data_row.t_record = TransactionOutRecord(
            TrType.INTEREST,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Coin amount"]),
            buy_asset=row_dict["Coin type"],
            buy_value=DataParser.convert_currency(row_dict["USD Value"], "USD", data_row.timestamp),
            wallet=WALLET,
        )
    elif row_dict["Transaction type"] in (
        "promo_code_reward",
        "Promo Code Reward",
        "referred_award",
        "Referred Award",
        "referrer_award",
        "Referrer Award",
        "bonus_token",
        "Bonus Token",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.GIFT_RECEIVED,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Coin amount"]),
            buy_asset=row_dict["Coin type"],
            buy_value=DataParser.convert_currency(row_dict["USD Value"], "USD", data_row.timestamp),
            wallet=WALLET,
        )
    elif row_dict["Transaction type"] in (
        "Swap out",
        "Swap in",
    ):
        if row_dict["Transaction type"] == "Swap out":
            sell_quantity = abs(Decimal(row_dict["Coin amount"]))
            sell_asset = row_dict["Coin type"]
            sell_value = abs(Decimal(row_dict["USD Value"]))

            buy_quantity, buy_asset, buy_value = _get_swap(
                datetimes[row_dict["Date and time"]], "Swap in"
            )
        else:
            buy_quantity = Decimal(row_dict["Coin amount"])
            buy_asset = row_dict["Coin type"]
            buy_value = Decimal(row_dict["USD Value"])

            sell_quantity, sell_asset, sell_value = _get_swap(
                datetimes[row_dict["Date and time"]], "Swap out"
            )

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=DataParser.convert_currency(buy_value, "USD", data_row.timestamp),
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            sell_value=DataParser.convert_currency(sell_value, "USD", data_row.timestamp),
            wallet=WALLET,
        )
    # Skip transactions without a type.
    elif row_dict["Transaction type"] == "":
        return
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Transaction type"),
            "Transaction type",
            row_dict["Transaction type"],
        )


def _get_swap(
    swap_rows: List["DataRow"], t_type: str
) -> Tuple[Optional[Decimal], str, Optional[Decimal]]:
    for data_row in swap_rows:
        if not data_row.parsed and t_type == data_row.row_dict["Transaction type"]:
            data_row.timestamp = DataParser.parse_timestamp(data_row.row_dict["Date and time"])
            quantity: Optional[Decimal] = abs(Decimal(data_row.row_dict["Coin amount"]))
            asset = data_row.row_dict["Coin type"]
            value: Optional[Decimal] = abs(Decimal(data_row.row_dict["USD Value"]))
            data_row.parsed = True
            break

    return quantity, asset, value


DataParser(
    ParserType.SAVINGS,
    "Celsius",
    [
        "Internal id",
        "Date and time",
        "Transaction type",
        "Coin type",
        "Coin amount",
        "USD Value",
        "Original Reward Coin",
        "Reward Amount In Original Coin",
        "Confirmed",
    ],
    worksheet_name="Celsius",
    all_handler=parse_celsius,
)

DataParser(
    ParserType.SAVINGS,
    "Celsius",
    [
        "Internal id",
        "Date and time",
        "Transaction type",
        "Coin type",
        "Coin amount",
        "USD Value",
        "Original Interest Coin",
        "Interest Amount In Original Coin",
        "Confirmed",
    ],
    worksheet_name="Celsius",
    all_handler=parse_celsius,
)
