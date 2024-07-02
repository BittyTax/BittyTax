# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import sys
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from colorama import Fore
from typing_extensions import Dict, List, Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "BlockFi"


def parse_blockfi(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    tx_times: Dict[datetime, List["DataRow"]] = {}
    for dr in data_rows:
        if dr.row_dict["Confirmed At"]:
            dr.timestamp = DataParser.parse_timestamp(dr.row_dict["Confirmed At"])
            if dr.timestamp in tx_times:
                tx_times[dr.timestamp].append(dr)
            else:
                tx_times[dr.timestamp] = [dr]

    for data_row in data_rows:
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
            _parse_blockfi_row(tx_times, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_blockfi_row(
    tx_times: Dict[datetime, List["DataRow"]], parser: DataParser, data_row: "DataRow"
) -> None:
    row_dict = data_row.row_dict

    if not data_row.row_dict["Confirmed At"]:
        # Skip unconfirmed
        return

    if row_dict["Transaction Type"] in (
        "Deposit",
        "Wire Deposit",
        "Ach Deposit",
        "ACH Deposit",
        "Crypto Transfer",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Cryptocurrency"],
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] in (
        "Withdrawal",
        "Wire Withdrawal",
        "Ach Withdrawal",
        "ACH Withdrawal",
    ):
        fee_row = [
            dr
            for dr in tx_times[data_row.timestamp]
            if dr.row_dict["Transaction Type"] == "Withdrawal Fee"
            and dr.row_dict["Cryptocurrency"] == row_dict["Cryptocurrency"]
            and not dr.parsed
        ]
        if fee_row:
            fee_row[0].parsed = True

        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=row_dict["Cryptocurrency"],
            fee_quantity=abs(Decimal(fee_row[0].row_dict["Amount"])) if fee_row else None,
            fee_asset=fee_row[0].row_dict["Cryptocurrency"] if fee_row else "",
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "Withdrawal Fee":
        # Skip handled by Withdrawal
        return
    elif row_dict["Transaction Type"] == "Interest Payment":
        data_row.t_record = TransactionOutRecord(
            TrType.INTEREST,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Cryptocurrency"],
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "Referral Bonus":
        data_row.t_record = TransactionOutRecord(
            TrType.REFERRAL,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Cryptocurrency"],
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "Bonus Payment":
        data_row.t_record = TransactionOutRecord(
            TrType.AIRDROP,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Cryptocurrency"],
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "Cc Rewards Redemption":
        data_row.t_record = TransactionOutRecord(
            TrType.CASHBACK,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Cryptocurrency"],
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "Trade":
        t_rows = [
            dr
            for dr in tx_times[data_row.timestamp]
            if dr.row_dict["Transaction Type"] == row_dict["Transaction Type"] and not dr.parsed
        ]
        _make_trade(t_rows)
    elif row_dict["Transaction Type"] == "BIA Withdraw":
        # Skip internal transfers
        return
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Transaction Type"),
            "Transaction Type",
            row_dict["Transaction Type"],
        )


def _make_trade(t_rows: List["DataRow"]) -> None:
    buy_quantity = sell_quantity = None
    buy_asset = sell_asset = ""
    trade_row = None

    for data_row in t_rows:
        row_dict = data_row.row_dict

        if Decimal(row_dict["Amount"]) > 0:
            if buy_quantity is None:
                buy_quantity = Decimal(row_dict["Amount"])
                buy_asset = row_dict["Cryptocurrency"]
                data_row.parsed = True

        if Decimal(row_dict["Amount"]) <= 0:
            if sell_quantity is None:
                sell_quantity = abs(Decimal(row_dict["Amount"]))
                sell_asset = row_dict["Cryptocurrency"]
                data_row.parsed = True

        if not trade_row:
            trade_row = data_row

        if buy_quantity and sell_quantity:
            break

    if trade_row:
        trade_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            trade_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            wallet=WALLET,
        )


def parse_blockfi_trades(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    data_row.t_record = TransactionOutRecord(
        TrType.TRADE,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Buy Quantity"]),
        buy_asset=row_dict["Buy Currency"].upper(),
        sell_quantity=abs(Decimal(row_dict["Sold Quantity"])),
        sell_asset=row_dict["Sold Currency"].upper(),
        wallet=WALLET,
    )


DataParser(
    ParserType.SAVINGS,
    "BlockFi",
    [
        "Cryptocurrency",
        "Amount",
        "Transaction Type",
        "Exchange Rate Per Coin (USD)",
        "Confirmed At",
    ],
    worksheet_name="BlockFi",
    all_handler=parse_blockfi,
)

DataParser(
    ParserType.SAVINGS,
    "BlockFi",
    ["Cryptocurrency", "Amount", "Transaction Type", "Confirmed At"],
    worksheet_name="BlockFi",
    all_handler=parse_blockfi,
)

DataParser(
    ParserType.SAVINGS,
    "BlockFi Trades",
    [
        "Trade ID",
        "Date",
        "Buy Quantity",
        "Buy Currency",
        "Sold Quantity",
        "Sold Currency",
        "Rate Amount",
        "Rate Currency",
        "Type",
        "Frequency",
        "Destination",
    ],
    worksheet_name="BlockFi T",
    row_handler=parse_blockfi_trades,
)

DataParser(
    ParserType.SAVINGS,
    "BlockFi Trades",
    [
        "Trade ID",
        "Date",
        "Buy Quantity",
        "Buy Currency",
        "Sold Quantity",
        "Sold Currency",
        "Rate Amount",
        "Rate Currency",
        "Type",
    ],
    worksheet_name="BlockFi T",
    row_handler=parse_blockfi_trades,
)
