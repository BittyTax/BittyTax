# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Yoroi"


def parse_yoroi(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["Type (Trade, IN or OUT)"] == "Deposit":
        if row_dict["Comment (optional)"].startswith("Staking Reward"):
            t_type = TrType.STAKING
        else:
            t_type = TrType.DEPOSIT

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Buy Amount"]),
            buy_asset=row_dict["Buy Cur."],
            wallet=WALLET,
            note=row_dict["Comment (optional)"],
        )

    elif row_dict["Type (Trade, IN or OUT)"] == "Withdrawal":
        if Decimal(row_dict["Sell Amount"]) == 0:
            t_type = TrType.SPEND
        else:
            t_type = TrType.WITHDRAWAL

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Sell Amount"]),
            sell_asset=row_dict["Sell Cur."],
            fee_quantity=Decimal(row_dict["Fee Amount (optional)"]),
            fee_asset=row_dict["Fee Cur. (optional)"],
            wallet=WALLET,
            note=row_dict["Comment (optional)"],
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Type (Trade, IN or OUT)"),
            "Type (Trade, IN or OUT)",
            row_dict["Type (Trade, IN or OUT)"],
        )


DataParser(
    ParserType.WALLET,
    "Yoroi",
    [
        "Type (Trade, IN or OUT)",
        "Buy Amount",
        "Buy Cur.",
        "Sell Amount",
        "Sell Cur.",
        "Fee Amount (optional)",
        "Fee Cur. (optional)",
        "Exchange (optional)",
        "Trade Group (optional)",
        "Comment (optional)",
        "Date",
        "ID",
    ],
    worksheet_name="Yoroi",
    row_handler=parse_yoroi,
)

DataParser(
    ParserType.WALLET,
    "Yoroi",
    [
        "Type (Trade, IN or OUT)",
        "Buy Amount",
        "Buy Cur.",
        "Sell Amount",
        "Sell Cur.",
        "Fee Amount (optional)",
        "Fee Cur. (optional)",
        "Exchange (optional)",
        "Trade Group (optional)",
        "Comment (optional)",
        "Date",
    ],
    worksheet_name="Yoroi",
    row_handler=parse_yoroi,
)
