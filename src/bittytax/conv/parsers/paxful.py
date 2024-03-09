# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Paxful"


def parse_paxful(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])

    if row_dict["type"] == "Cryptocurrency purchased":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["crypto_amount"]),
            buy_asset=row_dict["crypto_currency"],
            sell_quantity=Decimal(row_dict["amount"].strip("A$").replace(",", "")),
            sell_asset=row_dict["currency"],
            wallet=WALLET,
        )
    elif row_dict["type"] == "Sent out":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["crypto_amount"])),
            sell_asset=row_dict["crypto_currency"],
            wallet=WALLET,
        )
    elif row_dict["type"] == "Received (internal) from affiliate balance":
        data_row.t_record = TransactionOutRecord(
            TrType.REFERRAL,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["crypto_amount"]),
            buy_asset=row_dict["crypto_currency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


DataParser(
    ParserType.EXCHANGE,
    "Paxful",
    [
        "type",
        "amount",
        "currency",
        "crypto_amount",
        "crypto_currency",
        "balance_usd",
        "balance_crypto",
        "sent_to",
        "transaction_id",
        "trade_hash",
        "sent_to_user",
        "received_from_user",
        "time",
    ],
    worksheet_name="Paxful",
    row_handler=parse_paxful,
)
