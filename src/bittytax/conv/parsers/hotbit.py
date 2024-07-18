# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import copy
import sys
from decimal import ROUND_DOWN, Decimal
from typing import TYPE_CHECKING, List, Optional, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTradingPairError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Hotbit"

QUOTE_ASSETS = [
    "ALGO",
    "ATOM",
    "AUDIO",
    "BCH",
    "BTC",
    "CHZ",
    "DOGE",
    "DYDX",
    "ENS",
    "ETC",
    "ETH",
    "FSN",
    "HOT",
    "ICP",
    "IMX",
    "KDA",
    "LEV",
    "LRC",
    "LTC",
    "MFT",
    "MINA",
    "NEAR",
    "NEXO",
    "NFT",
    "QNT",
    "QTUM",
    "RVN",
    "SHIB",
    "SLP",
    "SOL",
    "TFUEL",
    "THETA",
    "TRB",
    "TRX",
    "TWT",
    "UNI",
    "USD",
    "USDC",
    "USDT",
    "VET",
    "XEM",
    "XMR",
    "XRP",
    "nUSD",
    "vUSD",
]

PRECISION = Decimal("0.00000000")
MAKER_FEE = Decimal(0.0005)
TAKER_FEE = Decimal(0.002)


def parse_hotbit_orders_v3(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    _parse_hotbit_orders(data_rows, parser, type_str="Side", amount_str="Volume")


def parse_hotbit_orders_v2(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    _parse_hotbit_orders(data_rows, parser, type_str="Side", amount_str="Amount")


def parse_hotbit_orders_v1(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    _parse_hotbit_orders(data_rows, parser, type_str="Type", amount_str="Amount")


def _parse_hotbit_orders(
    data_rows: List["DataRow"], parser: DataParser, type_str: str, amount_str: str
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
            _parse_hotbit_orders_row(data_rows, parser, data_row, row_index, type_str, amount_str)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_hotbit_orders_row(
    data_rows: List["DataRow"],
    parser: DataParser,
    data_row: "DataRow",
    row_index: int,
    type_str: str,
    amount_str: str,
) -> None:
    if data_row.row[0] == "":
        return

    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])
    data_row.parsed = True

    # Have to re-calculate the total as it's incorrect for USDT trades
    total = Decimal(row_dict["Price"].split(" ")[0]) * Decimal(row_dict[amount_str].split(" ")[0])

    # Maker fees are a credit (+)
    if row_dict["Fee"][0] == "+":
        # Have to re-calculate the fee as rounding in datafile is incorrect
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []
        dup_data_row.t_record = TransactionOutRecord(
            TrType.FEE_REBATE,
            data_row.timestamp,
            buy_quantity=(total * MAKER_FEE).quantize(PRECISION, rounding=ROUND_DOWN),
            buy_asset=row_dict["Fee"].split(" ")[1],
            wallet=WALLET,
        )
        data_rows.insert(row_index + 1, dup_data_row)

        fee_quantity = None
        fee_asset = ""
    else:
        # Have to re-calculate the fee as rounding in datafile is incorrect
        fee_quantity = (total * TAKER_FEE).quantize(PRECISION, rounding=ROUND_DOWN)
        fee_asset = row_dict["Fee"].split(" ")[1]

    if row_dict[type_str] == "BUY":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict[amount_str].split(" ")[0]),
            buy_asset=row_dict["Pair"].split("/")[0],
            sell_quantity=total.quantize(PRECISION),
            sell_asset=row_dict["Pair"].split("/")[1],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict[type_str] == "SELL":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=total.quantize(PRECISION),
            buy_asset=row_dict["Pair"].split("/")[1],
            sell_quantity=Decimal(row_dict[amount_str].split(" ")[0]),
            sell_asset=row_dict["Pair"].split("/")[0],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index(type_str), type_str, row_dict[type_str])


def parse_hotbit_trades(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    for row_index, data_row in enumerate(data_rows):
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f" row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if data_row.parsed:
            continue

        try:
            _parse_hotbit_trades_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_hotbit_trades_row(
    data_rows: List["DataRow"], parser: DataParser, data_row: "DataRow", row_index: int
) -> None:
    row_dict = data_row.row_dict

    if "_" in row_dict["time"]:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["time"].replace("_", " "))
    else:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["time"], tz="Asia/Hong_Kong")
    data_row.parsed = True

    base_asset, quote_asset = _split_trading_pair(row_dict["market"])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(
            parser.in_header.index("market"), "market", row_dict["market"]
        )

    # Maker fees are negative
    if Decimal(row_dict["fee"]) < 0:
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []

        dup_data_row.t_record = TransactionOutRecord(
            TrType.FEE_REBATE,
            data_row.timestamp,
            buy_quantity=abs(Decimal(row_dict["fee"]).quantize(PRECISION)),
            buy_asset=quote_asset,
            wallet=WALLET,
        )
        data_rows.insert(row_index + 1, dup_data_row)

        fee_quantity = None
        fee_asset = ""
    else:
        fee_quantity = Decimal(row_dict["fee"]).quantize(PRECISION)
        fee_asset = quote_asset

    if row_dict["side"] == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount"]),
            buy_asset=base_asset,
            sell_quantity=Decimal(row_dict["deal"]).quantize(PRECISION),
            sell_asset=quote_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["side"] == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["deal"]).quantize(PRECISION),
            buy_asset=quote_asset,
            sell_quantity=Decimal(row_dict["amount"]),
            sell_asset=base_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("side"), "side", row_dict["side"])


def _split_trading_pair(market: str) -> Tuple[Optional[str], Optional[str]]:
    for quote_asset in sorted(QUOTE_ASSETS, reverse=True):
        if market.endswith(quote_asset):
            return market[: -len(quote_asset)], quote_asset

    return None, None


DataParser(
    ParserType.EXCHANGE,
    "Hotbit Trades",
    ["Date", "Pair", "Side", "Price", "Volume", "Fee", "Total"],
    worksheet_name="Hotbit T",
    all_handler=parse_hotbit_orders_v3,
)

DataParser(
    ParserType.EXCHANGE,
    "Hotbit Trades",
    ["Date", "Pair", "Side", "Price", "Amount", "Fee", "Total"],
    worksheet_name="Hotbit T",
    all_handler=parse_hotbit_orders_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "Hotbit Trades",
    ["Date", "Pair", "Type", "Price", "Amount", "Fee", "Total", "Export"],
    worksheet_name="Hotbit T",
    all_handler=parse_hotbit_orders_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "Hotbit Trades",
    ["time", "market", "side", "price", "amount", "deal", "fee"],
    worksheet_name="Hotbit T",
    all_handler=parse_hotbit_trades,
)

# Format provided by request from support
DataParser(
    ParserType.EXCHANGE,
    "Hotbit Trades",
    [
        "time",
        "user_id",
        "market",
        "side",
        "role",
        "price",
        "amount",
        "deal",
        "fee",
        "platform",
        "stock",
        "deal_stock",
    ],
    worksheet_name="Hotbit T",
    all_handler=parse_hotbit_trades,
)
