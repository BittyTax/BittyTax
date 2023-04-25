# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

import re
from decimal import Decimal

from ..dataparser import DataParser
from ..out_record import TransactionOutRecord

WALLET = "Zelcore"


def parse_zelcore_kda(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["timestamp"]) / 1000)

    if row_dict["isError"] != "0":
        row_dict["amount"] = 0
        note = "Failure"
    else:
        note = ""

    if Decimal(row_dict["amount"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["amount"],
            buy_asset="KDA",
            wallet=_get_wallet(kwargs["filename"], row_dict["chainid"]),
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["amount"])),
            sell_asset="KDA",
            wallet=_get_wallet(kwargs["filename"], row_dict["chainid"]),
            note=note,
        )


def _get_wallet(filename, chain_id):
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
    DataParser.TYPE_WALLET,
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
