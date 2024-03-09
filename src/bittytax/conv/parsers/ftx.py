# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

import copy
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTradingPairError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "FTX"


def parse_ftx_deposits(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    _normalise_ftx_dict(row_dict)
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    if row_dict["Status"] not in ("complete", "confirmed"):
        return

    data_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount"]),
        buy_asset=row_dict["Coin"],
        wallet=WALLET,
    )


def parse_ftx_withdrawals(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    _normalise_ftx_dict(row_dict)
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    if row_dict["Fee"]:
        fee_quantity = Decimal(row_dict["Fee"])
        fee_asset = row_dict["Coin"]
    else:
        fee_quantity = None
        fee_asset = ""

    data_row.t_record = TransactionOutRecord(
        TrType.WITHDRAWAL,
        data_row.timestamp,
        sell_quantity=Decimal(row_dict["Amount"]),
        sell_asset=row_dict["Coin"],
        fee_quantity=fee_quantity,
        fee_asset=fee_asset,
        wallet=WALLET,
    )


def parse_ftx_trades(
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
            _parse_ftx_trades_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_ftx_trades_row(
    data_rows: List["DataRow"], parser: DataParser, data_row: "DataRow", row_index: int
) -> None:
    row_dict = data_row.row_dict
    _normalise_ftx_dict(row_dict)
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])
    data_row.parsed = True

    base_asset, quote_asset = _split_trading_pair(row_dict["Market"])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(
            parser.in_header.index("Market"), "Market", row_dict["Market"]
        )

    if Decimal(row_dict["Fee"]) < 0:
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []

        dup_data_row.t_record = TransactionOutRecord(
            TrType.FEE_REBATE,
            data_row.timestamp,
            buy_quantity=abs(Decimal(row_dict["Fee"])),
            buy_asset=row_dict["Fee Currency"],
            wallet=WALLET,
        )
        data_rows.insert(row_index + 1, dup_data_row)

        fee_quantity = None
        fee_asset = ""
    else:
        fee_quantity = Decimal(row_dict["Fee"])
        fee_asset = row_dict["Fee Currency"]

    if row_dict["Side"] == "buy":
        if Decimal(row_dict["Total"]) == 0:
            data_row.t_record = TransactionOutRecord(
                TrType.AIRDROP,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Size"]),
                buy_asset=base_asset,
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Size"]),
                buy_asset=base_asset,
                sell_quantity=Decimal(row_dict["Total"]),
                sell_asset=quote_asset,
                fee_quantity=fee_quantity,
                fee_asset=fee_asset,
                wallet=WALLET,
            )
    elif row_dict["Side"] == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Total"]),
            buy_asset=quote_asset,
            sell_quantity=Decimal(row_dict["Size"]),
            sell_asset=base_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


def parse_ftx_dust_conversion(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    _normalise_ftx_dict(row_dict)
    data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])

    data_row.t_record = TransactionOutRecord(
        TrType.TRADE,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["proceeds"]),
        buy_asset=row_dict["to"],
        sell_quantity=Decimal(row_dict["size"]),
        sell_asset=row_dict["from"],
        fee_quantity=Decimal(row_dict["fee"]),
        fee_asset=row_dict["to"],
        wallet=WALLET,
    )


def parse_ftx_lending(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    _normalise_ftx_dict(row_dict)
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    data_row.t_record = TransactionOutRecord(
        TrType.INTEREST,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Proceeds"]),
        buy_asset=row_dict["Currency"],
        wallet=WALLET,
    )


def parse_ftx_staking(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    _normalise_ftx_dict(row_dict)
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    data_row.t_record = TransactionOutRecord(
        TrType.STAKING,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Reward"]),
        buy_asset=row_dict["Coin"],
        wallet=WALLET,
    )


def _normalise_ftx_dict(row_dict: Dict[str, str]) -> None:
    if "time" in row_dict:
        row_dict["Time"] = row_dict["time"]

    if "status" in row_dict:
        row_dict["Status"] = row_dict["status"]

    if "coin" in row_dict:
        row_dict["Coin"] = row_dict["coin"]
        row_dict["Currency"] = row_dict["coin"]

    if "size" in row_dict:
        row_dict["Amount"] = row_dict["size"]
        row_dict["Size"] = row_dict["size"]

    if "market" in row_dict:
        row_dict["Market"] = row_dict["market"]

    if "side" in row_dict:
        row_dict["Side"] = row_dict["side"]

    if "total" in row_dict:
        row_dict["Total"] = row_dict["total"]

    if "fee" in row_dict:
        row_dict["Fee"] = row_dict["fee"]

    if "feeCurrency" in row_dict:
        row_dict["Fee Currency"] = row_dict["feeCurrency"]

    if "proceeds" in row_dict:
        row_dict["Proceeds"] = row_dict["proceeds"]


def _split_trading_pair(trading_pair: str) -> Tuple[Optional[str], Optional[str]]:
    if "/" in trading_pair:
        base_asset, quote_asset = trading_pair.split("/")
        return base_asset, quote_asset
    # Futures markets are not currently supported
    return None, None


DataParser(
    ParserType.EXCHANGE,
    "FTX Deposits",
    ["", "Time", "Coin", "Amount", "Status", "Additional info", "Transaction ID", ""],
    worksheet_name="FTX D",
    row_handler=parse_ftx_deposits,
)

DataParser(
    ParserType.EXCHANGE,
    "FTX Deposits",
    ["id", "time", "coin", "size", "status", "additionalInfo", "txid", "_delete"],
    worksheet_name="FTX D",
    row_handler=parse_ftx_deposits,
)

DataParser(
    ParserType.EXCHANGE,
    "FTX Deposits",
    ["id", "time", "coin", "size", "status", "txid"],
    worksheet_name="FTX D",
    row_handler=parse_ftx_deposits,
)

DataParser(
    ParserType.EXCHANGE,
    "FTX Withdrawals",
    ["Time", "Coin", "Amount", "Destination", "Status", "Transaction ID", "fee", ""],
    worksheet_name="FTX W",
    row_handler=parse_ftx_withdrawals,
)

DataParser(
    ParserType.EXCHANGE,
    "FTX Withdrawals",
    ["time", "coin", "size", "address", "status", "txid", "fee", "id"],
    worksheet_name="FTX W",
    row_handler=parse_ftx_withdrawals,
)

ftx_trades = DataParser(
    ParserType.EXCHANGE,
    "FTX Trades",
    ["ID", "Time", "Market", "Side", "Order Type", "Size", "Price", "Total", "Fee", "Fee Currency"],
    worksheet_name="FTX T",
    all_handler=parse_ftx_trades,
)

DataParser(
    ParserType.EXCHANGE,
    "FTX Trades",
    ["id", "time", "market", "side", "type", "size", "price", "total", "fee", "feeCurrency"],
    worksheet_name="FTX T",
    all_handler=parse_ftx_trades,
)

DataParser(
    ParserType.EXCHANGE,
    "FTX Dust Conversion",
    ["time", "from", "to", "size", "fee", "price", "proceeds", "status"],
    worksheet_name="FTX T",
    row_handler=parse_ftx_dust_conversion,
    deprecated=ftx_trades,
)

# Futures markets are not currently supported
# DataParser(
#    ParserType.EXCHANGE,
#    "FTX Funding",
#   ["time", "future", "payment", "rate"],
#    worksheet_name="FTX F",
#    row_handler=parse_ftx_funding,
# )

DataParser(
    ParserType.EXCHANGE,
    "FTX Lending",
    ["Time", "Currency", "Size", "Hourly Funding Rate", "Proceeds", "Proceeds in USD"],
    worksheet_name="FTX L",
    row_handler=parse_ftx_lending,
)

DataParser(
    ParserType.EXCHANGE,
    "FTX Lending",
    ["time", "coin", "size", "rate", "proceeds", "feeUsd"],
    worksheet_name="FTX L",
    row_handler=parse_ftx_lending,
)

DataParser(
    ParserType.EXCHANGE,
    "FTX Lending",
    ["time", "coin", "size", "rate", "proceeds"],
    worksheet_name="FTX L",
    row_handler=parse_ftx_lending,
)

DataParser(
    ParserType.EXCHANGE,
    "FTX Staking",
    ["Time", "Notes", "Coin", "Reward"],
    worksheet_name="FTX S",
    row_handler=parse_ftx_staking,
)
