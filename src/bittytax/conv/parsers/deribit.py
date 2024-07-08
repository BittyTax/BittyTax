# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import copy
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, NewType, Tuple

from colorama import Fore
from typing_extensions import List, Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError, UnknownCryptoassetError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Deribit"

Uid = NewType("Uid", str)
Instrument = NewType("Instrument", str)

balance: Dict[Uid, Decimal] = {}


@dataclass
class Position:
    trading_fees: Decimal = Decimal(0)
    funding_fees: Decimal = Decimal(0)
    unrealised_pnl: Decimal = Decimal(0)


def parse_deribit(
    data_rows: List["DataRow"], parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    positions: Dict[Uid, Dict[Instrument, Position]] = {}
    uid, asset = _get_uid_and_asset(kwargs["filename"])
    balance[uid] = Decimal(0)

    for row_index, data_row in enumerate(
        sorted(data_rows, key=lambda dr: Decimal(dr.row_dict["UserSeq"]), reverse=False)
    ):
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
            _parse_deribit_row(
                data_rows,
                parser,
                data_row,
                row_index,
                positions,
                uid,
                asset,
            )
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e

        if config.debug:
            sys.stderr.write(f"{Fore.GREEN}conv: (uid: {uid}) Balance={balance[uid]} {asset}\n")

    if uid in positions:
        for instrument, position in positions[uid].items():
            sys.stderr.write(
                f"{Fore.CYAN}conv: Open Position: (uid: {uid}) {instrument} "
                f"trading_fees={position.trading_fees} funding_fees={position.funding_fees} "
                f"unrealised_pnl={position.unrealised_pnl}\n"
            )


def _parse_deribit_row(
    data_rows: List["DataRow"],
    parser: DataParser,
    data_row: "DataRow",
    row_index: int,
    positions: Dict[Uid, Dict[Instrument, Position]],
    uid: Uid,
    asset: str,
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])
    data_row.parsed = True

    if "Fee Paid" in row_dict:
        row_dict["Fee Charged"] = row_dict["Fee Paid"]

    if row_dict["Type"] == "deposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset=asset,
            wallet=WALLET,
        )
        if data_row.t_record.buy_quantity:
            balance[uid] += data_row.t_record.buy_quantity
    elif row_dict["Type"] == "withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Change"])) - Decimal(row_dict["Fee Charged"]),
            sell_asset=asset,
            fee_quantity=Decimal(row_dict["Fee Charged"]),
            fee_asset=asset,
            wallet=WALLET,
        )
        if data_row.t_record.sell_quantity:
            balance[uid] -= data_row.t_record.sell_quantity + data_row.t_record.fee_quantity
    elif row_dict["Type"] == "transfer":
        if Decimal(row_dict["Change"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Change"]),
                buy_asset=asset,
                wallet=WALLET,
            )
            if data_row.t_record.buy_quantity:
                balance[uid] += data_row.t_record.buy_quantity
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Change"])),
                sell_asset=asset,
                wallet=WALLET,
            )
            if data_row.t_record.sell_quantity:
                balance[uid] -= data_row.t_record.sell_quantity
    elif row_dict["Type"] == "trade":
        instrument = Instrument(row_dict["Instrument"])
        if uid not in positions:
            positions[uid] = {}
        if instrument not in positions[uid]:
            positions[uid][instrument] = Position()

        trading_fee = Decimal(row_dict["Fee Charged"])
        if trading_fee > 0:
            # Accumulate trading fees
            positions[uid][instrument].trading_fees += trading_fee
            balance[uid] -= trading_fee

            if config.debug:
                sys.stderr.write(
                    f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:trading_fees "
                    f"{positions[uid][instrument].trading_fees} ({trading_fee:+})\n"
                )

        change = Decimal(row_dict["Change"])
        if change == -abs(trading_fee):
            return

        # Accumulate unrealised profit and loss
        unrealised_pnl = Decimal(row_dict["Cash Flow"])
        positions[uid][instrument].unrealised_pnl += unrealised_pnl
        balance[uid] += unrealised_pnl

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:unrealised_pnl "
                f"{positions[uid][instrument].unrealised_pnl} ({unrealised_pnl:+})\n"
            )

        if Decimal(row_dict["Position"]) == 0:
            _close_position(data_rows, data_row, row_index, positions, uid, asset)
    elif row_dict["Type"] == "settlement":
        instrument = Instrument(row_dict["Instrument"])
        if uid not in positions:
            positions[uid] = {}
        if instrument not in positions[uid]:
            positions[uid][instrument] = Position()

        # Accumulate funding fees
        funding_fee = Decimal(row_dict["Funding"])
        if funding_fee != 0:
            positions[uid][instrument].funding_fees += funding_fee
            balance[uid] += funding_fee

            if config.debug:
                sys.stderr.write(
                    f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:funding_fees "
                    f"{positions[uid][instrument].funding_fees} ({funding_fee:+})\n"
                )

        # Accumulate unrealised profit and loss
        unrealised_pnl = Decimal(row_dict["Cash Flow"]) - funding_fee
        positions[uid][instrument].unrealised_pnl += unrealised_pnl
        balance[uid] += unrealised_pnl

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:unrealised_pnl "
                f"{positions[uid][instrument].unrealised_pnl} ({unrealised_pnl:+})\n"
            )

        # Realise profit/loss and total fees when position closes
        if Decimal(row_dict["Position"]) == 0:
            _close_position(data_rows, data_row, row_index, positions, uid, asset)
    elif row_dict["Type"] == "delivery":
        instrument = Instrument(row_dict["Instrument"])
        if uid not in positions:
            positions[uid] = {}
        if instrument not in positions[uid]:
            positions[uid][instrument] = Position()

        trading_fee = Decimal(row_dict["Fee Charged"])
        if trading_fee > 0:
            # Accumulate trading fees
            positions[uid][instrument].trading_fees += trading_fee
            balance[uid] -= trading_fee

            if config.debug:
                sys.stderr.write(
                    f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:trading_fees "
                    f"{positions[uid][instrument].trading_fees} ({trading_fee:+})\n"
                )

        # Accumulate unrealised profit and loss
        unrealised_pnl = Decimal(row_dict["Cash Flow"])
        positions[uid][instrument].unrealised_pnl += unrealised_pnl
        balance[uid] += unrealised_pnl

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:unrealised_pnl "
                f"{positions[uid][instrument].unrealised_pnl} ({unrealised_pnl:+})\n"
            )

        _close_position(data_rows, data_row, row_index, positions, uid, asset)
    elif row_dict["Type"] == "transfer from insurance":
        data_row.t_record = TransactionOutRecord(
            TrType.GIFT_RECEIVED,  # Update to FEE_REBATE when merged
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset="BTC",
            wallet=WALLET,
        )
        if data_row.t_record.buy_quantity:
            balance[uid] += data_row.t_record.buy_quantity
    elif row_dict["Type"] == "socialized fund":
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Change"])),
            sell_asset="BTC",
            wallet=WALLET,
        )
        if data_row.t_record.sell_quantity:
            balance[uid] -= data_row.t_record.sell_quantity
    elif row_dict["Type"] == "position move":
        # Skip
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _close_position(
    data_rows: List["DataRow"],
    data_row: "DataRow",
    row_index: int,
    positions: Dict[Uid, Dict[Instrument, Position]],
    uid: Uid,
    asset: str,
) -> None:
    row_dict = data_row.row_dict
    instrument = Instrument(row_dict["Instrument"])
    price = DataParser.convert_currency(row_dict["Price"], "USD", data_row.timestamp)

    if config.debug:
        sys.stderr.write(
            f"{Fore.CYAN}conv: Closed Position: (uid: {uid}) {instrument} "
            f"trading_fees={positions[uid][instrument].trading_fees} "
            f"funding_fees={positions[uid][instrument].funding_fees} "
            f"unrealised_pnl={positions[uid][instrument].unrealised_pnl}\n"
        )

    if positions[uid][instrument].unrealised_pnl > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_GAIN,
            data_row.timestamp,
            buy_quantity=positions[uid][instrument].unrealised_pnl,
            buy_asset=asset,
            buy_value=positions[uid][instrument].unrealised_pnl * price if price else None,
            wallet=WALLET,
            note=instrument,
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_LOSS,
            data_row.timestamp,
            sell_quantity=abs(positions[uid][instrument].unrealised_pnl),
            sell_asset=asset,
            sell_value=abs(positions[uid][instrument].unrealised_pnl) * price if price else None,
            wallet=WALLET,
            note=instrument,
        )

    dup_data_row = copy.copy(data_row)
    dup_data_row.row = []

    total_fees = positions[uid][instrument].funding_fees - positions[uid][instrument].trading_fees
    if total_fees > 0:
        dup_data_row.t_record = TransactionOutRecord(
            TrType.GIFT_RECEIVED,  # Update to FEE_REBATE when merged
            data_row.timestamp,
            buy_quantity=total_fees,
            buy_asset=asset,
            buy_value=total_fees * price if price else None,
            wallet=WALLET,
            note=instrument,
        )
    else:
        dup_data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=abs(total_fees),
            sell_asset=asset,
            sell_value=abs(total_fees) * price if price else None,
            wallet=WALLET,
            note=instrument,
        )
    data_rows.insert(row_index + 1, dup_data_row)

    del positions[uid][instrument]


def _get_uid_and_asset(filename: str) -> Tuple[Uid, str]:
    match = re.match(r".*transaction_log-(\d+)-([A-Z]{3,4})-.*", filename)

    if match:
        return Uid(match.group(1)), match.group(2)

    match = re.match(r".*[- ]([A-Z]{3,4})[-.*|.csv]", filename)

    if match:
        return Uid(""), match.group(1)

    raise UnknownCryptoassetError(filename)


DataParser(
    ParserType.EXCHANGE,
    "Deribit",
    [
        "ID",
        "UserSeq",
        "Date",
        "Instrument",
        "Type",
        "Side",
        "Base Amount",
        "Position",
        "Price",
        "Mark Price",
        "Index Price",
        "Cash Flow",
        "Funding",
        "Fee Rate",
        "Fee Charged",
        "Fee Balance",
        "Change",
        "Balance",
        "Equity",
        "Trade ID",
        "Order ID",
        "Info",
        "Note",  # New field
    ],
    worksheet_name="Deribit",
    all_handler=parse_deribit,
)

DataParser(
    ParserType.EXCHANGE,
    "Deribit",
    [
        "ID",
        "UserSeq",
        "Date",
        "Instrument",
        "Type",
        "Side",
        "Base Amount",  # Renamed
        "Position",
        "Price",
        "Mark Price",
        "Index Price",  # New field
        "Cash Flow",
        "Funding",
        "Fee Rate",
        "Fee Charged",  # Renamed
        "Fee Balance",
        "Change",
        "Balance",
        "Equity",
        "Trade ID",
        "Order ID",
        "Info",
    ],
    worksheet_name="Deribit",
    all_handler=parse_deribit,
)

DataParser(
    ParserType.EXCHANGE,
    "Deribit",
    [
        "ID",
        "UserSeq",
        "Date",
        "Instrument",
        "Type",
        "Side",
        "Size",
        "Position",
        "Price",
        "Mark Price",
        "Cash Flow",
        "Funding",
        "Fee Rate",
        "Fee Paid",
        "Fee Balance",
        "Change",
        "Balance",
        "Equity",
        "Trade ID",
        "Order ID",
        "Info",
    ],
    worksheet_name="Deribit",
    all_handler=parse_deribit,
)
