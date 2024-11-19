# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import copy
import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, NewType

from colorama import Fore
from typing_extensions import Dict, List, Optional, Tuple, Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

PRECISION = Decimal("0." + "0" * 8)

WALLET = "Bybit"

OrderId = NewType("OrderId", str)
Contract = NewType("Contract", str)

balance: Decimal = Decimal(0)


@dataclass
class Position:
    unrealised_pnl: Decimal = Decimal(0)
    trading_fees: Decimal = Decimal(0)
    funding_fees: Decimal = Decimal(0)


def parse_bybit_deposits_withdrawals_v2(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date & Time(UTC)"])

    if row_dict["Description"] == "Deposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["QTY"]),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Description"] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["QTY"])),
            sell_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Description"] in (
        "Transfer to Derivatives Account",
        "Transfer from Derivatives Account",
    ):
        # Ignore internal transfers
        return
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Description"), "Description", row_dict["Description"]
        )


def parse_bybit_deposits_withdrawals_v1(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time(UTC)"])

    if row_dict["Type"] == "userDeposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Type"] in (
        "internalAccountTransferDeposit",
        "internalAccountTransferWithdrawal",
    ):
        # Ignore internal transfers
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def parse_bybit_futures(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    order_ids: Dict[OrderId, List["DataRow"]] = {}
    positions: Dict[Contract, Position] = {}

    for dr in data_rows:
        dr.timestamp = DataParser.parse_timestamp(dr.row_dict["Time"])
        order_id = OrderId(dr.row_dict["Order ID"])

        if order_id in order_ids:
            order_ids[order_id].append(dr)
        else:
            order_ids[order_id] = [dr]

    for data_row in reversed(data_rows):
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            if not data_row.parsed:
                sys.stderr.write(
                    f"{Fore.YELLOW}conv: "
                    f" row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
                )
            else:
                sys.stderr.write(
                    f"{Fore.BLUE}conv: "
                    f" //row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
                )

        if data_row.parsed:
            continue

        try:
            _parse_bybit_futures_row(
                data_rows,
                parser,
                data_row,
                order_ids,
                positions,
            )
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: Balance={balance.normalize():0,f} "
                f"{data_row.row_dict['Currency']}\n"
            )

    balance_diff = Decimal(0)
    for contract, position in positions.items():
        balance_diff += position.unrealised_pnl
        balance_diff -= position.trading_fees
        balance_diff -= position.funding_fees

        sys.stderr.write(
            f"{Fore.CYAN}conv: Open Position: {contract} "
            f"unrealised_pnl={position.unrealised_pnl.normalize():0,f} "
            f"trading_fees={position.trading_fees.normalize():0,f} "
            f"funding_fees={position.funding_fees.normalize():0,f}\n"
        )

    if balance_diff:
        sys.stderr.write(
            f"{Fore.CYAN}conv: Balance difference: {balance_diff.normalize():0,f} "
            f"(for all open positions)\n"
        )


def _parse_bybit_futures_row(
    data_rows: List["DataRow"],
    parser: DataParser,
    data_row: "DataRow",
    order_ids: Dict[OrderId, List["DataRow"]],
    positions: Dict[Contract, Position],
) -> None:
    global balance  # pylint: disable=global-statement
    row_dict = data_row.row_dict
    data_row.parsed = True

    contract = Contract(row_dict["Contract"])

    if row_dict["Type"] == "trade":
        unrealised_pnl, trading_fee, quantity, position = _consolidate_trades(
            order_ids[OrderId(row_dict["Order ID"])]
        )

        if position is None:
            raise RuntimeError("Position is None")

        if row_dict["Direction"] in ("Open Long", "Open Short"):
            if contract not in positions:
                positions[contract] = Position()

            positions[contract].trading_fees += trading_fee
            balance -= trading_fee

            if config.debug:
                sys.stderr.write(
                    f"{Fore.GREEN}conv: {contract}:unrealised_pnl="
                    f"{positions[contract].unrealised_pnl.normalize():0,f}\n"
                    f"{Fore.GREEN}conv: {contract}:trading_fees="
                    f"{positions[contract].trading_fees.normalize():0,f} "
                    f"({trading_fee.normalize():+0,f})\n"
                    f"{Fore.GREEN}conv: {contract}:funding_fees="
                    f"{positions[contract].funding_fees.normalize():0,f}\n"
                )
        elif row_dict["Direction"] in ("Close Long", "Close Short"):
            if contract not in positions:
                raise RuntimeError(f"No position open for {contract}")

            positions[contract].unrealised_pnl += unrealised_pnl
            balance += unrealised_pnl
            positions[contract].trading_fees += trading_fee
            balance -= trading_fee

            if config.debug:
                sys.stderr.write(
                    f"{Fore.GREEN}conv: {contract}:unrealised_pnl="
                    f"{positions[contract].unrealised_pnl.normalize():0,f} "
                    f"({unrealised_pnl.normalize():+0,f})\n"
                    f"{Fore.GREEN}conv: {contract}:trading_fees="
                    f"{positions[contract].trading_fees.normalize():0,f} "
                    f"({trading_fee.normalize():+0,f})\n"
                    f"{Fore.GREEN}conv: {contract}:funding_fees="
                    f"{positions[contract].funding_fees.normalize():0,f}\n"
                )

            partial_close = 1 - (position / (quantity + position))

            if config.debug:
                sys.stderr.write(
                    f"{Fore.GREEN}conv: {contract}:position={position.normalize()} "
                    f"(quantity={quantity.normalize()})\n"
                )

            _close_position(data_rows, data_row, positions, partial_close)
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("Direction"), "Direction", row_dict["Direction"]
            )
    elif row_dict["Type"] == "funding":
        if contract not in positions:
            raise RuntimeError(f"No position open for {contract}")

        funding_fee = Decimal(row_dict["Funding"])
        positions[contract].funding_fees -= funding_fee
        balance -= funding_fee

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: {contract}:unrealised_pnl="
                f"{positions[contract].unrealised_pnl.normalize():0,f}\n"
                f"{Fore.GREEN}conv: {contract}:trading_fees="
                f"{positions[contract].trading_fees.normalize():0,f}\n"
                f"{Fore.GREEN}conv: {contract}:funding_fees="
                f"{positions[contract].funding_fees.normalize():0,f} "
                f"({-funding_fee.normalize():+0,f})\n"
            )
    elif row_dict["Type"] == "liquidation":
        if contract not in positions:
            raise RuntimeError(f"No position open for {contract}")

        trading_fee = Decimal(row_dict["Fee Paid"])
        unrealised_pnl = Decimal(row_dict["Cash Flow"])

        positions[contract].unrealised_pnl += unrealised_pnl
        balance += unrealised_pnl
        positions[contract].trading_fees += trading_fee
        balance -= trading_fee

        _close_position(data_rows, data_row, positions, Decimal(1))
    elif row_dict["Type"] in ("transferIn", "transferOut"):
        # Skip internal transfers
        balance += Decimal(row_dict["Cash Flow"])
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _consolidate_trades(
    trades: List["DataRow"],
) -> Tuple[Decimal, Decimal, Decimal, Optional[Decimal]]:
    trading_fee = unrealised_pnl = quantity = Decimal(0)
    position = None

    for dr in trades:
        dr.parsed = True
        unrealised_pnl += Decimal(dr.row_dict["Cash Flow"])
        trading_fee += Decimal(dr.row_dict["Fee Paid"])
        quantity += Decimal(dr.row_dict["Quantity"])

        if position is None:
            position = Decimal(dr.row_dict["Position"])

        if dr.row_dict["Direction"] in ("Open Long", "Open Short"):
            position = max(position, Decimal(dr.row_dict["Position"]))
        elif dr.row_dict["Direction"] in ("Close Long", "Close Short"):
            position = min(position, Decimal(dr.row_dict["Position"]))
        else:
            raise RuntimeError(f"Unexpected direction:{dr.row_dict['Direction']}")

    return unrealised_pnl, trading_fee, quantity, position


def _close_position(
    data_rows: List["DataRow"],
    data_row: "DataRow",
    positions: Dict[Contract, Position],
    partial_close: Decimal,
) -> None:
    row_dict = data_row.row_dict
    contract = Contract(row_dict["Contract"])

    realised_pnl = (positions[contract].unrealised_pnl * partial_close).quantize(PRECISION)
    trading_fees = (positions[contract].trading_fees * partial_close).quantize(PRECISION)
    funding_fees = (positions[contract].funding_fees * partial_close).quantize(PRECISION)

    if partial_close == 1:
        if config.debug:
            sys.stderr.write(
                f"{Fore.CYAN}conv: Closed position: {contract} "
                f"realised_pnl={realised_pnl.normalize():0,f} "
                f"trading_fees={trading_fees.normalize():0,f} "
                f"funding_fees={funding_fees.normalize():0,f}\n"
            )
        del positions[contract]
    else:
        if config.debug:
            sys.stderr.write(
                f"{Fore.CYAN}conv: Partially closed position ({partial_close.normalize():.2%}): "
                f"{contract} "
                f"realised_pnl={realised_pnl.normalize():0,f} "
                f"trading_fees={trading_fees.normalize():0,f} "
                f"funding_fees={funding_fees.normalize():0,f}\n"
            )

        positions[contract].unrealised_pnl -= realised_pnl
        positions[contract].trading_fees -= trading_fees
        positions[contract].funding_fees -= funding_fees

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: {contract}:unrealised_pnl="
                f"{positions[contract].unrealised_pnl.normalize():0,f} "
                f"({1 - partial_close.normalize():.2%})\n"
                f"{Fore.GREEN}conv: {contract}:trading_fees="
                f"{positions[contract].trading_fees.normalize():0,f} "
                f"({1 - partial_close.normalize():.2%})\n"
                f"{Fore.GREEN}conv: {contract}:funding_fees="
                f"{positions[contract].funding_fees.normalize():0,f} "
                f"({1 - partial_close.normalize():.2%})\n"
            )

    if realised_pnl > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_GAIN,
            data_row.timestamp,
            buy_quantity=realised_pnl,
            buy_asset=row_dict["Currency"],
            wallet=WALLET,
            note=contract,
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_LOSS,
            data_row.timestamp,
            sell_quantity=abs(realised_pnl),
            sell_asset=row_dict["Currency"],
            wallet=WALLET,
            note=contract,
        )

    dup_data_row = copy.copy(data_row)
    dup_data_row.row = []

    if funding_fees - trading_fees > 0:
        dup_data_row.t_record = TransactionOutRecord(
            TrType.FEE_REBATE,
            data_row.timestamp,
            buy_quantity=funding_fees - trading_fees,
            buy_asset=row_dict["Currency"],
            wallet=WALLET,
            note=contract,
        )
    else:
        dup_data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=abs(funding_fees - trading_fees),
            sell_asset=row_dict["Currency"],
            wallet=WALLET,
            note=contract,
        )
    data_rows.append(dup_data_row)


DataParser(
    ParserType.EXCHANGE,
    "Bybit Deposits/Withdrawals",
    ["Date & Time(UTC)", "Coin", "QTY", "Type", "Account Balance", "Description"],
    worksheet_name="Bybit D,W",
    row_handler=parse_bybit_deposits_withdrawals_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "Bybit Deposits/Withdrawals",
    ["Type", "Coin", "Amount", "Wallet Balance", "Time(UTC)"],
    worksheet_name="Bybit D,W",
    row_handler=parse_bybit_deposits_withdrawals_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "Bybit Futures",
    [
        "Time",
        "Currency",
        "Contract",
        "Type",
        "Direction",
        "Quantity",
        "Position",
        "Filled Price",
        "Funding",
        "Fee Paid",
        "Cash Flow",
        "Change",
        "Wallet Balance",
        "Fee Rate",
        "Trade ID",
        "Order ID",
    ],
    worksheet_name="Bybit F",
    all_handler=parse_bybit_futures,
)
