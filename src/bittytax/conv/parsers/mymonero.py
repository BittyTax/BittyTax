# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "MyMonero"


def parse_mymonero(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["date"])
    data_row.tx_raw = TxRawPos(parser.in_header.index("tx id"))
    symbol = "XMR"

    if row_dict["status"] != "CONFIRMED":
        return

    amount = Decimal(row_dict["amount"])

    if amount > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=symbol,
            wallet=WALLET,
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(amount),
            sell_asset=symbol,
            wallet=WALLET,
        )


DataParser(
    ParserType.WALLET,
    "MyMonero",
    ["date", "amount", "status", "tx id", "payment_id"],
    worksheet_name="MyMonero",
    row_handler=parse_mymonero,
)
