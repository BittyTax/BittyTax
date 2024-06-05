# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Union

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Blockchain.com"


def parse_blockchain_v2(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = _get_timestamp(row_dict["date"], row_dict["time"])

    value = _get_fiat_value(row_dict["value_then"], data_row.timestamp)
    fee_value = _get_fiat_value(row_dict["fee_value_then"], data_row.timestamp)
    recipient_value = _get_fiat_value(row_dict["recipient_value_then"], data_row.timestamp)

    if Decimal(row_dict["amount"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount"]),
            buy_asset=row_dict["token"],
            buy_value=value,
            wallet=WALLET,
            note=row_dict["note"],
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["recipient_received"]),
            sell_asset=row_dict["token"],
            sell_value=recipient_value,
            fee_quantity=Decimal(row_dict["fee_value"]),
            fee_asset=row_dict["token"],
            fee_value=fee_value,
            wallet=WALLET,
            note=row_dict["note"],
        )


def _get_fiat_value(value_str: str, timestamp: datetime) -> Optional[Decimal]:
    symbol, value_str = value_str[0], value_str.strip("£€$ ").replace(",", "")
    if symbol == "£":
        value = DataParser.convert_currency(value_str, "GBP", timestamp)
    elif symbol == "€":
        value = DataParser.convert_currency(value_str, "EUR", timestamp)
    elif symbol == "$":
        value = DataParser.convert_currency(value_str, "USD", timestamp)
    else:
        value = None

    if value is not None:
        value = abs(value)

    return value


def _get_timestamp(date_str: str, time_str: str) -> datetime:
    # Strangely, the date and time columns can be one of:
    # date="2024-02-17", time="1708208107"
    # date="2024-02-17", time="22:15:07 GMT +00:00"
    # The first happens when the asset is BTC and the second happens when the
    # asset is ETH. Not sure about other assets.
    # Handle both cases.

    timestamp: Union[int, str]

    if time_str.isdigit():
        timestamp = int(time_str)
    else:
        timestamp = date_str + " " + time_str

    return DataParser.parse_timestamp(timestamp)


def parse_blockchain_v1(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = _get_timestamp(row_dict["date"], row_dict["time"])

    value = _get_fiat_value(row_dict["value_then"], data_row.timestamp)

    if Decimal(row_dict["amount"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount"]),
            buy_asset=row_dict["token"],
            buy_value=value,
            wallet=WALLET,
            note=row_dict["note"],
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["amount"])),
            sell_asset=row_dict["token"],
            sell_value=value,
            wallet=WALLET,
            note=row_dict["note"],
        )


def parse_blockchain_btc(
    data_row: "DataRow", parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    data_row.row_dict["token"] = "BTC"
    data_row.row_dict["amount"] = data_row.row_dict["amount_btc"]
    parse_blockchain_v1(data_row, parser, **kwargs)


DataParser(
    ParserType.WALLET,
    "Blockchain.com",
    [
        "date",
        "time",
        "token",
        "type",
        "amount",
        "value_then",
        "value_now",
        "exchange_rate_then",
        "tx",
        "note",
        "fee_value",
        "fee_value_then",
        "recipient_received",
        "recipient_value_then",
        "value_then_raw",
        "value_now_raw",
        "exchange_rate_then_raw",
    ],
    worksheet_name="Blockchain.com",
    row_handler=parse_blockchain_v2,
)

DataParser(
    ParserType.WALLET,
    "Blockchain.com",
    [
        "date",
        "time",
        "token",
        "type",
        "amount",
        "value_then",
        "value_now",
        "exchange_rate_then",
        "tx",
        "note",
    ],
    worksheet_name="Blockchain.com",
    row_handler=parse_blockchain_v1,
)

DataParser(
    ParserType.WALLET,
    "Blockchain.com",
    [
        "date",
        "time",
        "type",
        "amount_btc",
        "value_then",
        "value_now",
        "exchange_rate_then",
        "tx",
        "note",
    ],
    worksheet_name="Blockchain.com",
    row_handler=parse_blockchain_btc,
)
