# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
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

    if row_dict["Operation Fees"]:
        fee_quantity = Decimal(row_dict["Operation Fees"])
        fee_asset = row_dict["Currency Ticker"]
    else:
        fee_quantity = None
        fee_asset = ""

    if row_dict["Operation Type"] == "IN":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Operation Amount"]) + fee_quantity
            if fee_quantity
            else Decimal(row_dict["Operation Amount"]),
            buy_asset=row_dict["Currency Ticker"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["Operation Type"] == "OUT":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Operation Amount"]) - fee_quantity
            if fee_quantity
            else Decimal(row_dict["Operation Amount"]),
            sell_asset=row_dict["Currency Ticker"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["Operation Type"] in ("FEES", "REVEAL", "BOND"):
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Operation Amount"]) - fee_quantity
            if fee_quantity
            else Decimal(row_dict["Operation Amount"]),
            sell_asset=row_dict["Currency Ticker"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["Operation Type"] == "REWARD":
        data_row.t_record = TransactionOutRecord(
            TrType.STAKING,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Operation Amount"]),
            buy_asset=row_dict["Currency Ticker"],
            wallet=WALLET,
        )
    elif row_dict["Operation Type"] == "NFT_IN":
        # Skip
        return
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
