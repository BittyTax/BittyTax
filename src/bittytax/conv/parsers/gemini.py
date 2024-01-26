# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import sys
from decimal import Decimal
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

WALLET = "Gemini"

QUOTE_ASSETS = [
    "BCH",
    "BTC",
    "DAI",
    "ETH",
    "EUR",
    "FIL",
    "GBP",
    "GUSD",
    "LTC",
    "SGD",
    "USD",
    "USDT",
]

TRADINGPAIR_TO_QUOTE_ASSET = {
    "PAXGUSD": "USD",
}


def parse_gemini(
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

        if not data_row.row_dict["Date"]:
            # Delete blank row with totals
            del data_rows[row_index]
            continue

        try:
            _parse_gemini_row(parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_gemini_row(parser: DataParser, data_row: "DataRow") -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["Type"] in ("Credit", "Debit"):
        asset = row_dict["Symbol"]
        if row_dict[f"Fee ({asset}) {asset}"]:
            fee_quantity = abs(Decimal(row_dict[f"Fee ({asset}) {asset}"]))
            fee_asset = asset
        else:
            fee_quantity = None
            fee_asset = ""

        if row_dict["Type"] == "Credit":
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict[f"{asset} Amount {asset}"]),
                buy_asset=asset,
                fee_quantity=fee_quantity,
                fee_asset=fee_asset,
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict[f"{asset} Amount {asset}"])),
                sell_asset=asset,
                fee_quantity=fee_quantity,
                fee_asset=fee_asset,
                wallet=WALLET,
            )
    elif row_dict["Type"] in ("Buy", "Sell"):
        base_asset, quote_asset = _split_trading_pair(row_dict["Symbol"])
        if base_asset is None or quote_asset is None:
            raise UnexpectedTradingPairError(
                parser.in_header.index("Symbol"), "Symbol", row_dict["Symbol"]
            )

        base_quantity = abs(Decimal(row_dict[f"{base_asset} Amount {base_asset}"]))
        quote_quantity = abs(Decimal(row_dict[f"{quote_asset} Amount {quote_asset}"]))

        if row_dict[f"Fee ({quote_asset}) {quote_asset}"]:
            fee_quantity = abs(Decimal(row_dict[f"Fee ({quote_asset}) {quote_asset}"]))
            fee_asset = quote_asset
        else:
            fee_quantity = None
            fee_asset = ""

        if row_dict["Type"] == "Buy":
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=base_quantity,
                buy_asset=base_asset,
                sell_quantity=quote_quantity,
                sell_asset=quote_asset,
                fee_quantity=fee_quantity,
                fee_asset=fee_asset,
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=quote_quantity,
                buy_asset=quote_asset,
                sell_quantity=base_quantity,
                sell_asset=base_asset,
                fee_quantity=fee_quantity,
                fee_asset=fee_asset,
                wallet=WALLET,
            )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _split_trading_pair(symbol: str) -> Tuple[Optional[str], Optional[str]]:
    if symbol.endswith("PERP"):
        # Futures are not supported
        return None, None

    if symbol in TRADINGPAIR_TO_QUOTE_ASSET:
        quote_asset = TRADINGPAIR_TO_QUOTE_ASSET[symbol]
        base_asset = symbol[: -len(quote_asset)]
        return base_asset, quote_asset

    for quote_asset in QUOTE_ASSETS:
        if symbol.endswith(quote_asset):
            base_asset = symbol[: -len(quote_asset)]
            return base_asset, quote_asset

    return None, None


DataParser(
    ParserType.EXCHANGE,
    "Gemini",
    [
        "Date",
        "Time (UTC)",
        "Type",
        "Symbol",
        "Specification",
        "Liquidity Indicator",
        "Trading Fee Rate (bps)",
        "Trade ID",
        "Order ID",
        "Order Date",
        "Order Time",
        "Client Order ID",
        "API Session",
        "Tx Hash",
        "Deposit Destination",
        "Deposit Tx Output",
        "Withdrawal Destination",
        "Withdrawal Tx Output",
    ],
    header_fixed=False,
    worksheet_name="Gemini",
    all_handler=parse_gemini,
)
