# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import re
from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import DataFilenameError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "APT"

ASSET_NORMALISE = {
    "AptosCoin": "APT",
    "BaptLabs": "BAPT",
}


def parse_aptoscan_txns(
    data_row: "DataRow", parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["Time"]) / 100000)
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("Version"),
        parser.in_header.index("From"),
        parser.in_header.index("To"),
    )

    if row_dict["Success"] != "true":
        return

    if row_dict["From"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Fee"]),
            sell_asset="APT",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict["Function"]),
        )


def parse_aptoscan_coin(
    data_row: "DataRow", parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["Time"]) / 100000)
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("Version"),
        parser.in_header.index("From"),
        parser.in_header.index("To"),
    )

    if row_dict["Success"] != "true":
        return

    if row_dict["To"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=_get_asset(row_dict["Coin_Type"]),
            wallet=_get_wallet(row_dict["To"]),
        )
    elif row_dict["From"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=_get_asset(row_dict["Coin_Type"]),
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset="APT",
            wallet=_get_wallet(row_dict["From"]),
        )
    else:
        raise DataFilenameError(kwargs["filename"], "Aptos address")


def parse_aptoscan_tokens(
    data_row: "DataRow", parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["Time"]) / 100000)
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("Version"),
        parser.in_header.index("From"),
        parser.in_header.index("To"),
    )

    if row_dict["Success"] != "true":
        return

    if row_dict["To"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(1),
            buy_asset=_get_asset(row_dict["Token"], is_nft=True),
            wallet=_get_wallet(row_dict["To"]),
        )
    elif row_dict["From"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(1),
            sell_asset=_get_asset(row_dict["Token"], is_nft=True),
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset="APT",
            wallet=_get_wallet(row_dict["From"]),
        )
    else:
        raise DataFilenameError(kwargs["filename"], "Aptos address")


def _get_asset(token_str: str, is_nft: bool = False) -> str:
    if is_nft:
        token_shorten = f"{token_str[:8]}...{token_str[-8:]}"
        return f"{token_shorten} #1"

    match = re.match(r"^(\w+)::(\w+)::(\w+)$", token_str)

    if match:
        token_symbol = match.group(3)
        if token_symbol in ASSET_NORMALISE:
            return ASSET_NORMALISE[token_symbol]
    return token_symbol


def _get_wallet(address: str) -> str:
    return f"{WALLET}-{address.lower()[0 : TransactionOutRecord.WALLET_ADDR_LEN]}"


def _get_note(function_str: str) -> str:
    match = re.match(r"^(\w+)::(\w+)::(\w+)$", function_str)
    if match:
        return f"{match.group(3)} ({match.group(2)})"
    return ""


avax_txns = DataParser(
    ParserType.EXPLORER,
    "Aptoscan (Transactions)",
    ["Version", "Block", "Time", "From", "To", "Function", "Fee", "Success"],
    worksheet_name="Aptoscan",
    row_handler=parse_aptoscan_txns,
)

apt_tokens = DataParser(
    ParserType.EXPLORER,
    "Aptoscan (Coin Transfers)",
    ["Version", "Block", "Time", "Coin_Type", "From", "To", "Amount", "Fee", "Success"],
    worksheet_name="Aptoscan",
    row_handler=parse_aptoscan_coin,
)

apt_nfts = DataParser(
    ParserType.EXPLORER,
    "Aptoscan (Token Transfers)",
    [
        "Version",
        "Block",
        "Time",
        "Token",
        "Token_Version",
        "From",
        "To",
        "Amount",
        "Fee",
        "Success",
    ],
    worksheet_name="Aptoscan",
    row_handler=parse_aptoscan_tokens,
)
