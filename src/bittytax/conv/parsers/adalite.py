# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

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

WALLET = "AdaLite"


def parse_adalite(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if "Received from (disclaimer: may not be accurate - first sender address only)" in row_dict:
        data_row.tx_raw = TxRawPos(
            parser.in_header.index("Transaction ID"),
            parser.in_header.index(
                "Received from (disclaimer: may not be accurate - first sender address only)"
            ),
        )
    else:
        data_row.tx_raw = TxRawPos(parser.in_header.index("Transaction ID"))

    if row_dict["Type"] == "Received":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Received amount"]),
            buy_asset=row_dict["Received currency"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Sent":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Sent amount"]),
            sell_asset=row_dict["Sent currency"],
            fee_quantity=Decimal(row_dict["Fee amount"]),
            fee_asset=row_dict["Fee currency"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Reward awarded":
        data_row.t_record = TransactionOutRecord(
            TrType.STAKING_REWARD,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Received amount"]),
            buy_asset=row_dict["Received currency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    ParserType.WALLET,
    "AdaLite",
    [
        "Date",
        "Transaction ID",
        "Type",
        "Received from (disclaimer: may not be accurate - first sender address only)",
        "Received amount",
        "Received currency",
        "Sent amount",
        "Sent currency",
        "Fee amount",
        "Fee currency",
    ],
    worksheet_name="AdaLite",
    row_handler=parse_adalite,
)

DataParser(
    ParserType.WALLET,
    "AdaLite",
    [
        "Date",
        "Transaction ID",
        "Type",
        "Received amount",
        "Received currency",
        "Sent amount",
        "Sent currency",
        "Fee amount",
        "Fee currency",
    ],
    worksheet_name="AdaLite",
    row_handler=parse_adalite,
)
