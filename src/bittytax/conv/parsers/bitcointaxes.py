# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import copy
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, List

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "BitcoinTaxes"

BITCOINTAX_MAPPING = {
    "SPEND": TrType.SPEND,
    "DONATION": TrType.CHARITY_SENT,
    "GIFT": TrType.GIFT_SENT,
    "STOLEN": TrType.LOST,
    "LOST": TrType.LOST,
    "INCOME": TrType.INCOME,
    "MINING": TrType.MINING,
    "GIFTIN": TrType.GIFT_RECEIVED,
}


def parse_bitcointaxes_trades(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    for row_index, data_row in enumerate(data_rows):
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
            _parse_bitcointaxes_trades_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_bitcointaxes_trades_row(
    data_rows: List["DataRow"], parser: DataParser, data_row: "DataRow", row_index: int
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])
    data_row.parsed = True

    # Negative fees are rebates
    if Decimal(row_dict["Fee"]) < 0:
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []
        dup_data_row.t_record = TransactionOutRecord(
            TrType.FEE_REBATE,
            data_row.timestamp,
            buy_quantity=abs(Decimal(row_dict["Fee"])),
            buy_asset=row_dict["FeeCurrency"],
            wallet=WALLET,
        )
        data_rows.insert(row_index + 1, dup_data_row)

        fee_quantity = Decimal(0)
    else:
        fee_quantity = Decimal(row_dict["Fee"])

    if row_dict["Action"] == "BUY":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Volume"]),
            buy_asset=row_dict["Symbol"],
            sell_quantity=abs(Decimal(row_dict["Total"])),
            sell_asset=row_dict["Currency"],
            fee_quantity=fee_quantity if row_dict["FeeCurrency"] else None,
            fee_asset=row_dict["FeeCurrency"],
            wallet=WALLET,
            note=row_dict["Memo"],
        )
    elif row_dict["Action"] == "SELL":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=abs(Decimal(row_dict["Total"])),
            buy_asset=row_dict["Currency"],
            sell_quantity=Decimal(row_dict["Volume"]),
            sell_asset=row_dict["Symbol"],
            fee_quantity=fee_quantity if row_dict["FeeCurrency"] else None,
            fee_asset=row_dict["FeeCurrency"],
            wallet=WALLET,
            note=row_dict["Memo"],
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Action"), "Action", row_dict["Action"])


def parse_bitcointaxes_income_spending(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])
    data_row.parsed = True

    if row_dict["Action"] in ("SPEND", "DONATION", "GIFT", "STOLEN", "LOST"):
        data_row.t_record = TransactionOutRecord(
            BITCOINTAX_MAPPING[row_dict["Action"]],
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Volume"]),
            sell_asset=row_dict["Symbol"],
            sell_value=DataParser.convert_currency(
                row_dict["Total"], row_dict["Currency"], data_row.timestamp
            ),
            fee_quantity=Decimal(row_dict["Fee"]) if row_dict["FeeCurrency"] else None,
            fee_asset=row_dict["FeeCurrency"],
            wallet=WALLET,
            note=row_dict["Memo"],
        )
    elif row_dict["Action"] in ("INCOME", "MINING", "GIFTIN"):
        data_row.t_record = TransactionOutRecord(
            BITCOINTAX_MAPPING[row_dict["Action"]],
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Volume"]),
            buy_asset=row_dict["Symbol"],
            buy_value=DataParser.convert_currency(
                row_dict["Total"], row_dict["Currency"], data_row.timestamp
            ),
            fee_quantity=Decimal(row_dict["Fee"]) if row_dict["FeeCurrency"] else None,
            fee_asset=row_dict["FeeCurrency"],
            wallet=WALLET,
            note=row_dict["Memo"],
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Action"), "Action", row_dict["Action"])


DataParser(
    ParserType.ACCOUNTING,
    "BitcoinTaxes Trades",
    [
        "Date",
        "Action",
        "Symbol",
        "Account",
        "Volume",
        "Price",
        "Currency",
        "Fee",
        "FeeCurrency",
        "Total",
        "Cost/Proceeds",
        "ExchangeId",
        "Category",
        "Subaccount",
        "Memo",
        "SymbolBalance",
        "CurrencyBalance",
        "FeeBalance",
    ],
    worksheet_name="BitcoinTaxes T",
    all_handler=parse_bitcointaxes_trades,
)

DataParser(
    ParserType.ACCOUNTING,
    "BitcoinTaxes Spending/Income",
    [
        "Date",
        "Action",
        "Symbol",
        "Account",
        "Volume",
        "Price",
        "Currency",
        "Fee",
        "FeeCurrency",
        "Total",
        "Ref",
        "Memo",
        "Margin",
        "MarginId",
        "TxHash",
        "Sender",
        "Recipient",
    ],
    worksheet_name="BitcoinTaxes S",
    row_handler=parse_bitcointaxes_income_spending,
)

DataParser(
    ParserType.ACCOUNTING,
    "BitcoinTaxes Spending/Income",
    [
        "Date",
        "Action",
        "Symbol",
        "Account",
        "Volume",
        "Price",
        "Currency",
        "Fee",
        "FeeCurrency",
        "Total",
        "Ref",
        "Memo",
        "Margin",
        "MarginId",
        "TxHash",
        "Sender",
        "Recipient",
        "SymbolBalance",
    ],
    worksheet_name="BitcoinTaxes S",
    row_handler=parse_bitcointaxes_income_spending,
)
