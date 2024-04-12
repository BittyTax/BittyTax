# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List

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
            TrType.STAKING,
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
