# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType, UnmappedType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Gravity"
SYSTEM_ACCOUNT = "00000000-0000-0000-0000-000000000000"


def parse_gravity_v2(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    _parse_gravity(data_rows, parser, referral_type="referral fees payout")


def parse_gravity_v1(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    _parse_gravity(data_rows, parser, referral_type="referral fees grouping")


def _parse_gravity(data_rows: List["DataRow"], parser: DataParser, referral_type: str) -> None:
    tx_ids: Dict[str, List["DataRow"]] = {}
    for dr in data_rows:
        if dr.row_dict["transaction id"] in tx_ids:
            tx_ids[dr.row_dict["transaction id"]].append(dr)
        else:
            tx_ids[dr.row_dict["transaction id"]] = [dr]

    for data_row in data_rows:
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
            _parse_gravity_row(tx_ids, parser, data_row, referral_type)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_gravity_row(
    tx_ids: Dict[str, List["DataRow"]], parser: DataParser, data_row: "DataRow", referral_type: str
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["date utc"])
    data_row.parsed = True

    t_type: Union[TrType, UnmappedType] = UnmappedType("")
    buy_quantity = None
    buy_asset = ""
    sell_quantity = None
    sell_asset = ""
    fee_quantity = None
    fee_asset = ""

    if row_dict["transaction type"] == "deposit":
        if row_dict["from account"] == SYSTEM_ACCOUNT:
            t_type = TrType.DEPOSIT
            buy_quantity = Decimal(row_dict["amount"])
            buy_asset = row_dict["currency"]
        else:
            return

    elif row_dict["transaction type"] == "withdrawal":
        if row_dict["to account"] == SYSTEM_ACCOUNT:
            t_type = TrType.WITHDRAWAL
            sell_quantity = Decimal(row_dict["amount"])
            sell_asset = row_dict["currency"]
            quantity, asset = _get_tx(
                tx_ids[row_dict["transaction id"]], "withdrawal", "to account"
            )
            if quantity is not None and sell_quantity < quantity:
                # Swap sell/fee around
                fee_quantity = sell_quantity
                fee_asset = sell_asset
                sell_quantity = quantity
                sell_asset = asset
            else:
                fee_quantity = quantity
                fee_asset = asset

        else:
            return
    elif row_dict["transaction type"] == "trade" and row_dict["from account"] == SYSTEM_ACCOUNT:
        t_type = TrType.TRADE
        buy_quantity = Decimal(row_dict["amount"])
        buy_asset = row_dict["currency"]

        sell_quantity, sell_asset = _get_tx(
            tx_ids[row_dict["transaction id"]], "trade", "to account"
        )
        if sell_quantity is None:
            return
    elif row_dict["transaction type"] == "trade" and row_dict["to account"] == SYSTEM_ACCOUNT:
        t_type = TrType.TRADE
        sell_quantity = Decimal(row_dict["amount"])
        sell_asset = row_dict["currency"]

        buy_quantity, buy_asset = _get_tx(
            tx_ids[row_dict["transaction id"]], "trade", "from account"
        )
        if buy_quantity is None:
            return
    elif row_dict["transaction type"] == referral_type:
        t_type = TrType.REFERRAL
        buy_quantity = Decimal(row_dict["amount"])
        buy_asset = row_dict["currency"]
    elif row_dict["transaction type"] in (
        "referral fees collection",
        "referral fees grouping",
        "referral fees transfer",
        "internal transfer",
        "correction",
    ):
        return
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("transaction type"),
            "transaction type",
            row_dict["transaction type"],
        )

    data_row.t_record = TransactionOutRecord(
        t_type,
        data_row.timestamp,
        buy_quantity=buy_quantity,
        buy_asset=buy_asset,
        sell_quantity=sell_quantity,
        sell_asset=sell_asset,
        fee_quantity=fee_quantity,
        fee_asset=fee_asset,
        wallet=WALLET,
    )


def _get_tx(
    tx_id_rows: List["DataRow"], tx_type: str, system_acc: str
) -> Tuple[Optional[Decimal], str]:
    quantity = None
    asset = ""

    for data_row in tx_id_rows:
        if (
            not data_row.parsed
            and data_row.row_dict["transaction type"] == tx_type
            and data_row.row_dict[system_acc] == SYSTEM_ACCOUNT
        ):
            quantity = Decimal(data_row.row_dict["amount"])
            asset = data_row.row_dict["currency"]
            data_row.timestamp = DataParser.parse_timestamp(data_row.row_dict["date utc"])
            data_row.parsed = True
            break

    return quantity, asset


DataParser(
    ParserType.EXCHANGE,
    "Gravity (Bitstocks)",
    [
        "transaction id",
        "from account",
        "to account",
        "from account type",
        "to account type",
        "date utc",
        "transaction type",
        "status",
        "amount",
        "currency",
        "withdrawal_address",
    ],
    worksheet_name="Gravity",
    all_handler=parse_gravity_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "Gravity (Bitstocks)",
    [
        "transaction id",
        "from account",
        "to account",
        "date utc",
        "transaction type",
        "status",
        "amount",
        "currency",
    ],
    worksheet_name="Gravity",
    all_handler=parse_gravity_v1,
)
