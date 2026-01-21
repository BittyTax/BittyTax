# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import copy
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, NewType, Optional, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import AssetSymbol, TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import DataRowError, UnexpectedTradingPairError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

PRECISION = Decimal("0." + "0" * 8)

WALLET = "MEXC"

QUOTE_ASSETS = [
    "BRL",
    "BTC",
    "ETH",
    "EUR",
    "USD1",
    "USDC",
    "USDE",
    "USDF",
    "USDT",
]

Instrument = NewType("Instrument", str)


@dataclass
class Position:
    fee_asset: AssetSymbol
    size: Decimal = Decimal(0)
    trading_fees: Decimal = Decimal(0)


def parse_mexc_deposits(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])
    data_row.tx_raw = TxRawPos(parser.in_header.index("TxID"))

    if row_dict["Status"] != "Credited Successfully":
        return

    data_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Deposit Amount"]),
        buy_asset=row_dict["Crypto"],
        wallet=WALLET,
    )


def parse_mexc_withdrawals(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TxID"), tx_dest_pos=parser.in_header.index("Withdrawal Address")
    )

    if row_dict["Status"] != "Withdrawal Successful":
        return

    data_row.t_record = TransactionOutRecord(
        TrType.WITHDRAWAL,
        data_row.timestamp,
        sell_quantity=Decimal(row_dict["Request Amount"]),
        sell_asset=row_dict["Crypto"],
        fee_quantity=Decimal(row_dict["Trading Fee"]),
        fee_asset=row_dict["Crypto"],
        wallet=WALLET,
    )


def parse_mexc_trades_v3(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    base_asset, quote_asset = _split_trading_pair(row_dict["Pairs"])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(
            parser.in_header.index("Pairs"), "Pairs", row_dict["Pairs"]
        )

    fee_quantity, fee_asset = _get_fee(row_dict["Fee"])

    if row_dict["Side"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Executed Amount"]),
            buy_asset=base_asset,
            sell_quantity=Decimal(row_dict["Total"]),
            sell_asset=quote_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["Side"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Total"]),
            buy_asset=quote_asset,
            sell_quantity=Decimal(row_dict["Executed Amount"]),
            sell_asset=base_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


def _get_fee(data_field: str) -> Tuple[Optional[Decimal], str]:
    match = re.match(r"^(\d+(\.\d+)?)([A-Z]+)$", data_field)

    if match:
        amount = match.group(1)
        symbol = match.group(3)
        return Decimal(amount), symbol
    return None, ""


def parse_mexc_trades_v2(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    base_asset, quote_asset = _split_trading_pair(row_dict["Pairs"])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(
            parser.in_header.index("Pairs"), "Pairs", row_dict["Pairs"]
        )

    if row_dict["Direction"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Filled Quantity"]),
            buy_asset=base_asset,
            sell_quantity=Decimal(row_dict["Order Amount"]),
            sell_asset=quote_asset,
            wallet=WALLET,
        )
    elif row_dict["Direction"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Order Amount"]),
            buy_asset=quote_asset,
            sell_quantity=Decimal(row_dict["Filled Quantity"]),
            sell_asset=base_asset,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Direction"), "Direction", row_dict["Direction"]
        )


def parse_mexc_trades_v1(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    base_asset, quote_asset = _split_trading_pair(row_dict["Pairs"])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(
            parser.in_header.index("Pairs"), "Pairs", row_dict["Pairs"]
        )

    if row_dict["Side"] == "BUY":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Executed Amount"]),
            buy_asset=base_asset,
            sell_quantity=Decimal(row_dict["Total"]),
            sell_asset=quote_asset,
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=quote_asset,
            wallet=WALLET,
        )
    elif row_dict["Side"] == "SELL":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Total"]),
            buy_asset=quote_asset,
            sell_quantity=Decimal(row_dict["Executed Amount"]),
            sell_asset=base_asset,
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=quote_asset,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


def parse_mexc_futures(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    positions: Dict[Instrument, Position] = {}
    timestamp_hdr = parser.args[0].group(1)
    if parser.args[0].group(2) is not None:
        utc_offset = parser.args[0].group(2)
    else:
        utc_offset = "UTC+00:00"

    for row_index, data_row in reversed(list(enumerate(data_rows))):
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f" row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if not data_row.row:
            # Delete blank rows
            del data_rows[row_index]
            continue

        data_row.timestamp = DataParser.parse_timestamp(
            f"{data_row.row_dict[timestamp_hdr]} {utc_offset}"
        )

        if data_row.parsed:
            continue

        if data_row.row_dict["Status"] != "FINISHED":
            return

        try:
            _parse_mexc_futures_row(
                data_rows,
                parser,
                data_row,
                positions,
            )
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e

    balance_diffs = {}
    for instrument, position in positions.items():
        if position.fee_asset not in balance_diffs:
            balance_diffs[position.fee_asset] = Decimal(0)

        balance_diffs[position.fee_asset] -= position.trading_fees

        sys.stderr.write(
            f"{Fore.CYAN}conv: Open Position: {instrument} "
            f"size={position.size.normalize():0,f} "
            f"trading_fees={position.trading_fees.normalize():0,f} {position.fee_asset}\n"
        )

    for symbol, balance_diff in balance_diffs.items():
        if balance_diff:
            sys.stderr.write(
                f"{Fore.CYAN}conv: Balance difference: {balance_diff.normalize():0,f} "
                f"{symbol} (for all open positions)\n"
            )


def _parse_mexc_futures_row(
    data_rows: List["DataRow"],
    parser: DataParser,
    data_row: "DataRow",
    positions: Dict[Instrument, Position],
) -> None:
    row_dict = data_row.row_dict
    data_row.parsed = True

    instrument = Instrument(row_dict["Futures Trading Pair"])
    size = Decimal(row_dict["Filled Qty (Cont.)"])
    trading_fee = Decimal(row_dict["Trading Fee"])

    if row_dict["Direction"] == "buy long":
        if instrument not in positions:
            positions[instrument] = Position(AssetSymbol(row_dict["Fee-payment Crypto"]))

        positions[instrument].size += size
        positions[instrument].trading_fees += trading_fee

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: {instrument}:size="
                f"{positions[instrument].size.normalize():0,f} ({size.normalize():+0,f})\n"
                f"{Fore.GREEN}conv: {instrument}:trading_fees="
                f"{positions[instrument].trading_fees.normalize():0,f} "
                f"{positions[instrument].fee_asset} ({trading_fee.normalize():+0,f})\n"
            )
    elif row_dict["Direction"] == "buy short":
        if instrument not in positions:
            positions[instrument] = Position(AssetSymbol(row_dict["Fee-payment Crypto"]))

        size = -abs(size)
        positions[instrument].size += size
        positions[instrument].trading_fees += trading_fee

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: {instrument}:size="
                f"{positions[instrument].size.normalize():0,f} ({size.normalize():+0,f})\n"
                f"{Fore.GREEN}conv: {instrument}:trading_fees="
                f"{positions[instrument].trading_fees.normalize():0,f} "
                f"{positions[instrument].fee_asset} ({trading_fee.normalize():+0,f})\n"
            )
    elif row_dict["Direction"] == "sell short":
        if instrument not in positions:
            raise RuntimeError(f"No position open for {instrument}")

        positions[instrument].size += size
        positions[instrument].trading_fees += trading_fee

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: {instrument}:size="
                f"{positions[instrument].size.normalize():0,f} ({size.normalize():+0,f})\n"
                f"{Fore.GREEN}conv: {instrument}:trading_fees="
                f"{positions[instrument].trading_fees.normalize():0,f} "
                f"{positions[instrument].fee_asset} ({trading_fee.normalize():+0,f})\n"
            )

        partial_close = 1 - (positions[instrument].size / (positions[instrument].size - size))
        _close_position(data_rows, data_row, positions, instrument, partial_close, parser)
    elif row_dict["Direction"] == "sell long":
        if instrument not in positions:
            raise RuntimeError(f"No position open for {instrument}")

        size = -abs(size)
        positions[instrument].size += size
        positions[instrument].trading_fees += trading_fee
        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: {instrument}:size="
                f"{positions[instrument].size.normalize():0,f} ({size.normalize():+0,f})\n"
                f"{Fore.GREEN}conv: {instrument}:trading_fees="
                f"{positions[instrument].trading_fees.normalize():0,f} "
                f"{positions[instrument].fee_asset} ({trading_fee.normalize():+0,f})\n"
            )
        partial_close = 1 - (positions[instrument].size / (positions[instrument].size - size))
        _close_position(data_rows, data_row, positions, instrument, partial_close, parser)
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Direction"), "Direction", row_dict["Direction"]
        )


def _close_position(
    data_rows: List["DataRow"],
    data_row: "DataRow",
    positions: Dict[Instrument, Position],
    instrument: Instrument,
    partial_close: Decimal,
    parser: DataParser,
) -> None:
    row_dict = data_row.row_dict
    _, quote_asset = _split_trading_pair(instrument)
    if quote_asset is None:
        raise UnexpectedTradingPairError(
            parser.in_header.index("Futures Trading Pair"), "Futures Trading Pair", instrument
        )

    realised_pnl = Decimal(row_dict["Closing PNL"])
    trading_fees = (positions[instrument].trading_fees * partial_close).quantize(PRECISION)
    fee_asset = positions[instrument].fee_asset

    if partial_close == 1:
        if config.debug:
            sys.stderr.write(
                f"{Fore.CYAN}conv: Closed position: {instrument} "
                f"trading_fees={trading_fees.normalize():0,f} {positions[instrument].fee_asset}\n"
            )
        del positions[instrument]
    else:
        if config.debug:
            sys.stderr.write(
                f"{Fore.CYAN}conv: Partially closed position ({partial_close.normalize():.2%}): "
                f"{instrument} "
                f"trading_fees={trading_fees.normalize():0,f} {positions[instrument].fee_asset}\n"
            )

        positions[instrument].trading_fees -= trading_fees

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: {instrument}:trading_fees="
                f"{positions[instrument].trading_fees.normalize():0,f} "
                f"{positions[instrument].fee_asset} ({1 - partial_close.normalize():.2%})\n"
            )

    if realised_pnl > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_GAIN,
            data_row.timestamp,
            buy_quantity=realised_pnl,
            buy_asset=quote_asset,
            wallet=WALLET,
            note=instrument,
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_LOSS,
            data_row.timestamp,
            sell_quantity=abs(realised_pnl),
            sell_asset=quote_asset,
            wallet=WALLET,
            note=instrument,
        )

    if trading_fees > 0:
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []
        dup_data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=trading_fees,
            sell_asset=fee_asset,
            wallet=WALLET,
            note=instrument,
        )
        data_rows.append(dup_data_row)


def _split_trading_pair(trading_pair: str) -> Tuple[Optional[str], Optional[str]]:
    if "_" in trading_pair:
        base, quote = trading_pair.split("_", 1)
        return base, quote

    for quote_asset in QUOTE_ASSETS:
        if trading_pair.endswith(quote_asset):
            base = trading_pair[: -len(quote_asset)]
            return base, quote_asset

    return None, None


DataParser(
    ParserType.EXCHANGE,
    "MEXC Deposits",
    ["UID", "Status", "Time", "Crypto", "Network", "Deposit Amount", "TxID", "Progress"],
    worksheet_name="MEXC D",
    row_handler=parse_mexc_deposits,
)

DataParser(
    ParserType.EXCHANGE,
    "MEXC Deposits",
    ["Status", "Time", "Crypto", "Network", "Deposit Amount", "TxID", "Progress"],
    worksheet_name="MEXC D",
    row_handler=parse_mexc_deposits,
)

DataParser(
    ParserType.EXCHANGE,
    "MEXC Withdrawals",
    [
        "UID",
        "Status",
        "Time",
        "Crypto",
        "Network",
        "Request Amount",
        "Withdrawal Address",
        "memo",
        "TxID",
        "Trading Fee",
        "Settlement Amount",
        "Withdrawal Descriptions",
    ],
    worksheet_name="MEXC W",
    row_handler=parse_mexc_withdrawals,
)

DataParser(
    ParserType.EXCHANGE,
    "MEXC Withdrawals",
    [
        "Status",
        "Time",
        "Crypto",
        "Network",
        "Request Amount",
        "Withdrawal Address",
        "TxID",
        "Trading Fee",
        "Settlement Amount",
        "Withdrawal Descriptions",
    ],
    worksheet_name="MEXC W",
    row_handler=parse_mexc_withdrawals,
)

# Export Order History
DataParser(
    ParserType.EXCHANGE,
    "MEXC Trades",
    [
        "UID",
        "Pairs",
        "Time",
        "Type",
        "Direction",
        "Average Filled Price",
        "Order Price",
        "Filled Quantity",
        "Order Quantity",
        "Order Amount",
        "Status",
    ],
    worksheet_name="MEXC T",
    row_handler=parse_mexc_trades_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "MEXC Trades",
    [
        "Pairs",
        "Time",
        "Type",
        "Direction",
        "Average Filled Price",
        "Order Price",
        "Filled Quantity",
        "Order Quantity",
        "Order Amount",
        "Status",
    ],
    worksheet_name="MEXC T",
    row_handler=parse_mexc_trades_v2,
)

# Export Trade History, this is preferred as it contains fees
DataParser(
    ParserType.EXCHANGE,
    "MEXC Trades",
    ["UID", "Pairs", "Time", "Side", "Filled Price", "Executed Amount", "Total", "Fee", "Role"],
    worksheet_name="MEXC T",
    row_handler=parse_mexc_trades_v3,
)

DataParser(
    ParserType.EXCHANGE,
    "MEXC Trades",
    ["Pairs", "Time", "Side", "Filled Price", "Executed Amount", "Total", "Fee", "Role"],
    worksheet_name="MEXC T",
    row_handler=parse_mexc_trades_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "MEXC Futures",
    [
        "UID",
        lambda c: re.match(r"(^Time\((UTC[-+]\d{2}:\d{2})\)|Time)", c),
        "Futures Trading Pair",
        "Direction",
        "Leverage",
        "Order Type",
        "Order Qty (Cont.)",
        "Filled Qty (Cont.)",
        "Order Qty (Crypto)",
        "Filled Qty (Crypto)",
        "Order Qty (Amount)",
        "Filled Qty (Amount)",
        "Order Price",
        "Average Filled Price",
        "Closing PNL",
        "Trading Fee",
        "Fee-payment Crypto",
        "Status",
    ],
    worksheet_name="MEXC F",
    all_handler=parse_mexc_futures,
)

DataParser(
    ParserType.EXCHANGE,
    "MEXC Futures",
    [
        lambda c: re.match(r"(^Time\((UTC[-+]\d{2}:\d{2})\)|Time)", c),
        "Futures Trading Pair",
        "Direction",
        "Leverage",
        "Order Type",
        "Order Qty (Cont.)",
        "Filled Qty (Cont.)",
        "Order Qty (Crypto)",
        "Filled Qty (Crypto)",
        "Order Qty (Amount)",
        "Filled Qty (Amount)",
        "Order Price",
        "Average Filled Price",
        "Closing PNL",
        "Trading Fee",
        "Fee-payment Crypto",
        "Status",
    ],
    worksheet_name="MEXC F",
    all_handler=parse_mexc_futures,
)
