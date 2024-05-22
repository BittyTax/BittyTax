# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnknownUsernameError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "ChangeTip"


def parse_changetip(data_row: "DataRow", _parser: DataParser, **kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["When"])

    if row_dict["Status"] == "Delivered":
        if row_dict["To"] in config.usernames:
            data_row.t_record = TransactionOutRecord(
                TrType.GIFT_RECEIVED,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount in Satoshi"]) / 10**8,
                buy_asset="BTC",
                wallet=WALLET,
            )
        elif row_dict["From"] in config.usernames:
            data_row.t_record = TransactionOutRecord(
                TrType.GIFT_SENT,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["Amount in Satoshi"]) / 10**8,
                sell_asset="BTC",
                wallet=WALLET,
            )
        else:
            raise UnknownUsernameError(kwargs["filename"], kwargs.get("worksheet", ""))


DataParser(
    ParserType.EXCHANGE,
    "ChangeTip",
    ["On", "From", "To", "When", "Amount in Satoshi", "mBTC", "Status", "Message"],
    worksheet_name="ChangeTip",
    row_handler=parse_changetip,
)
