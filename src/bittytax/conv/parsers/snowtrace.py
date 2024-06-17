# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataFilenameError
from ..out_record import TransactionOutRecord
from .etherscan import _get_note

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "AVAX"


def parse_snowtrace(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))

    if row_dict["Status"] != "":
        # Failed transactions should not have a Value_OUT
        row_dict["Value_OUT(ETH)"] = "0"

    if Decimal(row_dict["Value_IN(ETH)"]) > 0:
        if row_dict["Status"] == "":
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Value_IN(ETH)"]),
                buy_asset="AVAX",
                wallet=_get_wallet(row_dict["To"]),
                note=_get_note(row_dict),
            )
    elif Decimal(row_dict["Value_OUT(ETH)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(ETH)"]),
            sell_asset="AVAX",
            fee_quantity=Decimal(row_dict["TxnFee(ETH)"]),
            fee_asset="AVAX",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(ETH)"]),
            sell_asset="AVAX",
            fee_quantity=Decimal(row_dict["TxnFee(ETH)"]),
            fee_asset="AVAX",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )


def _get_wallet(address: str) -> str:
    return f"{WALLET}-{address.lower()[0 : TransactionOutRecord.WALLET_ADDR_LEN]}"


def parse_snowtrace_tokens(
    data_row: "DataRow", _parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["block_unix_timestamp"]) / 1000)
    row_dict["Transaction Hash"] = row_dict["tx_hash"]

    if row_dict["token_symbol"].endswith("-LP"):
        asset = row_dict["token_symbol"] + "-" + row_dict["ContractAddress"][0:10]
    else:
        asset = row_dict["token_symbol"]

    quantity = Decimal(row_dict["token_value"].replace(",", ""))

    if row_dict["to"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=quantity,
            buy_asset=asset,
            wallet=_get_wallet(row_dict["to"]),
        )
    elif row_dict["from"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=quantity,
            sell_asset=asset,
            wallet=_get_wallet(row_dict["from"]),
        )
    else:
        raise DataFilenameError(kwargs["filename"], "Ethereum address")


avax_txns = DataParser(
    ParserType.EXPLORER,
    "Snowtrace (Transactions)",
    [
        "Transaction Hash",
        "Blockno",
        "UnixTimestamp",
        "DateTime (UTC)",
        "From",
        "To",
        "ContractAddress",
        "Value_IN(ETH)",
        "Value_OUT(ETH)",
        "CurrentValue/Eth",
        "TxnFee(ETH)",
        "TxnFee(USD)",
        "Historical $Price/Eth",
        "Status",
        "ErrCode",
        "Method",
        "ChainId",
        "Chain",
        "Value(ETH)",
    ],
    worksheet_name="Snowtrace",
    row_handler=parse_snowtrace,
)

DataParser(
    ParserType.EXPLORER,
    "Snowtrace (Transactions)",
    [
        "Transaction Hash",
        "Blockno",
        "UnixTimestamp",
        "DateTime (UTC)",
        "From",
        "To",
        "ContractAddress",
        "Value_IN(ETH)",
        "Value_OUT(ETH)",
        "CurrentValue/Eth",
        "TxnFee(ETH)",
        "TxnFee(USD)",
        "Historical $Price/Eth",
        "Status",
        "ErrCode",
        "Method",
        "ChainId",
        "Chain",
        "Value(ETH)",
        "PrivateNote",
    ],
    worksheet_name="Snowtrace",
    row_handler=parse_snowtrace,
)

avax_tokens = DataParser(
    ParserType.EXPLORER,
    "Snowtrace (Token Transfers ERC-20)",
    [
        "chain_id",
        "tx_hash",
        "block_number",
        "block_unix_timestamp",
        "block_datetime",
        "from",
        "to",
        "token_value",
        "token_address",
        "token_name",
        "token_symbol",
    ],
    worksheet_name="Snowtrace",
    row_handler=parse_snowtrace_tokens,
)
