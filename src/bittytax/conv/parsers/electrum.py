# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal
from typing import TYPE_CHECKING

from colorama import Fore
from typing_extensions import List, Unpack

from ...bt_types import TrType
from ...config import config
from ...constants import WARNING
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnknownCryptoassetError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Electrum"


def parse_electrum_v3(
    data_rows: List["DataRow"], parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:

    symbol = kwargs["cryptoasset"]
    if not symbol:
        sys.stderr.write(f"{WARNING} Cryptoasset cannot be identified\n")
        sys.stderr.write(f"{Fore.RESET}Enter symbol: ")
        symbol = input()
        if not symbol:
            raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet", ""))

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
            _parse_electrum_row_v3(data_row, parser, symbol)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_electrum_row_v3(data_row: "DataRow", _parser: DataParser, symbol: str) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["timestamp"], tz=config.local_timezone)

    value = Decimal(row_dict["value"].replace(",", ""))
    if value > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=value,
            buy_asset=symbol,
            wallet=_get_wallet(symbol),
            note=row_dict["label"],
        )
    else:
        if row_dict["fee"]:
            sell_quantity = abs(value) - Decimal(row_dict["fee"])
            fee_quantity = Decimal(row_dict["fee"])
            fee_asset = symbol
        else:
            sell_quantity = abs(value)
            fee_quantity = None
            fee_asset = ""

        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=sell_quantity,
            sell_asset=symbol,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=_get_wallet(symbol),
            note=row_dict["label"],
        )


def _get_wallet(symbol: str) -> str:
    return f"{WALLET} ({symbol})"


def parse_electrum_v2(
    data_rows: List["DataRow"], parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    parse_electrum_v1(data_rows, parser, **kwargs)


def parse_electrum_v1(
    data_rows: List["DataRow"], parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:

    symbol = kwargs["cryptoasset"]
    if not symbol:
        sys.stderr.write(f"{WARNING} Cryptoasset cannot be identified\n")
        sys.stderr.write(f"{Fore.RESET}Enter symbol: ")
        symbol = input()
        if not symbol:
            raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet", ""))

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
            _parse_electrum_row_v1(data_row, parser, symbol)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_electrum_row_v1(data_row: "DataRow", _parser: DataParser, symbol: str) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["timestamp"], tz=config.local_timezone)

    value = Decimal(row_dict["value"].replace(",", ""))
    if value > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=value,
            buy_asset=symbol,
            wallet=_get_wallet(symbol),
            note=row_dict["label"],
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(value),
            sell_asset=symbol,
            wallet=_get_wallet(symbol),
            note=row_dict["label"],
        )


DataParser(
    ParserType.WALLET,
    "Electrum",
    [
        "transaction_hash",
        "label",
        "confirmations",
        "value",
        "fiat_value",
        "fee",
        "fiat_fee",
        "timestamp",
    ],
    worksheet_name="Electrum",
    all_handler=parse_electrum_v3,
)

DataParser(
    ParserType.WALLET,
    "Electrum",
    ["transaction_hash", "label", "value", "timestamp"],
    worksheet_name="Electrum",
    # Different handler name used to prevent data file consolidation
    all_handler=parse_electrum_v2,
)

DataParser(
    ParserType.WALLET,
    "Electrum",
    ["transaction_hash", "label", "confirmations", "value", "timestamp"],
    worksheet_name="Electrum",
    all_handler=parse_electrum_v1,
)
