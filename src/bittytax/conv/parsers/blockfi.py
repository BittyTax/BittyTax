# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import sys
from decimal import Decimal
from typing import TYPE_CHECKING

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...constants import WARNING
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "BlockFi"


def parse_blockfi(data_row: "DataRow", parser: DataParser, **kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict

    if row_dict["Confirmed At"] == "" and not kwargs["unconfirmed"]:
        if parser.in_header_row_num is None:
            raise RuntimeError("Missing in_header_row_num")

        sys.stderr.write(
            f"{Fore.YELLOW}row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            f"{WARNING} Skipping unconfirmed transaction, use the [-uc] option to include it\n"
        )
        return

    data_row.timestamp = DataParser.parse_timestamp(row_dict["Confirmed At"])

    if row_dict["Transaction Type"] in (
        "Deposit",
        "Wire Deposit",
        "ACH Deposit",
        "Crypto Transfer",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Cryptocurrency"],
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] in (
        "Withdrawal",
        "Wire Withdrawal",
        "ACH Withdrawal",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=row_dict["Cryptocurrency"],
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "Withdrawal Fee":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(0),
            sell_asset=row_dict["Cryptocurrency"],
            fee_quantity=abs(Decimal(row_dict["Amount"])),
            fee_asset=row_dict["Cryptocurrency"],
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "Interest Payment":
        data_row.t_record = TransactionOutRecord(
            TrType.INTEREST,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Cryptocurrency"],
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "Referral Bonus":
        data_row.t_record = TransactionOutRecord(
            TrType.REFERRAL,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Cryptocurrency"],
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] == "Bonus Payment":
        data_row.t_record = TransactionOutRecord(
            TrType.AIRDROP,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Cryptocurrency"],
            wallet=WALLET,
        )
    elif row_dict["Transaction Type"] in ("Trade", "BIA Withdraw"):
        # Skip trades, and internal transfers
        return
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Transaction Type"),
            "Transaction Type",
            row_dict["Transaction Type"],
        )


def parse_blockfi_trades(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    data_row.t_record = TransactionOutRecord(
        TrType.TRADE,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Buy Quantity"]),
        buy_asset=row_dict["Buy Currency"].upper(),
        sell_quantity=abs(Decimal(row_dict["Sold Quantity"])),
        sell_asset=row_dict["Sold Currency"].upper(),
        wallet=WALLET,
    )


DataParser(
    ParserType.SAVINGS,
    "BlockFi",
    [
        "Cryptocurrency",
        "Amount",
        "Transaction Type",
        "Exchange Rate Per Coin (USD)",
        "Confirmed At",
    ],
    worksheet_name="BlockFi",
    row_handler=parse_blockfi,
)

DataParser(
    ParserType.SAVINGS,
    "BlockFi",
    ["Cryptocurrency", "Amount", "Transaction Type", "Confirmed At"],
    worksheet_name="BlockFi",
    row_handler=parse_blockfi,
)

DataParser(
    ParserType.SAVINGS,
    "BlockFi Trades",
    [
        "Trade ID",
        "Date",
        "Buy Quantity",
        "Buy Currency",
        "Sold Quantity",
        "Sold Currency",
        "Rate Amount",
        "Rate Currency",
        "Type",
        "Frequency",
        "Destination",
    ],
    worksheet_name="BlockFi T",
    row_handler=parse_blockfi_trades,
)

DataParser(
    ParserType.SAVINGS,
    "BlockFi Trades",
    [
        "Trade ID",
        "Date",
        "Buy Quantity",
        "Buy Currency",
        "Sold Quantity",
        "Sold Currency",
        "Rate Amount",
        "Rate Currency",
        "Type",
    ],
    worksheet_name="BlockFi T",
    row_handler=parse_blockfi_trades,
)
