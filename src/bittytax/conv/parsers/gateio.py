# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Gate.io"


def parse_gateio(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    tx_ids: Dict[str, List["DataRow"]] = {}
    for dr in data_rows:
        if dr.row_dict["action_data"] in tx_ids:
            tx_ids[dr.row_dict["action_data"]].append(dr)
        else:
            tx_ids[dr.row_dict["action_data"]] = [dr]

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
            _parse_gateio_row(tx_ids, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_gateio_row(
    tx_ids: Dict[str, List["DataRow"]], parser: DataParser, data_row: "DataRow"
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])

    if row_dict["action_desc"] == "Deposits":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["change_amount"]),
            buy_asset=row_dict["type"],
            wallet=WALLET,
        )
    elif row_dict["action_desc"] == "Withdrawals":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["change_amount"])),
            sell_asset=row_dict["type"],
            wallet=WALLET,
        )
    elif row_dict["action_desc"] == "Referral Superior Rebate":
        data_row.t_record = TransactionOutRecord(
            TrType.REFERRAL,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["change_amount"]),
            buy_asset=row_dict["type"],
            wallet=WALLET,
        )
    elif row_dict["action_desc"] == "Airdrop":
        if Decimal(row_dict["change_amount"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.AIRDROP,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["change_amount"]),
                buy_asset=row_dict["type"],
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.SPEND,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["change_amount"])),
                sell_asset=row_dict["type"],
                wallet=WALLET,
            )
    elif row_dict["action_desc"] == "HODL Interest":
        data_row.t_record = TransactionOutRecord(
            TrType.INTEREST,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["change_amount"]),
            buy_asset=row_dict["type"],
            wallet=WALLET,
        )
    elif row_dict["action_desc"] in ("Dust Swap-Small Balances Deducted", "Dust Swap-GT Added"):
        tx_rows = [dr for dr in tx_ids[row_dict["action_data"]] if not dr.parsed]
        _make_trade(tx_rows)
    elif row_dict["action_desc"] in ("Order Placed", "Order Filled", "Trading Fees"):
        tx_rows = [dr for dr in tx_ids[row_dict["action_data"]] if not dr.parsed]
        _make_trade_with_fee(tx_rows)
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("action_desc"), "action_desc", row_dict["action_desc"]
        )


def _make_trade(tx_rows: List["DataRow"], t_type: TrType = TrType.TRADE) -> None:
    buy_quantity = sell_quantity = None
    buy_asset = sell_asset = ""
    trade_row = None

    for data_row in tx_rows:
        row_dict = data_row.row_dict
        data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])

        if Decimal(row_dict["change_amount"]) > 0:
            if buy_quantity is None:
                buy_quantity = Decimal(row_dict["change_amount"])
                buy_asset = row_dict["type"]
                data_row.parsed = True

        if Decimal(row_dict["change_amount"]) <= 0:
            if sell_quantity is None:
                sell_quantity = abs(Decimal(row_dict["change_amount"]))
                sell_asset = row_dict["type"]
                data_row.parsed = True

        if not trade_row:
            trade_row = data_row

        if buy_quantity and sell_quantity:
            break

    if trade_row:
        if buy_quantity is None:
            buy_quantity = Decimal(0)
            buy_asset = config.ccy

        if sell_quantity is None:
            sell_quantity = Decimal(0)
            sell_asset = config.ccy

        trade_row.t_record = TransactionOutRecord(
            t_type,
            trade_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            wallet=WALLET,
        )


def _make_trade_with_fee(tx_rows: List["DataRow"]) -> None:
    buy_quantity = sell_quantity = fee_quantity = None
    buy_asset = sell_asset = fee_asset = ""
    trade_row = None

    for data_row in tx_rows:
        row_dict = data_row.row_dict
        data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])

        if Decimal(row_dict["change_amount"]) > 0:
            if buy_quantity is None:
                buy_quantity = Decimal(row_dict["change_amount"])
                buy_asset = row_dict["type"]
                data_row.parsed = True

        if Decimal(row_dict["change_amount"]) <= 0:
            if row_dict["action_desc"] == "Trading Fees":
                if fee_quantity is None:
                    fee_quantity = abs(Decimal(row_dict["change_amount"]))
                    fee_asset = row_dict["type"]
                    data_row.parsed = True
            else:
                if sell_quantity is None:
                    sell_quantity = abs(Decimal(row_dict["change_amount"]))
                    sell_asset = row_dict["type"]
                    data_row.parsed = True

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


DataParser(
    ParserType.EXCHANGE,
    "Gate.io",
    ["no", "time", "action_desc", "action_data", "type", "change_amount", "amount", "total"],
    worksheet_name="Gate.io",
    all_handler=parse_gateio,
)
