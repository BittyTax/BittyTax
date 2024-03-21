# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

import sys
from decimal import Decimal
from typing import TYPE_CHECKING, List, Union

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType, UnmappedType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import (
    DataRowError,
    UnexpectedTypeError,
)
from ..out_record import TransactionOutRecord
from ..output_csv import OutputBase

if TYPE_CHECKING:
    from ..datarow import DataRow

STAKETAX_MAPPING = {
    "STAKING": TrType.STAKING,
    "AIRDROP": TrType.AIRDROP,
    "TRADE": TrType.TRADE,
    "SPEND": TrType.SPEND,
    "INCOME": TrType.INCOME,
    "LP_DEPOSIT": TrType.TRADE,
    "LP_WITHDRAW": TrType.TRADE,
}

STANDARDIZE_ASSET_TERRA = {
    "LUNA": "LUNC",
    "UST": "USTC",
    "AUD": "AUDC",
    "CAD": "CADC",
    "CHF": "CHFC",
    "CNY": "CNYC",
    "DKK": "DKKC",
    "EUR": "EURC",
    "GBP": "GBPC",
    "HKD": "HKDC",
    "IDR": "IDRC",
    "INR": "INRC",
    "JPY": "JPYC",
    "KRT": "KRTC",
    "MNT": "MNTC",
    "MYR": "MYRC",
    "NOK": "NOKC",
    "PHP": "PHPC",
    "SDR": "SDRC",
    "SEK": "SEKC",
    "SGD": "SGDC",
    "THB": "THBC",
    "TWD": "TWDC",
}


def parse_staketax_default(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    for row_index, data_row in enumerate(data_rows):
        if row_index == 1:
            row_dict = data_row.row_dict
            if parser.p_type == ParserType.ACCOUNTING:
                parser.worksheet_name = (
                    "StakeTax " + row_dict["exchange"].replace("_blockchain", "").capitalize()
                )
            else:
                parser.worksheet_name = (
                    "StakeTax " + row_dict["Wallet"][: row_dict["Wallet"].find("-")]
                )
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
            if parser.p_type == ParserType.ACCOUNTING:
                parse_staketax_row(parser, data_row)
            else:
                parse_bittytax_row(parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def parse_staketax_row(
    parser: DataParser,
    data_row: "DataRow",
) -> None:
    row_dict = data_row.row_dict
    if row_dict["timestamp"]:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["timestamp"])
    data_row.parsed = True

    # Ignore known unhandled types.
    if row_dict["tx_type"].startswith("_"):
        return

    if row_dict["tx_type"] in STAKETAX_MAPPING:
        t_type = STAKETAX_MAPPING[row_dict["tx_type"]]
    else:
        t_type = UnmappedType(f'_{row_dict["tx_type"]}')

    if row_dict["received_amount"]:
        buy_quantity = Decimal(row_dict["received_amount"])
    else:
        buy_quantity = None

    if row_dict["sent_amount"]:
        sell_quantity = Decimal(row_dict["sent_amount"])
    else:
        sell_quantity = None

    if row_dict["fee"]:
        fee_quantity = Decimal(row_dict["fee"])
    else:
        fee_quantity = None

    if row_dict["tx_type"] == "TRANSFER":
        if buy_quantity is not None and sell_quantity is None:
            t_type = TrType.DEPOSIT
        elif sell_quantity is not None and buy_quantity is None:
            t_type = TrType.WITHDRAWAL
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("tx_type"), "tx_type", row_dict["tx_type"]
            )

    buy_asset = row_dict["received_currency"]
    sell_asset = row_dict["sent_currency"]
    fee_asset = row_dict["fee_currency"]

    # Add a dummy sell_quantity if fee is on it's own
    if fee_quantity is not None and (buy_quantity is None and sell_quantity is None):
        sell_quantity = Decimal(0)
        sell_asset = row_dict["fee_currency"]
    else:
        sell_asset = row_dict["sent_currency"]

    # Convert assets to a recognized token name.
    if row_dict["Wallet"].find("Terra") > -1:
        for wallet_asset, asset in STANDARDIZE_ASSET_TERRA.items():
            buy_asset = buy_asset.replace(wallet_asset, asset)
            sell_asset = sell_asset.replace(wallet_asset, asset)
            fee_asset = fee_asset.replace(wallet_asset, asset)

    data_row.t_record = TransactionOutRecord(
        t_type,
        data_row.timestamp,
        buy_quantity=buy_quantity,
        buy_asset=buy_asset,
        sell_quantity=sell_quantity,
        sell_asset=sell_asset,
        fee_quantity=fee_quantity,
        fee_asset=fee_asset,
        wallet=_get_wallet(row_dict["exchange"], row_dict["wallet_address"]),
        note=row_dict["comment"],
    )


def _get_wallet(exchange: str, wallet_address: str) -> str:
    return f'{exchange.replace("_blockchain", "").capitalize()}-{wallet_address[0:16]}'


def parse_bittytax_row(
    parser: DataParser,
    data_row: "DataRow",
) -> None:
    row_dict = data_row.row_dict
    if row_dict["Timestamp"]:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["Timestamp"])
    data_row.parsed = True

    try:
        t_type: Union[TrType, UnmappedType] = TrType(row_dict["Type"])
    except ValueError:
        t_type = UnmappedType(row_dict["Type"])

    if row_dict["Buy Quantity"]:
        buy_quantity = Decimal(row_dict["Buy Quantity"])
    else:
        buy_quantity = None

    if row_dict["Sell Quantity"]:
        sell_quantity = Decimal(row_dict["Sell Quantity"])
    else:
        sell_quantity = None

    if row_dict["Fee Quantity"]:
        fee_quantity = Decimal(row_dict["Fee Quantity"])
    else:
        fee_quantity = None

    buy_asset = row_dict["Buy Asset"]
    sell_asset = row_dict["Sell Asset"]
    fee_asset = row_dict["Fee Asset"]

    # Convert assets to a recognized token name.
    if row_dict["Wallet"].find("Terra") > -1:
        for wallet_asset, asset in STANDARDIZE_ASSET_TERRA.items():
            buy_asset = buy_asset.replace(wallet_asset, asset)
            sell_asset = sell_asset.replace(wallet_asset, asset)
            fee_asset = fee_asset.replace(wallet_asset, asset)

    data_row.t_record = TransactionOutRecord(
        t_type,
        data_row.timestamp,
        buy_quantity=buy_quantity,
        buy_asset=buy_asset,
        sell_quantity=sell_quantity,
        sell_asset=sell_asset,
        fee_quantity=fee_quantity,
        fee_asset=fee_asset,
        wallet=row_dict["Wallet"],
        note=row_dict["Note"],
    )

    # Remove TR headers and data
    if len(parser.in_header) > len(OutputBase.BITTYTAX_OUT_HEADER):
        del parser.in_header[0 : len(OutputBase.BITTYTAX_OUT_HEADER)]
    del data_row.row[0 : len(OutputBase.BITTYTAX_OUT_HEADER)]


DataParser(
    ParserType.ACCOUNTING,
    "StakeTax",
    [
        "timestamp",
        "tx_type",
        "received_amount",
        "received_currency",
        "sent_amount",
        "sent_currency",
        "fee",
        "fee_currency",
        "comment",
        "txid",
        "url",
        "exchange",
        "wallet_address",
    ],
    worksheet_name="StakeTax",
    all_handler=parse_staketax_default,
)

DataParser(
    ParserType.GENERIC,
    "StakeTax",
    [
        "Type",
        "Buy Quantity",
        "Buy Asset",
        "Buy Value",
        "Sell Quantity",
        "Sell Asset",
        "Sell Value",
        "Fee Quantity",
        "Fee Asset",
        "Fee Value",
        "Wallet",
        "Timestamp",
        "Note",
        "Tx ID",
        "URL",
        "Raw Data",
    ],
    worksheet_name="StakeTax",
    all_handler=parse_staketax_default,
)
