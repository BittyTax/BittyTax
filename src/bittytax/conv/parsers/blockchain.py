# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Blockchain.com"


def parse_blockchain(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["date"] + " " + row_dict["time"])
    data_row.tx_raw = TxRawPos(parser.in_header.index("tx"))

    symbol, value_str = row_dict["value_then"][0], row_dict["value_then"].strip("£€$ ").replace(
        ",", ""
    )
    if symbol == "£":
        value = DataParser.convert_currency(value_str, "GBP", data_row.timestamp)
    elif symbol == "€":
        value = DataParser.convert_currency(value_str, "EUR", data_row.timestamp)
    elif symbol == "$":
        value = DataParser.convert_currency(value_str, "USD", data_row.timestamp)
    else:
        value = None

    if value is not None:
        value = abs(value)

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
    parse_blockchain(data_row, parser, **kwargs)


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
    row_handler=parse_blockchain,
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
