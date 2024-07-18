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

WALLET = "Neon Wallet"


def parse_neon_wallet(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(
        row_dict["time"].replace(" |", ""),
        tz=config.local_timezone,
        dayfirst=config.date_is_day_first,
    )
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("txid"), parser.in_header.index("from"), parser.in_header.index("to")
    )

    if row_dict["type"] == "RECEIVE":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount"]),
            buy_asset=row_dict["symbol"],
            wallet=WALLET,
        )
    elif row_dict["type"] == "SEND":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["amount"]),
            sell_asset=row_dict["symbol"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


DataParser(
    ParserType.WALLET,
    "Neon Wallet",
    ["to", "from", "txid", "time", "amount", "symbol", "type", "id"],
    worksheet_name="Neon Wallet",
    row_handler=parse_neon_wallet,
)
