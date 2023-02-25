# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
import sys
from decimal import Decimal

from colorama import Back, Fore

from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError, UnknownCryptoassetError
from ..out_record import TransactionOutRecord

WALLET = "Qt Wallet"


def parse_qt_wallet(data_row, parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"], tz="Europe/London")

    amount, symbol = _get_amount(data_row.row[5])

    if not kwargs["cryptoasset"]:
        if parser.args[0].group(1):
            symbol = parser.args[0].group(1)
        elif not symbol:
            raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet"))
    else:
        symbol = kwargs["cryptoasset"]

    if row_dict["Confirmed"] == "false" and not kwargs["unconfirmed"]:
        sys.stderr.write(
            "%srow[%s] %s\n" % (Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row)
        )
        sys.stderr.write(
            "%sWARNING%s Skipping unconfirmed transaction, "
            "use the [-uc] option to include it\n"
            % (Back.YELLOW + Fore.BLACK, Back.RESET + Fore.YELLOW)
        )
        return

    if row_dict["Type"] == "Received with":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=symbol,
            wallet=WALLET,
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Sent to":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=amount,
            sell_asset=symbol,
            wallet=WALLET,
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Mined":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_MINING,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=symbol,
            wallet=WALLET,
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Masternode Reward":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_STAKING,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=symbol,
            wallet=WALLET,
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Payment to yourself":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=0,
            sell_asset=symbol,
            fee_quantity=amount,
            fee_asset=symbol,
            wallet=WALLET,
            note=row_dict["Label"],
        )
    elif row_dict["Type"] == "Name operation":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_SPEND,
            data_row.timestamp,
            sell_quantity=amount,
            sell_asset=symbol,
            wallet=WALLET,
            note=row_dict["Label"],
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _get_amount(amount):
    match = re.match(r"^(-?\d+\.\d+) (\w{3,4})$", amount)

    if match:
        amount = match.group(1)
        symbol = match.group(2)
        return abs(Decimal(amount)), symbol
    return abs(Decimal(amount)), None


def parse_vericoin_qt_wallet(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date/Time"], tz="Europe/London")

    if row_dict["Type"] == "Receive":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["Amount"],
            buy_asset="VRC",
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Send":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset="VRC",
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Stake":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_STAKING,
            data_row.timestamp,
            buy_quantity=row_dict["Amount"],
            buy_asset="VRC",
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    DataParser.TYPE_WALLET,
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
    DataParser.TYPE_WALLET,
    "Qt Wallet (i.e. Bitcoin Core, etc)",
    ["Confirmed", "Date", "Type", "Label", "Address", "Amount", "ID"],
    worksheet_name="Qt Wallet",
    row_handler=parse_qt_wallet,
)

DataParser(
    DataParser.TYPE_WALLET,
    "Qt Wallet (i.e. Bitcoin Core, etc)",
    ["Transaction", "Block", "Date/Time", "Type", "Amount", "Total"],
    worksheet_name="Qt Wallet",
    row_handler=parse_vericoin_qt_wallet,
)
