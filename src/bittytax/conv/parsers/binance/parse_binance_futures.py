from sys import stderr
from typing import TYPE_CHECKING, Dict, List

from colorama import Fore

from ....bt_types import TrType
from ....config import config
from ...exceptions import DataRowError, UnexpectedTypeError
from ...out_record import TransactionOutRecord
from .utils import WALLET, Decimal

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from ...dataparser import DataParser, ParserArgs
    from ...datarow import DataRow


def _make_trade(tx_rows: List["DataRow"]) -> None:
    buy_quantity = sell_quantity = None
    buy_asset = sell_asset = ""
    trade_row = None

    for data_row in tx_rows:
        row_dict = data_row.row_dict

        if Decimal(row_dict["Amount"]) > 0:
            if buy_quantity is None:
                buy_quantity = Decimal(row_dict["Amount"])
                buy_asset = row_dict["Asset"]
                data_row.parsed = True

        if Decimal(row_dict["Amount"]) <= 0:
            if sell_quantity is None:
                sell_quantity = abs(Decimal(row_dict["Amount"]))
                sell_asset = row_dict["Asset"]
                data_row.parsed = True

        if not trade_row:
            trade_row = data_row

        if buy_quantity and sell_quantity:
            break

    if trade_row:
        trade_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            trade_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            wallet=WALLET,
        )


def _parse_binance_futures_row(
    tx_ids: Dict[str, List["DataRow"]], parser: "DataParser", data_row: "DataRow"
) -> None:
    row_dict = data_row.row_dict

    if row_dict["type"] == "REALIZED_PNL":
        if Decimal(row_dict["Amount"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_GAIN,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount"]),
                buy_asset=row_dict["Asset"],
                wallet=WALLET,
                note=row_dict["Symbol"],
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_LOSS,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Amount"])),
                sell_asset=row_dict["Asset"],
                wallet=WALLET,
                note=row_dict["Symbol"],
            )
    elif row_dict["type"] == "COMMISSION":
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=row_dict["Asset"],
            wallet=WALLET,
            note=row_dict["Symbol"],
        )
    elif row_dict["type"] == "FUNDING_FEE":
        if Decimal(row_dict["Amount"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_FEE_REBATE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount"]),
                buy_asset=row_dict["Asset"],
                wallet=WALLET,
                note=row_dict["Symbol"],
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_FEE,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Amount"])),
                sell_asset=row_dict["Asset"],
                wallet=WALLET,
                note=row_dict["Symbol"],
            )
    elif row_dict["type"] in ("COIN_SWAP_DEPOSIT", "COIN_SWAP_WITHDRAW"):
        _make_trade(tx_ids[row_dict["Transaction ID"]])
    elif row_dict["type"] in ("DEPOSIT", "WITHDRAW", "TRANSFER"):
        # Skip transfers
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def parse_binance_futures(
    data_rows: List["DataRow"], parser: "DataParser", **_kwargs: "Unpack[ParserArgs]"
) -> None:
    tx_ids: Dict[str, List["DataRow"]] = {}
    for dr in data_rows:
        dr.timestamp = parser.parse_timestamp(dr.row_dict["Date(UTC)"])
        # Normalise fields to be compatible with Statements functions
        dr.row_dict["Operation"] = dr.row_dict["type"]
        dr.row_dict["Change"] = dr.row_dict["Amount"]
        dr.row_dict["Coin"] = dr.row_dict["Asset"]

        if dr.row_dict["Transaction ID"] in tx_ids:
            tx_ids[dr.row_dict["Transaction ID"]].append(dr)
        else:
            tx_ids[dr.row_dict["Transaction ID"]] = [dr]

    for data_row in data_rows:
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            stderr.write(
                f"{Fore.YELLOW}conv: "
                f"row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if data_row.parsed:
            continue

        try:
            _parse_binance_futures_row(tx_ids, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e
