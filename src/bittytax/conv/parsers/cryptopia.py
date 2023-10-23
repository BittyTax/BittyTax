# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Cryptopia"

PRECISION = Decimal("0.00000000")


def parse_cryptopia_deposits(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Timestamp"])

    data_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount"]),
        buy_asset=row_dict["Currency"],
        wallet=WALLET,
    )


def parse_cryptopia_withdrawals(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Timestamp"])

    data_row.t_record = TransactionOutRecord(
        TrType.WITHDRAWAL,
        data_row.timestamp,
        sell_quantity=Decimal(row_dict["Amount"]) - Decimal(row_dict["Fee"]),
        sell_asset=row_dict["Currency"],
        fee_quantity=Decimal(row_dict["Fee"]),
        fee_asset=row_dict["Currency"],
        wallet=WALLET,
    )


def parse_cryptopia_trades(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Timestamp"])

    if row_dict["Type"] == "Buy":
        sell_quantity = Decimal(row_dict["Rate"]) * Decimal(row_dict["Amount"])

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Market"].split("/")[0],
            sell_quantity=sell_quantity.quantize(PRECISION),
            sell_asset=row_dict["Market"].split("/")[1],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Market"].split("/")[0],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Sell":
        buy_quantity = Decimal(row_dict["Rate"]) * Decimal(row_dict["Amount"])

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=buy_quantity.quantize(PRECISION),
            buy_asset=row_dict["Market"].split("/")[1],
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Market"].split("/")[0],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Market"].split("/")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    ParserType.EXCHANGE,
    "Cryptopia Deposits",
    ["#", "Currency", "Amount", "Status", "Type", "Transaction", "Conf.", "Timestamp"],
    worksheet_name="Cryptopia D",
    row_handler=parse_cryptopia_deposits,
)

DataParser(
    ParserType.EXCHANGE,
    "Cryptopia Withdrawals",
    [
        "#",
        "Currency",
        "Amount",
        "Fee",
        "Status",
        "TransactionId",
        "Address",
        "Timestamp",
    ],
    worksheet_name="Cryptopia W",
    row_handler=parse_cryptopia_withdrawals,
)

DataParser(
    ParserType.EXCHANGE,
    "Cryptopia Trades",
    ["#", "Market", "Type", "Rate", "Amount", "Total", "Fee", "Timestamp"],
    worksheet_name="Cryptopia T",
    row_handler=parse_cryptopia_trades,
)
