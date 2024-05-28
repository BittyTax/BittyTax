# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ...constants import WARNING
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError, UnknownCryptoassetError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Blockscout"


def parse_blockscout(
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
            _parse_blockscout_row(data_row, parser, symbol)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_blockscout_row(data_row: "DataRow", parser: DataParser, symbol: str) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["UnixTimestamp"])

    quantity = Decimal(row_dict["Value"]) / 10**18

    if row_dict["Type"] == "IN":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=quantity,
            buy_asset=symbol,
            wallet=_get_wallet(row_dict["ToAddress"]),
            note=_get_note(row_dict),
        )
    elif row_dict["Type"] == "OUT":
        if quantity > 0:
            t_type = TrType.WITHDRAWAL
        else:
            t_type = TrType.SPEND

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            sell_quantity=quantity,
            sell_asset=symbol,
            fee_quantity=Decimal(row_dict["Fee"]) / 10**18,
            fee_asset=symbol,
            wallet=_get_wallet(row_dict["FromAddress"]),
            note=_get_note(row_dict),
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def parse_blockscout_tokens(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["UnixTimestamp"])

    if row_dict["Type"] == "IN":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["TokensTransferred"]) / 10**18,
            buy_asset=row_dict["TokenSymbol"],
            wallet=_get_wallet(row_dict["ToAddress"]),
            note=_get_note(row_dict),
        )
    elif row_dict["Type"] == "OUT":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["TokensTransfered"]) / 10**18,
            sell_asset=row_dict["TokenSymbol"],
            wallet=_get_wallet(row_dict["FromAddress"]),
            note=_get_note(row_dict),
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _get_wallet(address: str) -> str:
    return f"{WALLET}-{address.lower()[0 : TransactionOutRecord.WALLET_ADDR_LEN]}"


def _get_note(row_dict: Dict[str, str]) -> str:
    if row_dict["Status"] != "ok":
        return "Failure"
    return ""


DataParser(
    ParserType.EXPLORER,
    "Blockscout",
    [
        "TxHash",
        "BlockNumber",
        "UnixTimestamp",
        "FromAddress",
        "ToAddress",
        "ContractAddress",
        "Type",
        "Value",
        "Fee",
        "Status",
        "ErrCode",
        "CurrentPrice",
        "TxDateOpeningPrice",
        "TxDateClosingPrice",
    ],
    worksheet_name="Blockscout",
    all_handler=parse_blockscout,
)

DataParser(
    ParserType.EXPLORER,
    "Blockscout (Tokens)",
    [
        "TxHash",
        "BlockNumber",
        "UnixTimestamp",
        "FromAddress",
        "ToAddress",
        "TokenContractAddress",
        "Type",
        "TokenSymbol",
        "TokensTransferred",
        "TransactionFee",
        "Status",
        "ErrCode",
    ],
    worksheet_name="Blockscout",
    row_handler=parse_blockscout_tokens,
)
