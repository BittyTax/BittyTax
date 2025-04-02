# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2025

import copy
import re
import sys
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, NewType, Optional

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import AssetSymbol, TrType
from ...config import config
from ...constants import WARNING
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import DataRowError, UnexpectedContentError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

PRECISION = Decimal("0." + "0" * 8)

WALLET = "BloFin"

Instrument = NewType("Instrument", str)


@dataclass
class Position:
    fee_asset: AssetSymbol
    size: Decimal = Decimal(0)
    trading_fees: Decimal = Decimal(0)
    funding_fees: Decimal = Decimal(0)
    data_row: Optional["DataRow"] = None


def parse_blofin_deposits(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    if not data_row.row:
        # skip empty rows
        return

    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])
    data_row.tx_raw = TxRawPos(parser.in_header.index("txid"))

    if row_dict["State"] != "completed":
        return

    data_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["amount"]),
        buy_asset=row_dict["Asset"],
        wallet=WALLET,
    )


def parse_blofin_withdrawals(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("txid"), tx_dest_pos=parser.in_header.index("Address")
    )

    if row_dict["State"] != "success":
        return

    data_row.t_record = TransactionOutRecord(
        TrType.WITHDRAWAL,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["amount"]),
        buy_asset=row_dict["Asset"],
        wallet=WALLET,
    )


def parse_blofin_spot_trades_v2(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["order_time"])

    if row_dict["Status"] == "canceled":
        return

    if row_dict["Side"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Filled(Quantity)"]),
            buy_asset=row_dict["Underlying Asset"].split("-")[0],
            sell_quantity=Decimal(row_dict["Filled(Value)"]),
            sell_asset=row_dict["Underlying Asset"].split("-")[1],
            fee_quantity=Decimal(row_dict["Fee"].split(" ")[0]),
            fee_asset=row_dict["Fee"].split(" ")[1],
            wallet=WALLET,
        )
    elif row_dict["Side"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Filled(Value)"]),
            buy_asset=row_dict["Underlying Asset"].split("-")[1],
            sell_quantity=Decimal(row_dict["Filled(Quantity)"]),
            sell_asset=row_dict["Underlying Asset"].split("-")[0],
            fee_quantity=Decimal(row_dict["Fee"].split(" ")[0]),
            fee_asset=row_dict["Fee"].split(" ")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


def parse_blofin_spot_trades(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Order Time"])

    if row_dict["Status"] != "Filled":
        return

    if row_dict["Side"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Filled"].split(" ")[0]),
            buy_asset=row_dict["Filled"].split(" ")[1],
            sell_quantity=Decimal(row_dict["Avg Fill"].split(" ")[0])
            * Decimal(row_dict["Filled"].split(" ")[0]),
            sell_asset=row_dict["Avg Fill"].split(" ")[1],
            fee_quantity=Decimal(row_dict["Fee"].split(" ")[0]),
            fee_asset=row_dict["Fee"].split(" ")[1],
            wallet=WALLET,
        )
    elif row_dict["Side"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Avg Fill"].split(" ")[0])
            * Decimal(row_dict["Filled"].split(" ")[0]),
            buy_asset=row_dict["Avg Fill"].split(" ")[1],
            sell_quantity=Decimal(row_dict["Filled"].split(" ")[0]),
            sell_asset=row_dict["Filled"].split(" ")[1],
            fee_quantity=Decimal(row_dict["Fee"].split(" ")[0]),
            fee_asset=row_dict["Fee"].split(" ")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


def parse_blofin_futures(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    positions: Dict[Instrument, Position] = {}

    for row_index, data_row in enumerate(data_rows):
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f" row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if not data_row.row:
            continue

        data_row.timestamp = DataParser.parse_timestamp(data_row.row_dict["order_time"])

        if data_row.parsed:
            continue

        if data_row.row_dict["Status"] != "filled":
            return

        try:
            _parse_blofin_futures_row(
                data_rows,
                parser,
                data_row,
                row_index,
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


def _parse_blofin_futures_row(
    data_rows: List["DataRow"],
    parser: DataParser,
    data_row: "DataRow",
    row_index: int,
    positions: Dict[Instrument, Position],
) -> None:
    row_dict = data_row.row_dict
    data_row.parsed = True

    instrument = Instrument(row_dict["Underlying Asset"])
    size = Decimal(row_dict["Filled(Quantity)"])
    trading_fee = Decimal(row_dict["Fee"])
    fee_asset = _get_asset(row_dict["Underlying Asset"])
    if not fee_asset:
        raise UnexpectedContentError(
            parser.in_header.index("Underlying Asset"),
            "Underlying Asset",
            row_dict["Underlying Asset"],
        )

    if row_dict["Side"] == "Open Long":
        if instrument not in positions:
            positions[instrument] = Position(fee_asset)

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
    elif row_dict["Side"] == "Open Short":
        if instrument not in positions:
            positions[instrument] = Position(fee_asset)

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
    elif row_dict["Side"] == "Close Short":
        if instrument not in positions:
            sys.stderr.write(
                f"{WARNING} No position open for {instrument} at "
                f"{data_row.timestamp:%Y-%m-%dT%H:%M:%S}\n"
            )
            positions[instrument] = Position(fee_asset, -size)

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
        _close_position_futures(
            data_rows, data_row, row_index, positions, instrument, partial_close
        )
    elif row_dict["Side"] == "Close Long":
        if instrument not in positions:
            sys.stderr.write(
                f"{WARNING} No position open for {instrument} at "
                f"{data_row.timestamp:%Y-%m-%dT%H:%M:%S}\n"
            )
            positions[instrument] = Position(fee_asset, size)

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
        _close_position_futures(
            data_rows, data_row, row_index, positions, instrument, partial_close
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


def _get_asset(instrument: str) -> AssetSymbol:
    match = re.match(r"^(?:\w+)-(\w+)|(?:\w+)|(?:\w+)$", instrument)

    if match:
        return AssetSymbol(match.group(1))
    return AssetSymbol("")


def _close_position_futures(
    data_rows: List["DataRow"],
    data_row: "DataRow",
    row_index: int,
    positions: Dict[Instrument, Position],
    instrument: Instrument,
    partial_close: Decimal,
) -> None:
    row_dict = data_row.row_dict
    realised_pnl = Decimal(row_dict["PNL"])
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
            buy_asset=fee_asset,
            wallet=WALLET,
            note=instrument,
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_LOSS,
            data_row.timestamp,
            sell_quantity=abs(realised_pnl),
            sell_asset=fee_asset,
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
        data_rows.insert(row_index + 1, dup_data_row)


def parse_blofin_margin_trades(
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
            _parse_blofin_margin_trades_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_blofin_margin_trades_row(
    data_rows: List["DataRow"], _parser: DataParser, data_row: "DataRow", row_index: int
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(
        row_dict["Order Time"], dayfirst=config.date_is_day_first, tz=config.local_timezone
    )
    data_row.parsed = True

    if row_dict["PNL"] != "--":
        pnl = Decimal(row_dict["PNL"].split(" ")[0])
        pnl_asset = row_dict["PNL"].split(" ")[1]
    else:
        pnl = Decimal(0)
        pnl_asset = ""

    fee = Decimal(row_dict["Fee"].split(" ")[0])
    fee_asset = row_dict["Fee"].split(" ")[1]

    if pnl > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_GAIN,
            data_row.timestamp,
            buy_quantity=pnl,
            buy_asset=pnl_asset,
            wallet=WALLET,
            note=row_dict["Underlying Asset"],
        )
    elif pnl < 0:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_LOSS,
            data_row.timestamp,
            sell_quantity=abs(pnl),
            sell_asset=pnl_asset,
            wallet=WALLET,
            note=row_dict["Underlying Asset"],
        )
    elif fee > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=fee,
            sell_asset=fee_asset,
            wallet=WALLET,
            note=row_dict["Underlying Asset"],
        )

    if pnl != 0 and fee != 0:
        # Insert extra row to contain the MARGIN_FEE in addition to a MARGIN_GAIN/LOSS
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []
        dup_data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=fee,
            sell_asset=fee_asset,
            wallet=WALLET,
            note=row_dict["Underlying Asset"],
        )
        data_rows.insert(row_index + 1, dup_data_row)


def parse_blofin_funding(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    positions: Dict[Instrument, Position] = {}

    for data_row in reversed(data_rows):
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f" row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if not data_row.row:
            continue

        data_row.timestamp = DataParser.parse_timestamp(data_row.row_dict["Time"])

        if data_row.parsed:
            continue

        try:
            _parse_blofin_funding_row(
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

    for instrument in positions:
        # Assume last funding fee received is for a position closed
        _close_position_funding(positions, instrument)


def _parse_blofin_funding_row(
    parser: DataParser,
    data_row: "DataRow",
    positions: Dict[Instrument, Position],
) -> None:
    row_dict = data_row.row_dict
    data_row.parsed = True

    instrument = Instrument(row_dict["symbol"])
    funding_fee = Decimal(row_dict["real_funding_amount"])
    fee_asset = AssetSymbol(row_dict["symbol"].split("-")[1])
    if not fee_asset:
        raise UnexpectedContentError(parser.in_header.index("symbol"), "symbol", row_dict["symbol"])

    if instrument in positions:
        p_data_row = positions[instrument].data_row
        if p_data_row is None:
            raise RuntimeError("Missing data_row")

        # Assume position closed if no funding fees after 1 day
        if p_data_row.timestamp + timedelta(days=1) < data_row.timestamp:
            _close_position_funding(positions, instrument)
            del positions[instrument]

    if instrument not in positions:
        positions[instrument] = Position(fee_asset, data_row=data_row)

    if row_dict["Funding type"] == "pay":
        funding_fee = -funding_fee
        positions[instrument].funding_fees += funding_fee
    elif row_dict["Funding type"] == "receive":
        positions[instrument].funding_fees += funding_fee
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Funding type"), "Funding type", row_dict["Funding type"]
        )

    if config.debug:
        sys.stderr.write(
            f"{Fore.GREEN}conv: {instrument}:funding_fees="
            f"{positions[instrument].funding_fees.normalize():0,f} "
            f"{positions[instrument].fee_asset} ({funding_fee.normalize():+0,f})\n"
        )

    if instrument in positions:
        positions[instrument].data_row = data_row


def _close_position_funding(positions: Dict[Instrument, Position], instrument: Instrument) -> None:
    if config.debug:
        sys.stderr.write(
            f"{Fore.CYAN}conv: Closed position: {instrument}:funding_fees="
            f"{positions[instrument].funding_fees.normalize():0,f} "
            f"{positions[instrument].fee_asset}\n"
        )

    p_data_row = positions[instrument].data_row
    if p_data_row is None:
        raise RuntimeError("Missing data_row")

    if positions[instrument].funding_fees > 0:
        p_data_row.t_record = TransactionOutRecord(
            TrType.FEE_REBATE,
            p_data_row.timestamp,
            buy_quantity=positions[instrument].funding_fees,
            buy_asset=positions[instrument].fee_asset,
            wallet=WALLET,
            note=instrument,
        )
    else:
        p_data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            p_data_row.timestamp,
            sell_quantity=abs(positions[instrument].funding_fees),
            sell_asset=positions[instrument].fee_asset,
            wallet=WALLET,
            note=instrument,
        )


DataParser(
    ParserType.EXCHANGE,
    "BloFin Deposits",
    ["Asset", "amount", "chain_name", "txid", "Time", "State"],
    worksheet_name="BloFin D",
    row_handler=parse_blofin_deposits,
)

DataParser(
    ParserType.EXCHANGE,
    "BloFin Withdrawals",
    ["Asset", "amount", "chain_name", "txid", "Address", "Tag", "Time", "State"],
    worksheet_name="BloFin W",
    row_handler=parse_blofin_withdrawals,
)

DataParser(
    ParserType.EXCHANGE,
    "BloFin Spot Trades",
    [
        "Underlying Asset",
        "order_time",
        "Side",
        "Avg Filled price",
        "Price",
        "Filled(Quantity)",
        "Filled(Total)",
        "Filled(Value)",
        "Filled(OrderValue)",
        "Fee",
        "Order options",
        "Status",
    ],
    worksheet_name="BloFin S",
    row_handler=parse_blofin_spot_trades_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "BloFin Spot Trades",
    [
        "Underlying Asset",
        "Order Time",
        "Side",
        "Avg Fill",
        "Price",
        "Filled",
        "Total",
        "Fee",
        "Order Options",
        "Status",
    ],
    worksheet_name="BloFin S",
    row_handler=parse_blofin_spot_trades,
)

DataParser(
    ParserType.EXCHANGE,
    "BloFin Futures",
    [
        "Underlying Asset",
        "order_time",
        "Side",
        "price",
        "Order price",
        "Filled(Quantity)",
        "Filled(Total)",
        "Filled(Value)",
        "Filled(OrderValue)",
        "PNL",
        "PNL%",
        "Fee",
        "Order options",
        "Reduce-only",
        "Status",
    ],
    worksheet_name="BloFin F",
    all_handler=parse_blofin_futures,
)

DataParser(
    ParserType.EXCHANGE,
    "BloFin Margin Trades",
    [
        "Underlying Asset",
        "Margin Mode",
        "Leverage",
        "Order Time",
        "Side",
        "Avg Fill",
        "Price",
        "Filled",
        "Total",
        "PNL",
        "PNL%",
        "Fee",
        "Order Options",
        "Reduce-only",
        "Status",
    ],
    worksheet_name="BloFin M",
    all_handler=parse_blofin_margin_trades,
)

DataParser(
    ParserType.EXCHANGE,
    "BloFin Funding",
    ["symbol", "QTY", "Funding rate", "Funding type", "Funding Fee", "real_funding_amount", "Time"],
    worksheet_name="BloFin F",
    all_handler=parse_blofin_funding,
)
