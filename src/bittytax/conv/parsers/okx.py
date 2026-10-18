# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Literal

import dateutil.tz
from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedContentError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "OKX"
TZ_INFOS = {"CST": dateutil.tz.gettz("Asia/Shanghai")}
BOM = "\ufeff"  # pylint: disable=anomalous-unicode-escape-in-string


def parse_okx_trades_v2(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    ids: Dict[str, List["DataRow"]] = {}
    orders: Dict[str, List["DataRow"]] = {}

    for dr in data_rows:
        if dr.row_dict.get(BOM + "id"):
            dr.row_dict["id"] = dr.row_dict[BOM + "id"]

        if dr.row_dict["id"] in ids:
            ids[dr.row_dict["id"]].append(dr)
        else:
            ids[dr.row_dict["id"]] = [dr]

        if dr.row_dict["Order id"] in orders:
            orders[dr.row_dict["Order id"]].append(dr)
        else:
            orders[dr.row_dict["Order id"]] = [dr]

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
            _parse_okx_trades_v2_row(ids, orders, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_okx_trades_v2_row(
    ids: Dict[str, List["DataRow"]],
    orders: Dict[str, List["DataRow"]],
    parser: DataParser,
    data_row: "DataRow",
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])
    data_row.parsed = True

    if row_dict["Trade Type"] == "Spot":
        if row_dict["Type"] in ("Buy", "Sell"):
            if not _make_trade(ids[row_dict["id"]], data_row):
                # Some trades don't have matching id's, try matching by Order id instead
                if not _make_trade(orders[row_dict["Order id"]], data_row):
                    raise UnexpectedContentError(0, "id", row_dict["id"])
        else:
            raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])
    elif row_dict["Trade Type"] == "Transfer":
        # Skip internal transfers
        return
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Trade Type"), "Trade Type", row_dict["Trade Type"]
        )


def _make_trade(ids: List["DataRow"], data_row: "DataRow") -> bool:
    buy_rows = [dr for dr in ids if dr.row_dict["Type"] == "Buy"]
    sell_rows = [dr for dr in ids if dr.row_dict["Type"] == "Sell"]

    if len(buy_rows) == 1 and len(sell_rows) == 1:
        if data_row == buy_rows[0]:
            sell_rows[0].timestamp = DataParser.parse_timestamp(sell_rows[0].row_dict["Time"])
            sell_rows[0].parsed = True
        else:
            buy_rows[0].timestamp = DataParser.parse_timestamp(buy_rows[0].row_dict["Time"])
            buy_rows[0].parsed = True

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(buy_rows[0].row_dict["Amount"]),
            buy_asset=buy_rows[0].row_dict["Unit"],
            sell_quantity=Decimal(sell_rows[0].row_dict["Amount"]),
            sell_asset=sell_rows[0].row_dict["Unit"],
            fee_quantity=abs(Decimal(buy_rows[0].row_dict["Fee"])),
            fee_asset=buy_rows[0].row_dict["Unit"],
            wallet=WALLET,
        )
        return True

    return False


def parse_okx_trades_v1(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    for buy_row, sell_row in zip(data_rows[0::2], data_rows[1::2]):
        try:
            if config.debug:
                if parser.in_header_row_num is None:
                    raise RuntimeError("Missing in_header_row_num")

                sys.stderr.write(
                    f"{Fore.YELLOW}conv: "
                    f"row[{parser.in_header_row_num + buy_row.line_num}] {buy_row}\n"
                )
                sys.stderr.write(
                    f"{Fore.YELLOW}conv: "
                    f"row[{parser.in_header_row_num + sell_row.line_num}] {sell_row}\n"
                )

            _parse_okx_trades_v1_row(buy_row, sell_row, parser)
        except DataRowError as e:
            buy_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            buy_row.failure = e


def _parse_okx_trades_v1_row(buy_row: "DataRow", sell_row: "DataRow", parser: DataParser) -> None:
    buy_row.timestamp = DataParser.parse_timestamp(buy_row.row_dict["time"], tzinfos=TZ_INFOS)
    sell_row.timestamp = DataParser.parse_timestamp(sell_row.row_dict["time"], tzinfos=TZ_INFOS)

    if buy_row.row_dict["type"] == "buy" and sell_row.row_dict["type"] == "sell":
        buy_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            buy_row.timestamp,
            buy_quantity=Decimal(buy_row.row_dict["size"]),
            buy_asset=buy_row.row_dict["currency"],
            sell_quantity=abs(Decimal(sell_row.row_dict["size"])),
            sell_asset=sell_row.row_dict["currency"],
            fee_quantity=abs(Decimal(buy_row.row_dict["fee"])),
            fee_asset=buy_row.row_dict["currency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", buy_row.row_dict["type"])


def parse_okx_funding(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    if row_dict["Type"] == "Deposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Symbol"],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Symbol"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=row_dict["Symbol"],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Symbol"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Staking Yield":
        data_row.t_record = TransactionOutRecord(
            TrType.STAKING_REWARD,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Symbol"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Fee rebate":
        data_row.t_record = TransactionOutRecord(
            TrType.FEE_REBATE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Symbol"],
            wallet=WALLET,
        )
    elif row_dict["Type"] in (
        "Stake",
        "Redeem staking",
        "Savings subscription",
        "Savings redemption",
        "From unified trading account",
        "To unified trading account",
    ):
        # Skip not taxable events
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])

__founding_cache = {}
def parse_okx_funding_v2026_09(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
   
    row_dict = data_row.row_dict

    # Skip metadata row
    if "Account Type" in row_dict or "Time Zone" in row_dict:
        return
    if "Type" not in row_dict or not row_dict["Type"]:
        return
    if row_dict["Type"] == "Type":
        return
    if "Time" not in row_dict or not row_dict["Time"]:
        return

    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    symbol = row_dict["Symbol"]
    amount = Decimal(row_dict["Amount"])
    tx_type = row_dict["Type"]

    if tx_type == "Convert":
        tx_key = data_row.timestamp
        if tx_key not in __founding_cache:
            __founding_cache[tx_key] = data_row
            return
        else:
            other_row = __founding_cache.pop(tx_key)
            if amount < 0:
                # Sold asset, received USDT
                sell_quantity = abs(amount)
                sell_asset = symbol
                buy_asset = other_row.row_dict["Symbol"]
                buy_quantity = Decimal(str(other_row.row_dict["Amount"]))
            else:
                # buy asset
                sell_quantity = Decimal(str(other_row.row_dict["Amount"]))
                sell_asset = other_row.row_dict["Symbol"]
                buy_asset = symbol
                buy_quantity = abs(amount)
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=abs(buy_quantity),
            buy_asset=buy_asset,
            sell_quantity=abs(sell_quantity),
            sell_asset=sell_asset,
            fee_quantity=Decimal(0),
            fee_asset=buy_asset,
            wallet=WALLET,
        )

    elif tx_type == "Deposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=symbol,
            wallet=WALLET,
        )

    elif tx_type == "Withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(amount),
            sell_asset=symbol,
            wallet=WALLET,
        )

    elif tx_type == "Untradable asset collection":
        # Token migration/dust collection
        # Only process the negative row (the one removing the old token)
        if amount < 0:
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=abs(amount),
                buy_asset=symbol,  # The new token (e.g., A for Vaulta)
                sell_quantity=abs(amount),
                sell_asset=symbol,  # The old token (e.g., EOS)
                fee_quantity=Decimal(0),
                fee_asset="USDT",
                wallet=WALLET,
            )
        # Positive row (new token received) is skipped to avoid duplication
        return
    elif tx_type in (
            "Received",
            "Stake",
            "Redeem staking",
            "Savings subscription",
            "Savings redemption",
            "From unified trading account",
            "To unified trading account",
            "Received from main account",
            "Transferred to sub-account",
    ):
        # Skip not taxable events (including internal transfers)
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", tx_type)


__trade_cache = {}


def parse_okx_spot_trades_v2026_09(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:

    def pop_order(opposite_order: tuple[int, Literal["Buy", "Sell"]]) -> "DataRow|None":
        if key := next((key for key in __trade_cache if opposite_order in key), None):
            row = __trade_cache.pop(key)
            if config.debug:
                sys.stderr.write(
                    f"{Fore.YELLOW}conv: "
                    f" cache pop  {row}\n"
                )
            return row
        return None

    def push_order(tx_id, order: tuple[int, str], row: "DataRow"):
        if config.debug:
            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f" cache push {row}\n"
            )
        __trade_cache[(tx_id, order)] = row

    # 1. Clean the BOM hidden markers from keys and values
    cleaned_dict = {}
    for k, v in list(data_row.row_dict.items()):
        clean_key = k.replace(BOM, "").strip()
        clean_val = str(v).replace(BOM, "").strip() if isinstance(v, str) else v
        cleaned_dict[clean_key] = clean_val
        cleaned_dict[clean_key] = clean_val
    data_row.row_dict = cleaned_dict

    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    # We only care about Spot trades (ignore derivative changes or internal sub-transfers)
    if row_dict["Trade Type"] != "Spot":
        data_row.parsed = True
        return

    _ = row_dict["id"]
    order_id = row_dict["Order id"]
    action = row_dict["Action"]
    pair_parts = str(row_dict["Symbol"]).split("-")
    base_asset = pair_parts[0]
    quote_asset = pair_parts[1] if len(pair_parts) > 1 else "USDT"
    convert_asset = (
        pair_parts[2] if len(pair_parts) > 2
                         and pair_parts[2] == "CONVERT"
                         and action == ""
        else None
    )

    # Sort out which row is the 'Buy' side and which is the 'Sell' side
    if action == "Buy" and row_dict["Trading Unit"] == row_dict["Fee Unit"] == base_asset:
        # buy order/buy base side
        if (other_row:= pop_order((order_id, "Sell"))) is not None:
            buy_row = data_row
            sell_row = other_row
        else:
            push_order(_, (order_id, action), data_row)
            return
    elif action == "Sell" and row_dict["Trading Unit"] == base_asset and row_dict["Fee Unit"] == quote_asset:
        # buy order/sell quote side
        if (other_row:=pop_order((order_id, "Buy"))) is not None:
            buy_row = other_row
            sell_row = data_row
        else:
            push_order(_, (order_id, action), data_row)
            return
    elif action and row_dict["Trading Unit"] == row_dict["Fee Unit"] == base_asset:
        # sell order/sell base side
        if (other_row := pop_order((order_id, "Buy"))) is not None:
            buy_row = other_row
            sell_row = data_row
        else:
            push_order(_, (order_id, action), data_row)
            return
    elif action == "Buy" and row_dict["Trading Unit"] == base_asset and row_dict["Fee Unit"] == quote_asset:
        # sell order/buy quote side
        if (other_row := pop_order((order_id, "Sell"))) is not None:
            buy_row = data_row
            sell_row = other_row
        else:
            push_order(_, (order_id, action), data_row)
            return
    elif convert_asset is not None:
        if row_dict["Trading Unit"] == base_asset and row_dict["Fee Unit"] == quote_asset:

            # buy order/buy quote side
            if (other_row := pop_order((order_id, "Sell"))) is not None:
                buy_row = data_row
                sell_row = other_row
            else:
                push_order(_, (order_id, "Buy"), data_row)
                return
        elif row_dict["Trading Unit"] == row_dict["Fee Unit"] == base_asset:
            # sell order/sell base side
            if (other_row := pop_order((order_id, "Buy"))) is not None:
                buy_row = other_row
                sell_row = data_row
            else:
                push_order(_, (order_id, "Sell"), data_row)
                return
        else:
            raise UnexpectedContentError(0, "", row_dict["id"])

    else:
        raise UnexpectedContentError(0, "", row_dict["id"])

    # Mark both rows as fully parsed so BittyTax knows they are resolved
    data_row.parsed = True
    other_row.parsed = True
    fee_asset = buy_row.row_dict.get("Fee Unit", base_asset)
    fee_amt = abs(Decimal(buy_row.row_dict.get("Fee", 0)))

    # Construct a singular, unified Trade Output record
    data_row.t_record = TransactionOutRecord(
        TrType.TRADE,
        data_row.timestamp,
        buy_quantity=Decimal(buy_row.row_dict["Amount"]),
        buy_asset=buy_row.row_dict["Fee Unit"],
        sell_quantity=Decimal(sell_row.row_dict["Amount"]),
        sell_asset=sell_row.row_dict["Fee Unit"],
        fee_quantity=fee_amt,
        fee_asset=fee_asset,
        wallet=WALLET,
    )
    return


DataParser(
    ParserType.EXCHANGE,
    "OKX Trades",
    [
        lambda h: h in ("id", BOM + "id", h),
        "Order id",
        "Time",
        "Trade Type",
        "Instrument",
        "Type",
        "Amount",
        "Unit",
        "PL",
        "Fee",
        "Position Change",
        "Position Balance",
        "Balance Change",
        "Balance",
        "Unit",
    ],
    worksheet_name="OKX T",
    all_handler=parse_okx_trades_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "OKX Trades",
    ["time", "type", "size", "balance", "fee", "currency"],
    worksheet_name="OKX T",
    all_handler=parse_okx_trades_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "OKX Funding",
    [
        lambda h: h in ("id", BOM + "id", h),
        "Time",
        "Type",
        "Amount",
        "Before Balance",
        "After Balance",
        "Fee",
        "Symbol",
    ],
    worksheet_name="OKX F",
    row_handler=parse_okx_funding,
)

DataParser(
    ParserType.EXCHANGE,
    "OKX Funding",
    [
        lambda h: h in ("id", BOM + "id", h),
        "",
        "Time",
        "Type",
        "Amount",
        "Before Balance",
        "After Balance",
        "Fee",
        "Symbol",
    ],
    worksheet_name="OKX F",
    row_handler=parse_okx_funding,
)

DataParser(
    ParserType.EXCHANGE,
    "OKX Funding History v2026 Sep",
    [
        lambda h: h in ("id", BOM + "id"),
        lambda h: h in ("Time", BOM + "Time"),
        lambda h: h in ("Type", BOM + "Type"),
        lambda h: h in ("Amount", BOM + "Amount"),
        lambda h: h in ("Before Balance", BOM + "Before Balance"),
        lambda h: h in ("After Balance", BOM + "After Balance"),
        lambda h: h in ("Symbol", BOM + "Symbol"),
        lambda h: h in ("Amount-USD", BOM + "Amount-USD"),

    ],
    worksheet_name="OKX F",
    row_handler=parse_okx_funding_v2026_09,
)

DataParser(
    ParserType.EXCHANGE,
    "OKX Spot grouped Transaction History v2026 Sep",
    [
        lambda h: h in ("id", BOM + "id", h),
        "Order id",
        "Time",
        "Trade Type",
        "Symbol",
        "Action",
        "Amount",
        "Trading Unit",
        "Filled Price",
        "PnL",
        "Fee",
        "Fee Unit",
        "Position Change",
        "Position Balance",
        "Balance Change",
        "Balance",
        "Balance Unit",
        "Filled_price-USD",
        "Pnl-USD",
        "Fee-USD",
        "Balance-USD",
        "Balance_change-USD"


    ],
    worksheet_name="OKX Trades",
    row_handler=parse_okx_spot_trades_v2026_09,
)
