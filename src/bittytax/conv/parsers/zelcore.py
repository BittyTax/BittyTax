# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

import re
from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Zelcore"


def parse_zelcore_kda(
    data_row: "DataRow", _parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["timestamp"]) / 1000)

    if row_dict["isError"] != "0":
        quantity = Decimal(0)
        note = "Failure"
    else:
        quantity = Decimal(row_dict["amount"])
        note = ""

    if Decimal(row_dict["amount"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=quantity,
            buy_asset="KDA",
            wallet=_get_wallet(kwargs["filename"], row_dict["chainid"]),
            note=note,
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(quantity),
            sell_asset="KDA",
            wallet=_get_wallet(kwargs["filename"], row_dict["chainid"]),
            note=note,
        )


def _get_wallet(filename: str, chain_id: str) -> str:
    match = re.match(r".+KDA_transactions_(k_)?(\w+).csv$", filename)

    if match:
        if match.group(1) is None:
            return (
                f"{WALLET}-{match.group(2).lower()[0 : TransactionOutRecord.WALLET_ADDR_LEN]}:"
                f"{chain_id}"
            )
        return (
            f"{WALLET}-k:{match.group(2).lower()[0 : TransactionOutRecord.WALLET_ADDR_LEN]}:"
            f"{chain_id}"
        )
    return WALLET


DataParser(
    ParserType.WALLET,
    "Zelcore Kadena",
    [
        "txid",
        "formattedDate",
        "timestamp",
        "direction",
        "amount",
        "chainid",
        "destinationchainid",
        "isError",
        "type",
        "asset",
        "swapTokenIn",
        "swapTokenOut",
    ],
    worksheet_name="Zelcore KDA",
    row_handler=parse_zelcore_kda,
)
