# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Eternl"


def parse_eternl(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"], tz=config.local_timezone)
    data_row.tx_raw = TxRawPos(parser.in_header.index("TxHash"))

    if row_dict["TxType"] == "Received Funds":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Received Amount"].replace(",", ".")),
            buy_asset=row_dict["Received Currency"],
            wallet=WALLET,
        )
    elif row_dict["TxType"] in ("Sent Funds", "Internal Transfer - Withdrawal"):
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Sent Amount"].replace(",", ".")),
            sell_asset=row_dict["Sent Currency"],
            fee_quantity=Decimal(row_dict["Fee Amount"].replace(",", ".")),
            fee_asset=row_dict["Fee Currency"],
            wallet=WALLET,
        )
    elif not row_dict["TxType"]:
        if row_dict["Label"] == "reward":
            data_row.t_record = TransactionOutRecord(
                TrType.STAKING_REWARD,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Received Amount"].replace(",", ".")),
                buy_asset=row_dict["Received Currency"],
                wallet=WALLET,
            )
        else:
            raise UnexpectedTypeError(parser.in_header.index("Label"), "Label", row_dict["Label"])
    else:
        raise UnexpectedTypeError(parser.in_header.index("TxType"), "TxType", row_dict["TxType"])


DataParser(
    ParserType.WALLET,
    "Eternl",
    [
        "Date",
        "Sent Amount",
        "Sent Currency",
        "Received Amount",
        "Received Currency",
        "Fee Amount",
        "Fee Currency",
        "Label",
        "Description",
        "TxHash",
        "TxType",
    ],
    worksheet_name="Eternl",
    row_handler=parse_eternl,
)
