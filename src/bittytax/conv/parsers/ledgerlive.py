# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Ledger Live"


def parse_ledger_live(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Operation Date"])

    if row_dict["Operation Type"] == "IN":
        if row_dict["Operation Fees"]:
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Operation Amount"])
                + Decimal(row_dict["Operation Fees"]),
                buy_asset=row_dict["Currency Ticker"],
                fee_quantity=Decimal(row_dict["Operation Fees"]),
                fee_asset=row_dict["Currency Ticker"],
                wallet=WALLET,
            )
        else:
            # ERC-20 tokens don't include fees
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Operation Amount"]),
                buy_asset=row_dict["Currency Ticker"],
                wallet=WALLET,
            )
    elif row_dict["Operation Type"] == "OUT":
        if row_dict["Operation Fees"]:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["Operation Amount"])
                - Decimal(row_dict["Operation Fees"]),
                sell_asset=row_dict["Currency Ticker"],
                fee_quantity=Decimal(row_dict["Operation Fees"]),
                fee_asset=row_dict["Currency Ticker"],
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["Operation Amount"]),
                sell_asset=row_dict["Currency Ticker"],
                wallet=WALLET,
            )
    elif row_dict["Operation Type"] in ("FEES", "REVEAL"):
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Operation Amount"])
            - Decimal(row_dict["Operation Fees"]),
            sell_asset=row_dict["Currency Ticker"],
            fee_quantity=Decimal(row_dict["Operation Fees"]),
            fee_asset=row_dict["Currency Ticker"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Operation Type"),
            "Operation Type",
            row_dict["Operation Type"],
        )


DataParser(
    ParserType.WALLET,
    "Ledger Live",
    [
        "Operation Date",
        "Currency Ticker",
        "Operation Type",
        "Operation Amount",
        "Operation Fees",
        "Operation Hash",
        "Account Name",
        "Account xpub",
        "Countervalue Ticker",
        "Countervalue at Operation Date",
        "Countervalue at CSV Export",
    ],
    worksheet_name="Ledger",
    row_handler=parse_ledger_live,
)

DataParser(
    ParserType.WALLET,
    "Ledger Live",
    [
        "Operation Date",
        "Currency Ticker",
        "Operation Type",
        "Operation Amount",
        "Operation Fees",
        "Operation Hash",
        "Account Name",
        "Account xpub",
    ],
    worksheet_name="Ledger",
    row_handler=parse_ledger_live,
)

DataParser(
    ParserType.WALLET,
    "Ledger Live",
    [
        "Operation Date",
        "Currency Ticker",
        "Operation Type",
        "Operation Amount",
        "Operation Fees",
        "Operation Hash",
        "Account Name",
        "Account id",
    ],
    worksheet_name="Ledger",
    row_handler=parse_ledger_live,
)
