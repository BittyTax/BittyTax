# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ...constants import WARNING
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError, UnknownCryptoassetError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Qt Wallet"


def parse_qt_wallet(data_row: "DataRow", parser: DataParser, **kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"], tz=config.local_timezone)

    amount, symbol = _get_amount(data_row.row[5])

    if parser.args and parser.args[0].group(1):
        symbol = parser.args[0].group(1)
    elif not symbol:
        if kwargs["cryptoasset"]:
            symbol = kwargs["cryptoasset"]
        else:
            raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet", ""))

    if row_dict["Confirmed"] == "false" and not kwargs["unconfirmed"]:
        if parser.in_header_row_num is None:
            raise RuntimeError("Missing in_header_row_num")

        sys.stderr.write(
            f"{Fore.YELLOW}row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            f"{WARNING} Skipping unconfirmed transaction, use the [-uc] option to include it\n"
        )
        return

    if row_dict["Type"] == "Received with":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=symbol,
            wallet=WALLET,
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Sent to":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=amount,
            sell_asset=symbol,
            wallet=WALLET,
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Mined":
        data_row.t_record = TransactionOutRecord(
            TrType.MINING,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=symbol,
            wallet=WALLET,
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Masternode Reward":
        data_row.t_record = TransactionOutRecord(
            TrType.STAKING,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=symbol,
            wallet=WALLET,
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
            wallet=WALLET,
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Name operation":
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=amount,
            sell_asset=symbol,
            wallet=WALLET,
            note=row_dict["Label"],
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _get_amount(amount: str) -> Tuple[Decimal, str]:
    match = re.match(r"^(-?\d+\.\d+) (\w{3,4})$", amount)

    if match:
        amount = match.group(1)
        symbol = match.group(2)
        return abs(Decimal(amount)), symbol
    return abs(Decimal(amount)), ""


def parse_vericoin_qt_wallet(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date/Time"], tz=config.local_timezone)

    if row_dict["Type"] == "Receive":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset="VRC",
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Send":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset="VRC",
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Stake":
        data_row.t_record = TransactionOutRecord(
            TrType.STAKING,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset="VRC",
            wallet=WALLET,
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
        lambda c: re.match(r"Amount \((\w+)\)?", c),
        "ID",
    ],
    worksheet_name="Qt Wallet",
    row_handler=parse_qt_wallet,
)

DataParser(
    ParserType.WALLET,
    "Qt Wallet (i.e. Bitcoin Core, etc)",
    ["Confirmed", "Date", "Type", "Label", "Address", "Amount", "ID"],
    worksheet_name="Qt Wallet",
    row_handler=parse_qt_wallet,
)

DataParser(
    ParserType.WALLET,
    "Qt Wallet (i.e. Bitcoin Core, etc)",
    ["Transaction", "Block", "Date/Time", "Type", "Amount", "Total"],
    worksheet_name="Qt Wallet",
    row_handler=parse_vericoin_qt_wallet,
)
