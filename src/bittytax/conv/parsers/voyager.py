# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Voyager"


def parse_voyager_v2(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    internal_ids: Dict[str, List["DataRow"]] = {}
    platform_ids: Dict[str, List["DataRow"]] = {}
    for dr in data_rows:
        dr.timestamp = DataParser.parse_timestamp(dr.row_dict["Timestamp (UTC)"])
        if dr.row_dict["Internal Id"] in internal_ids:
            internal_ids[dr.row_dict["Internal Id"]].append(dr)
        else:
            internal_ids[dr.row_dict["Internal Id"]] = [dr]

        if dr.row_dict["Platform Id"] in platform_ids:
            platform_ids[dr.row_dict["Platform Id"]].append(dr)
        else:
            platform_ids[dr.row_dict["Platform Id"]] = [dr]

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
            _parse_voyager_v2_row(internal_ids, platform_ids, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_voyager_v2_row(
    internal_ids: Dict[str, List["DataRow"]],
    platform_ids: Dict[str, List["DataRow"]],
    parser: DataParser,
    data_row: "DataRow",
) -> None:
    row_dict = data_row.row_dict

    if row_dict["Type"] == "Deposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Withdrawal":
        fee_quantity, fee_asset = _get_fee(platform_ids, row_dict["Platform Id"])

        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=row_dict["Asset"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Interest Income":
        data_row.t_record = TransactionOutRecord(
            TrType.INTEREST,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Income":
        data_row.t_record = TransactionOutRecord(
            TrType.INCOME,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    elif row_dict["Type"] in ("Fiat Sell", "Fiat Buy", "Bankruptcy Liquidation"):
        _make_trade(internal_ids[row_dict["Internal Id"]])
    elif row_dict["Type"] == "Bankruptcy Recovery":
        _make_recovery(internal_ids[row_dict["Internal Id"]], data_row)
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _get_fee(
    platform_ids: Dict[str, List["DataRow"]], platform_id: str
) -> Tuple[Optional[Decimal], str]:
    fees = platform_ids.get(f"{platform_id}F", [])

    if len(fees) == 1:
        fees[0].parsed = True
        return abs(Decimal(fees[0].row_dict["Amount"])), fees[0].row_dict["Asset"]
    return None, ""


def _make_trade(trade_rows: List["DataRow"]) -> None:
    buy_quantity = sell_quantity = None
    buy_asset = sell_asset = ""
    trade_row = None

    for data_row in trade_rows:
        row_dict = data_row.row_dict

        if Decimal(row_dict["Amount"]) >= 0:
            if buy_quantity is None:
                buy_quantity = Decimal(row_dict["Amount"])
                buy_asset = row_dict["Asset"]
                data_row.parsed = True

        if Decimal(row_dict["Amount"]) < 0:
            if sell_quantity is None:
                sell_quantity = abs(Decimal(row_dict["Amount"]))
                sell_asset = row_dict["Asset"]
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


def _make_recovery(recovery_rows: List["DataRow"], data_row: "DataRow") -> None:
    amount = None
    asset = ""

    for dr in recovery_rows:
        dr.parsed = True
        row_dict = dr.row_dict

        if not asset:
            asset = row_dict["Asset"]
        elif asset != row_dict["Asset"]:
            raise RuntimeError("Unexpected Asset")

        if amount is None:
            amount = Decimal(row_dict["Amount"])
        else:
            amount += Decimal(row_dict["Amount"])  # type: ignore[unreachable]

    if amount:
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(0),
            buy_asset=config.ccy,
            sell_quantity=abs(amount),
            sell_asset=asset,
            wallet=WALLET,
        )


def parse_voyager_v1(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["transaction_date"])
    value = DataParser.convert_currency(Decimal(row_dict["net_amount"]), "USD", data_row.timestamp)

    if row_dict["transaction_direction"] == "deposit":
        if row_dict["transaction_type"] == "REWARD":
            t_type = TrType.REFERRAL
        else:
            t_type = TrType.DEPOSIT

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["quantity"]),
            buy_asset=row_dict["base_asset"],
            buy_value=value,
            wallet=WALLET,
        )
    elif row_dict["transaction_direction"] == "withdrawal":
        if row_dict["transaction_type"] == "FEE":
            data_row.t_record = TransactionOutRecord(
                TrType.SPEND,
                data_row.timestamp,
                sell_quantity=Decimal(0),
                sell_asset=row_dict["base_asset"],
                fee_quantity=Decimal(row_dict["quantity"]),
                fee_asset=row_dict["base_asset"],
                fee_value=value,
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["quantity"]),
                sell_asset=row_dict["base_asset"],
                sell_value=value,
                wallet=WALLET,
            )
    elif row_dict["transaction_direction"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["quantity"]),
            buy_asset=row_dict["base_asset"],
            buy_value=value,
            sell_quantity=Decimal(row_dict["net_amount"]),
            sell_asset=row_dict["quote_asset"],
            sell_value=value,
            wallet=WALLET,
        )
    elif row_dict["transaction_direction"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["net_amount"]),
            buy_asset=row_dict["quote_asset"],
            buy_value=value,
            sell_quantity=Decimal(row_dict["quantity"]),
            sell_asset=row_dict["base_asset"],
            sell_value=value,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("transaction_direction"),
            "transaction_direction",
            row_dict["transaction_direction"],
        )


DataParser(
    ParserType.EXCHANGE,
    "Voyager",
    [
        "Timestamp (UTC)",
        "Type",
        "Internal Id",
        "Platform",
        "Platform Id",
        "Blockchain Id",
        "Record Type",
        "Asset",
        "Amount",
        "Description",
    ],
    worksheet_name="Voyager",
    all_handler=parse_voyager_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "Voyager",
    [
        "transaction_date",
        "transaction_id",
        "transaction_direction",
        "transaction_type",
        "base_asset",
        "quote_asset",
        "quantity",
        "net_amount",
        "price",
    ],
    worksheet_name="Voyager",
    row_handler=parse_voyager_v1,
)
