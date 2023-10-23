# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Bittylicious"


def parse_bittylicious(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["startedTime"])

    if row_dict["status"] != "RECEIVED":
        return

    if row_dict["direction"] == "BUY":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["coinAmount"]),
            buy_asset=row_dict["coin"],
            sell_quantity=Decimal(row_dict["fiatCurrencyAmount"]),
            sell_asset=row_dict["fiatCurrency"],
            wallet=WALLET,
        )
    elif row_dict["direction"] == "SELL":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["fiatCurrencyAmount"]),
            buy_asset=row_dict["fiatCurrency"],
            sell_quantity=Decimal(row_dict["coinAmount"]),
            sell_asset=row_dict["coin"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("direction"), "direction", row_dict["direction"]
        )


DataParser(
    ParserType.EXCHANGE,
    "Bittylicious",
    [
        "reference",
        "direction",
        "status",
        "coin",
        "coinAmount",
        "fiatCurrency",
        "fiatCurrencyAmount",
        "startedTime",
        "endedTime",
        "transactionID",
        "coinAddress",
    ],
    worksheet_name="Bittylicious",
    row_handler=parse_bittylicious,
)
