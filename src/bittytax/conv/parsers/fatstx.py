# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import re
from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Stacks"


def parse_fatstx(data_row: "DataRow", parser: DataParser, **kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["burnDate"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("xactnId"),
        parser.in_header.index("sender"),
        parser.in_header.index("recipient"),
    )

    in_value = out_value = fee_value = None

    if row_dict["inCoinPrice"] != "N/A":
        coin_price = DataParser.convert_currency(
            row_dict["inCoinPrice"], row_dict["currency"], data_row.timestamp
        )
        in_value = Decimal(row_dict["inAmount"]) * coin_price if coin_price else None

    if row_dict["outCoinPrice"] != "N/A":
        coin_price = DataParser.convert_currency(
            row_dict["outCoinPrice"], row_dict["currency"], data_row.timestamp
        )
        out_value = Decimal(row_dict["outAmount"]) * coin_price if coin_price else None

    if row_dict["xactnFeeCoinPrice"] != "N/A":
        coin_price = DataParser.convert_currency(
            row_dict["xactnFeeCoinPrice"], row_dict["currency"], data_row.timestamp
        )
        fee_value = Decimal(row_dict["xactnFee"]) * coin_price if coin_price else None

    if row_dict["xactnType"] == "Receive":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["inAmount"]),
            buy_asset=row_dict["inSymbol"],
            buy_value=in_value,
            fee_quantity=Decimal(row_dict["xactnFee"]),
            fee_asset="STX",
            fee_value=fee_value,
            wallet=_get_wallet(kwargs["filename"]),
            note=row_dict["xactnTypeDetail"],
        )
    elif row_dict["xactnType"] == "Send":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["outAmount"]),
            sell_asset=row_dict["outSymbol"],
            sell_value=out_value,
            fee_quantity=Decimal(row_dict["xactnFee"]),
            fee_asset="STX",
            fee_value=fee_value,
            wallet=_get_wallet(kwargs["filename"]),
            note=row_dict["xactnTypeDetail"],
        )
    elif row_dict["xactnType"] in ("Trade Coin", "Swap Coin for NFT"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["inAmount"]),
            buy_asset=row_dict["inSymbol"],
            buy_value=in_value,
            sell_quantity=Decimal(row_dict["outAmount"]),
            sell_asset=row_dict["outSymbol"],
            sell_value=out_value,
            fee_quantity=Decimal(row_dict["xactnFee"]),
            fee_asset="STX",
            fee_value=fee_value,
            wallet=_get_wallet(kwargs["filename"]),
            note=row_dict["xactnTypeDetail"],
        )
    elif row_dict["xactnType"] == "XFee Only":
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=Decimal(0),
            sell_asset="STX",
            fee_quantity=Decimal(row_dict["xactnFee"]),
            fee_asset="STX",
            fee_value=fee_value,
            wallet=_get_wallet(kwargs["filename"]),
            note=row_dict["xactnTypeDetail"],
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("xactnType"), "xactnType", row_dict["xactnType"]
        )


def _get_wallet(filename: str) -> str:
    match = re.match(r"^.*transactions-(\w+)([ |-].*)?\.csv$", filename)
    if match:
        address = match.group(1)
        return f"{WALLET}-{address[0:4]}...{address[-4:]}"
    return WALLET


DataParser(
    ParserType.EXPLORER,
    "FatStx",
    [
        "currency",
        "burnDate",
        "inSymbol",
        "inAmount",
        "outSymbol",
        "outAmount",
        "xactnFee",
        "inCoinPrice",
        "outCoinPrice",
        "xactnFeeCoinPrice",
        "xactnType",
        "xactnTypeDetail",
        "xactnId",
        "inAmountRaw",
        "outAmountRaw",
        "xactnFeeRaw",
        "sender",
        "recipient",
        "memo",
        "burnDateAltFormat1",
    ],
    worksheet_name="FatStx",
    row_handler=parse_fatstx,
)
