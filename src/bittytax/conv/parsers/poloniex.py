# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import ROUND_DOWN, Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Poloniex"

PRECISION = Decimal("0.00000000")


def parse_poloniex_trades(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["Type"] == "Buy":
        fee_quantity = Decimal(row_dict["Amount"]) * (
            Decimal(row_dict["Fee"].replace("%", "")) / Decimal(100)
        )
        fee_quantity = fee_quantity.quantize(PRECISION, rounding=ROUND_DOWN)

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Market"].split("/")[0],
            sell_quantity=Decimal(row_dict["Total"]),
            sell_asset=row_dict["Market"].split("/")[1],
            fee_quantity=fee_quantity,
            fee_asset=row_dict["Market"].split("/")[0],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Sell":
        fee_quantity = Decimal(row_dict["Total"]) * (
            Decimal(row_dict["Fee"].replace("%", "")) / Decimal(100)
        )
        fee_quantity = fee_quantity.quantize(PRECISION, rounding=ROUND_DOWN)

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Total"]),
            buy_asset=row_dict["Market"].split("/")[1],
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Market"].split("/")[0],
            fee_quantity=fee_quantity,
            fee_asset=row_dict["Market"].split("/")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def parse_poloniex_deposits_withdrawals(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if "COMPLETE: " in row_dict["Status"]:
        # Legacy format also contained Withdrawals
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Currency"],
            wallet=WALLET,
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"],
            wallet=WALLET,
        )


def parse_poloniex_withdrawals(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    data_row.t_record = TransactionOutRecord(
        TrType.WITHDRAWAL,
        data_row.timestamp,
        sell_quantity=Decimal(row_dict["Amount"]) - Decimal(row_dict["Fee Deducted"]),
        sell_asset=row_dict["Currency"],
        fee_quantity=Decimal(row_dict["Fee Deducted"]),
        fee_asset=row_dict["Currency"],
        wallet=WALLET,
    )


def parse_poloniex_distributions(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["date"])

    data_row.t_record = TransactionOutRecord(
        TrType.AIRDROP,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["amount"]),
        buy_asset=row_dict["currency"],
        wallet=WALLET,
    )


DataParser(
    ParserType.EXCHANGE,
    "Poloniex Trades",
    [
        "Date",
        "Market",
        "Category",
        "Type",
        "Price",
        "Amount",
        "Total",
        "Fee",
        "Order Number",
        "Base Total Less Fee",
        "Quote Total Less Fee",
        "Fee Currency",
        "Fee Total",
    ],
    worksheet_name="Poloniex T",
    row_handler=parse_poloniex_trades,
)

DataParser(
    ParserType.EXCHANGE,
    "Poloniex Trades",
    [
        "Date",
        "Market",
        "Category",
        "Type",
        "Price",
        "Amount",
        "Total",
        "Fee",
        "Order Number",
        "Base Total Less Fee",
        "Quote Total Less Fee",
    ],
    worksheet_name="Poloniex T",
    row_handler=parse_poloniex_trades,
)

DataParser(
    ParserType.EXCHANGE,
    "Poloniex Deposits",
    ["Date", "Currency", "Amount", "Address", "Status"],
    worksheet_name="Poloniex D",
    row_handler=parse_poloniex_deposits_withdrawals,
)

DataParser(
    ParserType.EXCHANGE,
    "Poloniex Withdrawals",
    ["Date", "Currency", "Amount", "Fee Deducted", "Amount - Fee", "Address", "Status"],
    worksheet_name="Poloniex W",
    row_handler=parse_poloniex_withdrawals,
)

DataParser(
    ParserType.EXCHANGE,
    "Poloniex Distributions",
    ["date", "currency", "amount", "wallet"],
    worksheet_name="Poloniex D",
    row_handler=parse_poloniex_distributions,
)
