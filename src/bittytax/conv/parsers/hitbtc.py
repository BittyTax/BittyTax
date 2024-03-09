# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import copy
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, List

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "HitBTC"


def parse_hitbtc_trades_v2(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    for row_index, data_row in enumerate(data_rows):
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f"row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if data_row.parsed:
            continue

        try:
            _parse_hitbtc_trades_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_hitbtc_trades_row(
    data_rows: List["DataRow"], parser: DataParser, data_row: "DataRow", row_index: int
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date (UTC)"])
    data_row.parsed = True

    # Negative fees are rebates
    if Decimal(row_dict["Fee"]) < 0:
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []
        dup_data_row.t_record = TransactionOutRecord(
            TrType.FEE_REBATE,
            data_row.timestamp,
            buy_quantity=abs(Decimal(row_dict["Fee"])),
            buy_asset=row_dict["Instrument"].split("/")[1],
            wallet=WALLET,
        )
        data_rows.insert(row_index + 1, dup_data_row)

        fee_quantity = Decimal(0)
    else:
        fee_quantity = Decimal(row_dict["Fee"])

    fee_asset = row_dict["Instrument"].split("/")[1]

    if row_dict["Side"] == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]),
            buy_asset=row_dict["Instrument"].split("/")[0],
            sell_quantity=Decimal(row_dict["Quantity"]) * Decimal(row_dict["Price"]),
            sell_asset=row_dict["Instrument"].split("/")[1],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["Side"] == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]) * Decimal(row_dict["Price"]),
            buy_asset=row_dict["Instrument"].split("/")[1],
            sell_quantity=Decimal(row_dict["Quantity"]),
            sell_asset=row_dict["Instrument"].split("/")[0],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


def parse_hitbtc_trades_v1(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date (UTC)"])

    if row_dict["Side"] == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]),
            buy_asset=row_dict["Instrument"].split("/")[0],
            sell_quantity=Decimal(row_dict["Volume"]) - Decimal(row_dict["Rebate"]),
            sell_asset=row_dict["Instrument"].split("/")[1],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Instrument"].split("/")[1],
            wallet=WALLET,
        )
    elif row_dict["Side"] == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Volume"]) + Decimal(row_dict["Rebate"]),
            buy_asset=row_dict["Instrument"].split("/")[1],
            sell_quantity=Decimal(row_dict["Quantity"]),
            sell_asset=row_dict["Instrument"].split("/")[0],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Instrument"].split("/")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


def parse_hitbtc_deposits_withdrawals_v2(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date (UTC)"])

    # Looks like a bug in the exporter, Withdrawals are blank
    #  failed transactions have no transaction hash
    if row_dict["Type"] in ("Withdraw", "") and row_dict["Transaction hash"] != "":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=row_dict["Currency"].upper(),
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Deposit" and row_dict["Transaction hash"] != "":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"].upper(),
            wallet=WALLET,
        )


def parse_hitbtc_deposits_withdrawals_v1(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date (UTC)"])

    if row_dict["Type"] == "Withdraw":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=data_row.row[6],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Deposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=data_row.row[6],
            wallet=WALLET,
        )


DataParser(
    ParserType.EXCHANGE,
    "HitBTC Trades",
    [
        "Email",
        "Date (UTC)",
        "Instrument",
        "Trade ID",
        "Order ID",
        "Side",
        "Quantity",
        "Price",
        "Volume",
        "Fee",
        "Rebate",
        "Total",
        "Taker",
    ],
    worksheet_name="HitBTC T",
    all_handler=parse_hitbtc_trades_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "HitBTC Trades",
    [
        "Email",
        "Date (UTC)",
        "Instrument",
        "Trade ID",
        "Order ID",
        "Side",
        "Quantity",
        "Price",
        "Volume",
        "Fee",
        "Rebate",
        "Total",
    ],
    worksheet_name="HitBTC T",
    all_handler=parse_hitbtc_trades_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "HitBTC Trades",
    [
        "Date (UTC)",
        "Instrument",
        "Trade ID",
        "Order ID",
        "Side",
        "Quantity",
        "Price",
        "Volume",
        "Fee",
        "Rebate",
        "Total",
    ],
    worksheet_name="HitBTC T",
    row_handler=parse_hitbtc_trades_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "HitBTC Deposits/Withdrawals",
    [
        "Email",
        "Date (UTC)",
        "Operation id",
        "Type",
        "Amount",
        "Transaction hash",
        "Main account balance",
        "Currency",
    ],
    worksheet_name="HitBTC D,W",
    row_handler=parse_hitbtc_deposits_withdrawals_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "HitBTC Deposits/Withdrawals",
    [
        "Date (UTC)",
        "Operation id",
        "Type",
        "Amount",
        "Transaction Hash",
        "Main account balance",
    ],
    worksheet_name="HitBTC D,W",
    row_handler=parse_hitbtc_deposits_withdrawals_v1,
)
