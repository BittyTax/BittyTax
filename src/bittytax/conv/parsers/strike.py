# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022
# implementation of Strike ledger wallet using kraken as my starting point

import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Strike"


def parse_strike_ledger(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    ref_ids: Dict[str, List["DataRow"]] = {}

    for dr in data_rows:
        reference = dr.row_dict["Reference"]
        if reference in ref_ids:
            ref_ids[reference].append(dr)
        else:
            ref_ids[reference] = [dr]

    for row_index, data_row in enumerate(data_rows):
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f"row[{parser.in_header_row_num + data_row.line_num}] {data_row} {row_index}\n"
            )

        if data_row.parsed:
            continue

        try:
            _parse_strike_ledger_row(ref_ids, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_strike_ledger_row(
    ref_ids: Dict[str, List["DataRow"]], parser: DataParser, data_row: "DataRow"
) -> None:
    # strike.me do not document their CSV output, so I can only code for
    # what sample data is available
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date & Time (UTC)"])
    data_row.parsed = True

    if row_dict["Reference"] == "":
        # Skip failed transactions
        return

    if row_dict["Transaction Type"] == "Deposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount GBP"]),
            buy_asset="GBP",
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "Send":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount BTC"])),
            sell_asset="BTC",
            # i always use strikes free transfers, so don't know what they use
            # fee_quantity=abs(Decimal(row_dict["fee"])),
            # fee_asset=_normalise_asset(row_dict["asset"]),
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "Purchase":
        _make_trade(_get_ref_ids(ref_ids, row_dict["Reference"], ("Purchase",)))
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Transaction Type"),
            "Transaction Type",
            row_dict["Transaction Type"],
        )


def _get_ref_ids(
    ref_ids: Dict[str, List["DataRow"]], ref_id: str, k_type: Tuple[str, ...]
) -> List["DataRow"]:
    return [dr for dr in ref_ids[ref_id] if dr.row_dict["Transaction Type"] in k_type]


def _make_trade(ref_ids: List["DataRow"]) -> None:
    buy_quantity = sell_quantity = Decimal(0)
    fee_quantity = None
    buy_asset = sell_asset = config.ccy
    fee_asset = ""
    trade_row = None

    for data_row in ref_ids:
        row_dict = data_row.row_dict
        data_row.timestamp = DataParser.parse_timestamp(row_dict["Date & Time (UTC)"])
        data_row.parsed = True

        if row_dict["Amount GBP"] != "":
            if Decimal(row_dict["Amount GBP"]) < 0:
                sell_quantity = abs(Decimal(row_dict["Amount GBP"]))
                sell_asset = "GBP"

        if row_dict["Fee GBP"] != "":
            if Decimal(row_dict["Fee GBP"]) > 0:
                fee_quantity = Decimal(row_dict["Fee GBP"])
                fee_asset = "GBP"
                sell_quantity = sell_quantity - Decimal(row_dict["Fee GBP"])

        if row_dict["Amount BTC"] != "":
            if Decimal(row_dict["Amount BTC"]) > 0:
                buy_quantity = Decimal(row_dict["Amount BTC"])
                buy_asset = "BTC"
                trade_row = data_row

    if trade_row:
        trade_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            trade_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )


DataParser(
    ParserType.WALLET,
    "Strike",
    [
        "Reference",
        "Date & Time (UTC)",
        "Transaction Type",
        "Amount GBP",
        "Fee GBP",
        "Amount BTC",
        "Fee BTC",
        "BTC Price",
        "Cost Basis (GBP)",
        "Destination",
        "Description",
        "Transaction Hash",
        "Note",
    ],
    worksheet_name="Strike",
    all_handler=parse_strike_ledger,
)
