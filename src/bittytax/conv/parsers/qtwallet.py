# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, List, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ...constants import WARNING
from ..dataparser import ConsolidateType, DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError, UnknownCryptoassetError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Qt Wallet"


def parse_qt_wallet(
    data_rows: List["DataRow"], parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    if parser.args:
        amount_hdr = parser.args[0].group(1)
    else:
        amount_hdr = "Amount"

    if parser.args and parser.args[0].group(2):
        # Symbol in header
        symbol = parser.args[0].group(2)
    elif kwargs["cryptoasset"]:
        # Symbol from argument
        symbol = kwargs["cryptoasset"]
    else:
        symbol = ""

    unconfirmed_include = bool(kwargs["unconfirmed"])

    for data_row in data_rows:
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
            symbol, unconfirmed_include = _parse_qt_wallet_row(
                data_row, parser, amount_hdr, symbol, unconfirmed_include, **kwargs
            )
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_qt_wallet_row(
    data_row: "DataRow",
    parser: DataParser,
    amount_hdr: str,
    symbol: str,
    unconfirmed_include: bool,
    **kwargs: Unpack[ParserArgs],
) -> Tuple[str, bool]:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"], tz=config.local_timezone)

    amount, amount_symbol = _get_amount(row_dict[amount_hdr])

    if amount_symbol:
        # Amount has symbol
        symbol = amount_symbol
    elif not symbol:
        sys.stderr.write(f"{WARNING} Cryptoasset cannot be identified\n")
        sys.stderr.write(f"{Fore.RESET}Enter symbol: ")
        symbol = input()
        if not symbol:
            raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet", ""))

    if row_dict["Confirmed"] == "false" and not unconfirmed_include:
        if parser.in_header_row_num is None:
            raise RuntimeError("Missing in_header_row_num")

        sys.stderr.write(
            f"{Fore.YELLOW}row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            f"{WARNING} This transaction is unconfirmed\n"
        )
        sys.stderr.write(f"{Fore.RESET}Include unconfirmed transactions? [y/N] ")
        unconfirmed_include = bool(input().lower() == "y")
        if not unconfirmed_include:
            return symbol, unconfirmed_include

    if row_dict["Type"] == "Received with":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=symbol,
            wallet=_get_wallet(symbol),
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Sent to":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=amount,
            sell_asset=symbol,
            wallet=_get_wallet(symbol),
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Mined":
        data_row.t_record = TransactionOutRecord(
            TrType.MINING,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=symbol,
            wallet=_get_wallet(symbol),
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Masternode Reward":
        data_row.t_record = TransactionOutRecord(
            TrType.STAKING,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=symbol,
            wallet=_get_wallet(symbol),
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Payment to yourself":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(0),
            sell_asset=symbol,
            fee_quantity=amount,
            fee_asset=symbol,
            wallet=_get_wallet(symbol),
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Name operation":
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=amount,
            sell_asset=symbol,
            wallet=_get_wallet(symbol),
            note=row_dict["Label"],
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])

    return symbol, unconfirmed_include


def _get_amount(amount: str) -> Tuple[Decimal, str]:
    match = re.match(r"^(-?\d+\.\d+) (\w{3,4})$", amount)

    if match:
        amount = match.group(1)
        symbol = match.group(2)
        return abs(Decimal(amount)), symbol
    return abs(Decimal(amount)), ""


def _get_wallet(symbol: str) -> str:
    return f"{WALLET} ({symbol})"


def parse_vericoin_qt_wallet(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date/Time"], tz=config.local_timezone)
    symbol = "VRC"

    if row_dict["Type"] == "Receive":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=symbol,
            wallet=_get_wallet(symbol),
        )
    elif row_dict["Type"] == "Send":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=symbol,
            wallet=_get_wallet(symbol),
        )
    elif row_dict["Type"] == "Stake":
        data_row.t_record = TransactionOutRecord(
            TrType.STAKING,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=symbol,
            wallet=_get_wallet(symbol),
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    ParserType.WALLET,
    "Qt Wallet (i.e. Bitcoin Core, etc)",
    [
        "Confirmed",
        "Date",
        "Type",
        "Label",
        "Address",
        lambda c: re.match(r"(Amount \((\w+)\)?)", c),
        "ID",
    ],
    worksheet_name="Qt Wallet",
    all_handler=parse_qt_wallet,
    consolidate_type=ConsolidateType.HEADER_MATCH,
)

DataParser(
    ParserType.WALLET,
    "Qt Wallet (i.e. Bitcoin Core, etc)",
    ["Confirmed", "Date", "Type", "Label", "Address", "Amount", "ID"],
    worksheet_name="Qt Wallet",
    all_handler=parse_qt_wallet,
)

DataParser(
    ParserType.WALLET,
    "Qt Wallet (i.e. Bitcoin Core, etc)",
    ["Transaction", "Block", "Date/Time", "Type", "Amount", "Total"],
    worksheet_name="Qt Wallet",
    row_handler=parse_vericoin_qt_wallet,
)
