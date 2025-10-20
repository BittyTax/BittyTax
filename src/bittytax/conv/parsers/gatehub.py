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
from ..datarow import TxRawPos
from ..exceptions import DataRowError, MissingComponentError, MissingValueError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "GateHub"


def parse_gatehub(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    tx_ids: Dict[str, List["DataRow"]] = {}
    for dr in data_rows:
        if dr.row_dict["TX hash"] in tx_ids:
            tx_ids[dr.row_dict["TX hash"]].append(dr)
        else:
            tx_ids[dr.row_dict["TX hash"]] = [dr]

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
            _parse_gatehub_row(tx_ids, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_gatehub_row(
    tx_ids: Dict[str, List["DataRow"]], parser: DataParser, data_row: "DataRow"
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])
    data_row.tx_raw = TxRawPos(parser.in_header.index("TX hash"))
    data_row.parsed = True

    t_type: Union[TrType, UnmappedType] = UnmappedType("")
    buy_quantity = None
    buy_asset = ""
    sell_quantity = None
    sell_asset = ""
    fee_quantity = None
    fee_asset = ""

    if not row_dict["Amount"]:
        raise MissingValueError(parser.in_header.index("Amount"), "Amount", row_dict["Amount"])

    if row_dict["Type"] == "payment":
        if Decimal(row_dict["Amount"]) < 0:
            t_type = TrType.WITHDRAWAL
            sell_quantity = abs(Decimal(row_dict["Amount"]))
            sell_asset = row_dict["Currency"]
        else:
            t_type = TrType.DEPOSIT
            buy_quantity = Decimal(row_dict["Amount"])
            buy_asset = row_dict["Currency"]

        fee_quantity, fee_asset = _get_tx(tx_ids[row_dict["TX hash"]], "network_fee")
    elif row_dict["Type"] == "exchange":
        t_type = TrType.TRADE
        if Decimal(row_dict["Amount"]) < 0:
            sell_quantity = abs(Decimal(row_dict["Amount"]))
            sell_asset = row_dict["Currency"]

            buy_quantity, buy_asset = _get_tx(tx_ids[row_dict["TX hash"]], "exchange")
        else:
            buy_quantity = Decimal(row_dict["Amount"])
            buy_asset = row_dict["Currency"]

            sell_quantity, sell_asset = _get_tx(tx_ids[row_dict["TX hash"]], "exchange")

        if sell_quantity is None or buy_quantity is None:
            raise MissingComponentError(
                parser.in_header.index("TX hash"), "TX hash", row_dict["TX hash"]
            )

        fee_quantity, fee_asset = _get_tx(tx_ids[row_dict["TX hash"]], "network_fee")
    elif "network_fee" in row_dict["Type"]:
        # Fees which are not associated with a payment or exchange are added
        # as a Spend
        t_type = TrType.SPEND
        sell_quantity = abs(Decimal(row_dict["Amount"]))
        sell_asset = row_dict["Currency"]
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])

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


def _get_tx(tx_id_rows: List["DataRow"], tx_type: str) -> Tuple[Optional[Decimal], str]:
    quantity = None
    asset = ""

    for data_row in tx_id_rows:
        if not data_row.parsed and tx_type in data_row.row_dict["Type"]:
            quantity = abs(Decimal(data_row.row_dict["Amount"]))
            asset = data_row.row_dict["Currency"]
            data_row.timestamp = DataParser.parse_timestamp(data_row.row_dict["Time"])
            data_row.parsed = True
            break

    return quantity, asset


DataParser(
    ParserType.EXCHANGE,
    "GateHub (XRP)",
    [
        "Time",
        "TX hash",
        "Type",
        "Amount",
        "Currency",
        "Currency Issuer Address",
        "Currency Issuer Name",
        "Balance",
    ],
    worksheet_name="Gatehub",
    all_handler=parse_gatehub,
)
