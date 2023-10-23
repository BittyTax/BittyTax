# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

import copy
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, List, Union

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType, UnmappedType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

KOINLY_D_MAPPING = {
    "": TrType.GIFT_RECEIVED,
    "airdrop": TrType.AIRDROP,
    "fork": TrType.GIFT_RECEIVED,
    "mining": TrType.MINING,
    "reward": TrType.GIFT_RECEIVED,
    "income": TrType.INCOME,
    "loan_interest": TrType.INTEREST,
    "staking": TrType.STAKING,
}

KOINLY_W_MAPPING = {
    "": TrType.GIFT_SENT,
    "gift": TrType.GIFT_SENT,
    "lost": TrType.LOST,
    "cost": TrType.SPEND,
    "donation": TrType.CHARITY_SENT,
    "interest_payment": TrType.SPEND,
}


def parse_koinly(
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
            _parse_koinly_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_koinly_row(
    data_rows: List["DataRow"], parser: DataParser, data_row: "DataRow", row_index: int
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])
    data_row.parsed = True

    if row_dict["Fee Amount"]:
        fee_quantity = Decimal(row_dict["Fee Amount"])
    else:
        fee_quantity = None

    if row_dict["Fee Value (GBP)"]:
        fee_value = Decimal(row_dict["Fee Value (GBP)"])
    else:
        fee_value = None

    if row_dict["Type"] in ("buy", "sell", "exchange"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Received Amount"]),
            buy_asset=row_dict["Received Currency"],
            buy_value=Decimal(row_dict["Net Value (GBP)"]),
            sell_quantity=Decimal(row_dict["Sent Amount"]),
            sell_asset=row_dict["Sent Currency"],
            sell_value=Decimal(row_dict["Net Value (GBP)"]),
            fee_quantity=fee_quantity,
            fee_asset=row_dict["Fee Currency"],
            fee_value=fee_value,
            wallet=row_dict["Sending Wallet"],
            note=row_dict["Description"],
        )
    elif row_dict["Type"] == "transfer":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Sent Amount"]),
            sell_asset=row_dict["Sent Currency"],
            fee_quantity=fee_quantity,
            fee_asset=row_dict["Fee Currency"],
            wallet=row_dict["Sending Wallet"],
            note=row_dict["Description"],
        )
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []
        dup_data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Received Amount"]),
            buy_asset=row_dict["Received Currency"],
            wallet=row_dict["Receiving Wallet"],
            note=row_dict["Description"],
        )
        data_rows.insert(row_index + 1, dup_data_row)
    elif row_dict["Type"] in ("fiat_deposit", "crypto_deposit"):
        if row_dict["Label"] in KOINLY_D_MAPPING:
            t_type: Union[TrType, UnmappedType] = KOINLY_D_MAPPING[row_dict["Label"]]
        else:
            t_type = UnmappedType(f'_{row_dict["Label"]}')

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Received Amount"]),
            buy_asset=row_dict["Received Currency"],
            buy_value=Decimal(row_dict["Net Value (GBP)"]),
            fee_quantity=fee_quantity,
            fee_asset=row_dict["Fee Currency"],
            fee_value=fee_value,
            wallet=row_dict["Receiving Wallet"],
            note=row_dict["Description"],
        )
    elif row_dict["Type"] in ("fiat_withdrawal", "crypto_withdrawal"):
        if row_dict["Label"] in KOINLY_W_MAPPING:
            t_type = KOINLY_W_MAPPING[row_dict["Label"]]
        else:
            t_type = UnmappedType(f'_{row_dict["Label"]}')

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Sent Amount"]),
            sell_asset=row_dict["Sent Currency"],
            sell_value=Decimal(row_dict["Net Value (GBP)"]),
            fee_quantity=fee_quantity,
            fee_asset=row_dict["Fee Currency"],
            fee_value=fee_value,
            wallet=row_dict["Sending Wallet"],
            note=row_dict["Description"],
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    ParserType.ACCOUNTING,
    "Koinly",
    [
        "Date",
        "Type",
        "Label",
        "Sending Wallet",
        "Sent Amount",
        "Sent Currency",
        "Sent Cost Basis",
        "Receiving Wallet",
        "Received Amount",
        "Received Currency",
        "Received Cost Basis",
        "Fee Amount",
        "Fee Currency",
        "Gain (GBP)",
        "Net Value (GBP)",
        "Fee Value (GBP)",
        "TxSrc",
        "TxDest",
        "TxHash",
        "Description",
    ],
    worksheet_name="Koinly",
    all_handler=parse_koinly,
)
