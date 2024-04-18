# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal
from typing import TYPE_CHECKING, Dict

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import UnexpectedTypeError, UnknownCryptoassetError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Blockscout"


def parse_blockscout(data_row: "DataRow", parser: DataParser, **kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["UnixTimestamp"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TxHash"),
        parser.in_header.index("FromAddress"),
        parser.in_header.index("ToAddress"),
    )

    if not kwargs["cryptoasset"]:
        raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet", ""))

    quantity = Decimal(row_dict["Value"]) / 10**18

    if row_dict["Type"] == "IN":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=quantity,
            buy_asset=kwargs["cryptoasset"],
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
            sell_asset=kwargs["cryptoasset"],
            fee_quantity=Decimal(row_dict["Fee"]) / 10**18,
            fee_asset=kwargs["cryptoasset"],
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
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TxHash"),
        parser.in_header.index("FromAddress"),
        parser.in_header.index("ToAddress"),
    )

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
    row_handler=parse_blockscout,
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
