# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

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

WALLET = "Blockchair"


def parse_blockchair_simple(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:

    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"], dayfirst=True)
    data_row.tx_raw = TxRawPos(parser.in_header.index("Transaction hash"))

    if Decimal(row_dict["Effect"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Effect"]),
            buy_asset=row_dict["Ticker"],
            wallet=WALLET,
        )
    elif Decimal(row_dict["Effect"]) < 0:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Effect"])),
            sell_asset=row_dict["Ticker"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def parse_blockchair_extended(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:

    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"], dayfirst=True)
    data_row.tx_raw = TxRawPos(parser.in_header.index("Transaction hash"))

    if row_dict["Type"] == "External receiving":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Effect"]),
            buy_asset=row_dict["Ticker"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "External spending":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Effect"])),
            sell_asset=row_dict["Ticker"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Tx number"), 
                                  "Tx number", row_dict["Tx number"])


# simple format
DataParser(
    ParserType.WALLET,
    "Blockchair",
    [
        "Tx number",
        "Affected address/xpub",
        "Effect",
        "Ticker",
        "Amount fiat (USD)",
        "Asset rate (USD)",
        "Date",
        "Transaction hash",
    ],
    worksheet_name="Blockchair",
    row_handler=parse_blockchair_simple,
)

# extended format
DataParser(
    ParserType.WALLET,
    "Blockchair",
    [
        "Tx number",
        "Effect",
        "Ticker",
        "Amount fiat (USD)",
        "Asset rate (USD)",
        "Type",
        "Date",
        "Public key",
        "Wallet address",
        "Third-party address",
        "Transaction hash",
    ],
    worksheet_name="Blockchair",
    row_handler=parse_blockchair_extended,
)
