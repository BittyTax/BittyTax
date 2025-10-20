# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "WhiteBIT"


def parse_whitebit_deposits(
    data_row: "DataRow", parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Created At"].replace("UTC", "T"))
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("Hash"), tx_dest_pos=parser.in_header.index("Address")
    )

    if row_dict["Status"] != "success":
        return

    if "worksheet" in kwargs and kwargs["worksheet"] == "Withdrawals":
        return

    data_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount"]),
        buy_asset=row_dict["Currency"],
        fee_quantity=Decimal(row_dict["Fee"]),
        fee_asset=row_dict["Currency"],
        wallet=WALLET,
    )


def parse_whitebit_withdrawals(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Created At"].replace("UTC", "T"))
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("Hash"), tx_dest_pos=parser.in_header.index("Address")
    )

    if row_dict["Status"] != "success":
        return

    data_row.t_record = TransactionOutRecord(
        TrType.WITHDRAWAL,
        data_row.timestamp,
        sell_quantity=Decimal(row_dict["Processed Amount"]) - Decimal(row_dict["Processed Fee"]),
        sell_asset=row_dict["Currency"],
        fee_quantity=Decimal(row_dict["Processed Fee"]),
        fee_asset=row_dict["Currency"],
        wallet=WALLET,
    )


def parse_whitebit_trades(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Open"].replace("UTC", "T"))

    if row_dict["Type"] != "market":
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])

    if row_dict["Side"] == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Market"].split("_")[0],
            sell_quantity=Decimal(row_dict["Revenue"]),
            sell_asset=row_dict["Market"].split("_")[1],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Market"].split("_")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


DataParser(
    ParserType.EXCHANGE,
    "WhiteBIT Deposits",
    ["Id", "Currency", "Address", "Hash", "Amount", "Fee", "Status", "Created At", "Updated At"],
    worksheet_name="WhiteBIT D",
    row_handler=parse_whitebit_deposits,
)

DataParser(
    ParserType.EXCHANGE,
    "WhiteBIT Withdrawals",
    [
        "Id",
        "Currency",
        "Address",
        "Hash",
        "Requested Amount",
        "Requested Fee",
        "Processed Amount",
        "Processed Fee",
        "Status",
        "Created At",
        "Updated At",
    ],
    worksheet_name="WhiteBIT W",
    row_handler=parse_whitebit_withdrawals,
)

DataParser(
    ParserType.EXCHANGE,
    "WhiteBIT Trades",
    [
        "Id",
        "Market",
        "Type",
        "Side",
        "Trigger Market",
        "Trigger Condition",
        "Trigger Price",
        "Amount",
        "Price",
        "Fee",
        "Revenue",
        "Completed",
        "Total",
        "Open",
        "Close",
    ],
    worksheet_name="WhiteBIT T",
    row_handler=parse_whitebit_trades,
)
