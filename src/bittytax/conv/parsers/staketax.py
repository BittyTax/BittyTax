# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

import json
from decimal import Decimal
from typing import TYPE_CHECKING, Union

from typing_extensions import Unpack

from ...bt_types import TrType, UnmappedType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import UnexpectedTypeError
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


def parse_staketax_default(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    if row_dict["timestamp"]:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["timestamp"])

    data_row.tx_raw = TxRawPos(parser.in_header.index("txid"))

    if row_dict["tx_type"].startswith("_"):
        t_type: Union[TrType, UnmappedType] = UnmappedType(row_dict["tx_type"])
    else:
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

    # Add a dummy sell_quantity if fee is on it's own
    if fee_quantity is not None and (buy_quantity is None and sell_quantity is None):
        sell_quantity = Decimal(0)
        sell_asset = row_dict["fee_currency"]
    else:
        sell_asset = row_dict["sent_currency"]

    data_row.t_record = TransactionOutRecord(
        t_type,
        data_row.timestamp,
        buy_quantity=buy_quantity,
        buy_asset=row_dict["received_currency"],
        sell_quantity=sell_quantity,
        sell_asset=sell_asset,
        fee_quantity=fee_quantity,
        fee_asset=row_dict["fee_currency"],
        wallet=_get_wallet(row_dict["exchange"], row_dict["wallet_address"]),
        note=row_dict["comment"],
    )

    parser.worksheet_name = (
        "StakeTax " + row_dict["exchange"].replace("_blockchain", "").capitalize()
    )


def _get_wallet(exchange: str, wallet_address: str) -> str:
    return f'{exchange.replace("_blockchain", "").capitalize()}-{wallet_address[0:16]}'


def parse_staketax_bittytax(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    if row_dict["Timestamp"]:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["Timestamp"])

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

    data_row.t_record = TransactionOutRecord(
        t_type,
        data_row.timestamp,
        buy_quantity=buy_quantity,
        buy_asset=row_dict["Buy Asset"],
        sell_quantity=sell_quantity,
        sell_asset=row_dict["Sell Asset"],
        fee_quantity=fee_quantity,
        fee_asset=row_dict["Fee Asset"],
        wallet=row_dict["Wallet"],
        note=row_dict["Note"],
    )

    # Remove TR headers and data
    if len(parser.in_header) > len(OutputBase.BITTYTAX_OUT_HEADER):
        del parser.in_header[0 : len(OutputBase.BITTYTAX_OUT_HEADER)]
    del data_row.row[0 : len(OutputBase.BITTYTAX_OUT_HEADER)]

    data_row.tx_raw = TxRawPos(parser.in_header.index("Tx ID"))
    raw = json.loads(row_dict["Raw Data"])
    parser.worksheet_name = "StakeTax " + raw["exchange"].replace("_blockchain", "").capitalize()


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
    row_handler=parse_staketax_default,
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
    row_handler=parse_staketax_bittytax,
)
