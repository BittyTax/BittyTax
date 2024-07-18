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

WALLET = "Easy Crypto"


def parse_easy_crypto(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"], tz="Pacific/Auckland")
    data_row.tx_raw = TxRawPos(
        tx_dest_pos=parser.in_header.index("To address"),
    )

    if row_dict["Type"] in ("buy", "sell"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["To amount"]),
            buy_asset=row_dict["To symbol"],
            sell_quantity=Decimal(row_dict["From amount"]),
            sell_asset=row_dict["From symbol"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    ParserType.EXCHANGE,
    "Easy Crypto",
    [
        "Date",
        "Order ID",
        "Type",
        "From symbol",
        "To symbol",
        "From amount",
        "To amount",
        "To address",
        "To memo",
        "Fiat Value",
    ],
    worksheet_name="Easy Crypto",
    row_handler=parse_easy_crypto,
)
