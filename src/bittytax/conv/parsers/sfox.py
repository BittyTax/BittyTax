# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2025

import sys
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "sFOX"


def parse_sfox_transactions(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    tx_times: Dict[datetime, List["DataRow"]] = {}

    for dr in data_rows:
        dr.timestamp = DataParser.parse_timestamp(dr.row_dict["Date"])
        dr.tx_raw = TxRawPos(parser.in_header.index("Transaction Hash"))
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
            _parse_sfox_transactions_row(tx_times, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_sfox_transactions_row(
    tx_times: Dict[datetime, List["DataRow"]], parser: DataParser, data_row: "DataRow"
) -> None:
    row_dict = data_row.row_dict

    if row_dict["Action"] in ("Buy", "Sell"):
        rows = [
            dr
            for dr in tx_times[data_row.timestamp]
            if dr.row_dict["Action"] == row_dict["Action"] and not dr.parsed
        ]
        _make_trade(rows)
    elif row_dict["Action"] == "Deposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]),
            buy_asset=row_dict["Source Currency"].upper(),
            wallet=WALLET,
        )
    elif row_dict["Action"] == "Charge":
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Quantity"])),
            sell_asset=row_dict["Source Currency"].upper(),
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Action"), "Action", row_dict["Action"])


def _make_trade(op_rows: List["DataRow"]) -> None:
    buy_quantity = sell_quantity = fee_quantity = None
    buy_asset = sell_asset = fee_asset = ""
    trade_row = None

    for data_row in op_rows:
        row_dict = data_row.row_dict

        if Decimal(row_dict["Quantity"]) > 0:
            if buy_quantity is None:
                buy_quantity = Decimal(row_dict["Quantity"])
                buy_asset = row_dict["Source Currency"].upper()
                data_row.parsed = True

        if Decimal(row_dict["Quantity"]) <= 0:
            if sell_quantity is None:
                sell_quantity = abs(Decimal(row_dict["Quantity"]))
                sell_asset = row_dict["Source Currency"].upper()
                data_row.parsed = True

        if fee_quantity is None:
            fee_quantity = Decimal(row_dict["Fees"])
            fee_asset = "USD"

        if not trade_row:
            trade_row = data_row

        if buy_quantity and sell_quantity and fee_quantity:
            break

    if trade_row:
        trade_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            trade_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )


def parse_sfox_orders(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["OrderDate"][:-38])

    fees = DataParser.convert_currency(row_dict["FeesUSD"], "USD", data_row.timestamp)
    principal_amount = DataParser.convert_currency(
        row_dict["PrincipalAmountUSD"], "USD", data_row.timestamp
    )

    if row_dict["Action"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]),
            buy_asset=row_dict["Asset"].upper(),
            sell_quantity=principal_amount,
            sell_asset=config.ccy,
            fee_quantity=fees,
            fee_asset=config.ccy,
            wallet=WALLET,
        )
    elif row_dict["Action"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=principal_amount,
            buy_asset=config.ccy,
            sell_quantity=Decimal(row_dict["Quantity"]),
            sell_asset=row_dict["Asset"].upper(),
            fee_quantity=fees,
            fee_asset=config.ccy,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Action"), "Action", row_dict["Action"])


DataParser(
    ParserType.EXCHANGE,
    "sFOX",
    [
        "id",
        "Transaction Hash",
        "Date",
        "Action",
        "Quantity",
        "Target Currency",
        "Price",
        "Source Currency",
        "Fees",
        "Memo",
        "Status",
        "Balance",
        "Trader",
        "Timestamp",
    ],
    worksheet_name="sFOX Transactions",
    all_handler=parse_sfox_transactions,
)

DataParser(
    ParserType.EXCHANGE,
    "sFOX",
    [
        "OrderId",
        "OrderDate",
        "AddedByUserEmail",
        "Action",
        "AssetPair",
        "Quantity",
        "Asset",
        "AssetUSDFXRate",
        "UnitPrice",
        "PriceCurrency",
        "PrincipalAmount",
        "PriceUSDFXRate",
        "PrincipalAmountUSD",
        "Fees",
        "FeesUSD",
        "Total",
        "TotalUSD",
    ],
    worksheet_name="sFOX Orders",
    row_handler=parse_sfox_orders,
)
