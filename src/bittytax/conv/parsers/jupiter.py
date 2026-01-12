# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2025

import copy
import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, NewType

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

WALLET = "Jupiter"

PRECISION = Decimal("0.00")

Instrument = NewType("Instrument", str)


@dataclass
class Position:
    size: Decimal = Decimal(0)
    fees: Decimal = Decimal(0)


def parse_jupiter_futures(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    positions: Dict[Instrument, Position] = {}

    for data_row in sorted(data_rows, key=lambda dr: Decimal(dr.row_dict["ID"])):
        if data_row.parsed:
            continue

        if config.debug:
            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f" row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        try:
            _parse_jupiter_futures_row(data_rows, parser, data_row, positions)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e

    for instrument, position in positions.items():
        sys.stderr.write(
            f"{Fore.CYAN}conv: Open Position: {instrument} "
            f"size={position.size.normalize():0,f} "
            f"fees={position.fees.normalize():0,f}\n"
        )


def _parse_jupiter_futures_row(
    data_rows: List["DataRow"],
    parser: DataParser,
    data_row: "DataRow",
    positions: Dict[Instrument, Position],
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Created At"])
    data_row.tx_raw = TxRawPos(parser.in_header.index("Transaction ID"))
    data_row.parsed = True

    size = Decimal(row_dict["Size (USD)"])
    fee = DataParser.convert_currency(row_dict["Fee (USD)"], "USD", data_row.timestamp)
    liquidation_fee = DataParser.convert_currency(
        row_dict["Liquidation Fee (USD)"], "USD", data_row.timestamp
    )

    if size is None:
        raise RuntimeError("Missing size")

    if fee is None:
        raise RuntimeError("Missing fee")

    if liquidation_fee is None:
        raise RuntimeError("Missing liquidation_fee")

    if row_dict["Action"] == "Increase Long":
        instrument = Instrument(f"{row_dict['Symbol'].upper()}-PERP-Long")
        if instrument not in positions:
            positions[instrument] = Position()

        positions[instrument].size += size
        positions[instrument].fees += fee
        positions[instrument].fees += liquidation_fee

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: {instrument}:size="
                f"{positions[instrument].size.normalize():0,f} ({size.normalize():+0,f})\n"
                f"{Fore.GREEN}conv: {instrument}:fees="
                f"{positions[instrument].fees.normalize():0,f} "
                f"({fee.normalize():+0,f})\n"
            )
    elif row_dict["Action"] == "Increase Short":
        instrument = Instrument(f"{row_dict['Symbol'].upper()}-PERP-Short")
        if instrument not in positions:
            positions[instrument] = Position()

        size = -abs(size)
        positions[instrument].size += size
        positions[instrument].fees += fee
        positions[instrument].fees += liquidation_fee

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: {instrument}:size="
                f"{positions[instrument].size.normalize():0,f} ({size.normalize():+0,f})\n"
                f"{Fore.GREEN}conv: {instrument}:fees="
                f"{positions[instrument].fees.normalize():0,f} "
                f"({fee.normalize():+0,f})\n"
            )
    elif row_dict["Action"] == "Decrease Long":
        instrument = Instrument(f"{row_dict['Symbol'].upper()}-PERP-Long")
        if instrument not in positions:
            raise RuntimeError(f"No position open for {instrument}")

        size = -abs(size)
        positions[instrument].size += size
        positions[instrument].fees += fee
        positions[instrument].fees += liquidation_fee

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: {instrument}:size="
                f"{positions[instrument].size.normalize():0,f} ({size.normalize():+0,f})\n"
                f"{Fore.GREEN}conv: {instrument}:fees="
                f"{positions[instrument].fees.normalize():0,f} "
                f"({fee.normalize():+0,f})\n"
            )

        partial_close = 1 - (positions[instrument].size / (positions[instrument].size - size))
        _close_position(data_rows, data_row, positions, instrument, partial_close)
    elif row_dict["Action"] == "Decrease Short":
        instrument = Instrument(f"{row_dict['Symbol'].upper()}-PERP-Short")
        if instrument not in positions:
            raise RuntimeError(f"No position open for {instrument}")

        positions[instrument].size += size
        positions[instrument].fees += fee
        positions[instrument].fees += liquidation_fee

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: {instrument}:size="
                f"{positions[instrument].size.normalize():0,f} ({size.normalize():+0,f})\n"
                f"{Fore.GREEN}conv: {instrument}:fees="
                f"{positions[instrument].fees.normalize():0,f} "
                f"({fee.normalize():+0,f})\n"
            )

        partial_close = 1 - (positions[instrument].size / (positions[instrument].size - size))
        _close_position(data_rows, data_row, positions, instrument, partial_close)
    else:
        raise UnexpectedTypeError(parser.in_header.index("ACTION"), "ACTION", row_dict["ACTION"])


def _close_position(
    data_rows: List["DataRow"],
    data_row: "DataRow",
    positions: Dict[Instrument, Position],
    instrument: Instrument,
    partial_close: Decimal,
) -> None:
    row_dict = data_row.row_dict
    pnl = DataParser.convert_currency(row_dict["PnL (USD)"], "USD", data_row.timestamp)
    fees = positions[instrument].fees * partial_close

    if pnl is None:
        raise RuntimeError("Missing pnl")

    if partial_close == 1:
        if config.debug:
            sys.stderr.write(
                f"{Fore.CYAN}conv: Closed position: {instrument} " f"fees={fees.normalize():0,f}\n"
            )
        del positions[instrument]
    else:
        if config.debug:
            sys.stderr.write(
                f"{Fore.CYAN}conv: Partially closed position ({partial_close.normalize():.2%}): "
                f"{instrument} fees={fees.normalize():0,f}\n"
            )

        positions[instrument].fees -= fees

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: {instrument}:fees="
                f"{positions[instrument].fees.normalize():0,f} "
                f"({1 - partial_close.normalize():.2%})\n"
            )

    if pnl > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_GAIN,
            data_row.timestamp,
            buy_quantity=pnl,
            buy_asset=config.ccy,
            wallet=f"{WALLET}-{row_dict['Owner'][0 : TransactionOutRecord.WALLET_ADDR_LEN]}",
            note=instrument,
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_LOSS,
            data_row.timestamp,
            sell_quantity=abs(pnl),
            sell_asset=config.ccy,
            wallet=f"{WALLET}-{row_dict['Owner'][0 : TransactionOutRecord.WALLET_ADDR_LEN]}",
            note=instrument,
        )

    if fees > 0:
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []
        dup_data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=fees,
            sell_asset=config.ccy,
            wallet=f"{WALLET}-{row_dict['Owner'][0 : TransactionOutRecord.WALLET_ADDR_LEN]}",
            note=instrument,
        )
        data_rows.append(dup_data_row)


jupiter_parser = DataParser(
    ParserType.EXCHANGE,
    "Jupiter Futures",
    [
        "ID",
        "Owner",
        "Symbol",
        "Created At",
        "Updated At",
        "Action",
        "Order Type",
        "Deposit/Withdrawal (USD)",
        "Price",
        "Size (USD)",
        "PnL (USD)",
        "Fee (USD)",
        "Liquidation Fee (USD)",
        "Transaction ID",
    ],
    worksheet_name="Jupiter F",
    all_handler=parse_jupiter_futures,
)
