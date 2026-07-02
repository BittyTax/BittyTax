# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

import copy
import re
import sys
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional, Union

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType, UnmappedType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

KOINLY_D_MAPPING = {
    "": TrType.GIFT_RECEIVED,
    "Airdrop": TrType.AIRDROP,
    "airdrop": TrType.AIRDROP,
    "Fork": TrType.FORK,
    "fork": TrType.FORK,
    "Mining": TrType.MINING,
    "mining": TrType.MINING,
    "Reward": TrType.STAKING_REWARD,
    "reward": TrType.STAKING_REWARD,
    "Income": TrType.INCOME,
    "income": TrType.INCOME,
    "Other income": TrType.INCOME,
    "other_income": TrType.INCOME,
    "Lending interest": TrType.INTEREST,
    "lending_interest": TrType.INTEREST,
    "Cashback": TrType.CASHBACK,
    "cashback": TrType.CASHBACK,
    "Salary": TrType.INCOME,
    "salary": TrType.INCOME,
    "Fee refund": TrType.FEE_REBATE,
    "fee_refund": TrType.FEE_REBATE,
    "Loan": TrType.LOAN,
    "loan": TrType.LOAN,
    "Margin loan": TrType.LOAN,
    "margin_loan": TrType.LOAN,
    "Realized gain": TrType.MARGIN_GAIN,
    "realized_gain": TrType.MARGIN_GAIN,
}

KOINLY_W_MAPPING = {
    "": TrType.GIFT_SENT,
    "Gift": TrType.GIFT_SENT,
    "gift": TrType.GIFT_SENT,
    "Lost": TrType.LOST,
    "lost": TrType.LOST,
    "Donation": TrType.CHARITY_SENT,
    "donation": TrType.CHARITY_SENT,
    "Cost": TrType.SPEND,
    "cost": TrType.SPEND,
    "Loan fee": TrType.LOAN_INTEREST,
    "loan_fee": TrType.LOAN_INTEREST,
    "Margin fee": TrType.MARGIN_FEE,
    "margin_fee": TrType.MARGIN_FEE,
    "Loan repayment": TrType.LOAN_REPAYMENT,
    "loan_repayment": TrType.LOAN_REPAYMENT,
    "Margin repayment": TrType.LOAN_REPAYMENT,
    "margin_repayment": TrType.LOAN_REPAYMENT,
    "Realized gain": TrType.MARGIN_LOSS,
    "realized_gain": TrType.MARGIN_LOSS,
}


def parse_koinly(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    currency = parser.args[2].group(1)

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
            _parse_koinly_row(data_rows, parser, data_row, row_index, currency)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_koinly_row(
    data_rows: List["DataRow"],
    parser: DataParser,
    data_row: "DataRow",
    row_index: int,
    currency: str,
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TxHash"),
        parser.in_header.index("TxSrc"),
        parser.in_header.index("TxDest"),
    )
    data_row.parsed = True

    if "Label" in row_dict:
        row_dict["Tag"] = row_dict["Label"]

    if row_dict["Fee Amount"]:
        fee_quantity = Decimal(row_dict["Fee Amount"])
    else:
        fee_quantity = None

    if row_dict[f"Fee Value ({currency})"]:
        fee_value = DataParser.convert_currency(
            row_dict[f"Fee Value ({currency})"], currency, data_row.timestamp
        )
    else:
        fee_value = None

    net_value = DataParser.convert_currency(
        row_dict[f"Net Value ({currency})"], currency, data_row.timestamp
    )

    if row_dict["Type"] in ("buy", "sell", "exchange"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Received Amount"]),
            buy_asset=row_dict["Received Currency"],
            buy_value=net_value,
            sell_quantity=Decimal(row_dict["Sent Amount"]),
            sell_asset=row_dict["Sent Currency"],
            sell_value=net_value,
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
            fee_value=fee_value,
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
        if row_dict["Tag"] in KOINLY_D_MAPPING:
            t_type: Union[TrType, UnmappedType] = KOINLY_D_MAPPING[row_dict["Tag"]]
        else:
            t_type = UnmappedType(f'_{row_dict["Tag"]}')

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Received Amount"]),
            buy_asset=row_dict["Received Currency"],
            buy_value=net_value,
            fee_quantity=fee_quantity,
            fee_asset=row_dict["Fee Currency"],
            fee_value=fee_value,
            wallet=row_dict["Receiving Wallet"],
            note=row_dict["Description"],
        )
    elif row_dict["Type"] in ("fiat_withdrawal", "crypto_withdrawal"):
        if row_dict["Tag"] in KOINLY_W_MAPPING:
            t_type = KOINLY_W_MAPPING[row_dict["Tag"]]
        else:
            t_type = UnmappedType(f'_{row_dict["Tag"]}')

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Sent Amount"]),
            sell_asset=row_dict["Sent Currency"],
            sell_value=net_value,
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
        lambda h: h in ("Label", "Tag"),
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
        lambda h: re.match(r"Gain \((\w{3})\)", h),
        lambda h: re.match(r"Net Value \((\w{3})\)", h),
        lambda h: re.match(r"Fee Value \((\w{3})\)", h),
        "TxSrc",
        "TxDest",
        "TxHash",
        "Description",
    ],
    worksheet_name="Koinly",
    all_handler=parse_koinly,
)


# Koinly "Bulk edit in Excel" transactions export, see:
# https://support.koinly.io/en/articles/9490043-bulk-edit-in-excel
# One row per transaction, using From/To columns instead of the Sent/Received columns of the
# tax report export above. The direction is taken from the populated side: "To" only is a
# deposit, "From" only is a withdrawal, both is a trade. Currency and wallet cells carry a
# ";<id>" suffix (e.g. "WFLR;9546698") which is removed. The Tag column drives the type for
# deposits and withdrawals, an untagged transfer defaults to Deposit/Withdrawal.


def _strip_koinly_id(value: str) -> str:
    return value.split(";", 1)[0].strip()


def _get_koinly_value(amount: str, currency: str, timestamp: datetime) -> Optional[Decimal]:
    if amount and Decimal(amount) != 0:
        return DataParser.convert_currency(amount, _strip_koinly_id(currency), timestamp)
    return None


def parse_koinly_bulk_edit(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date (UTC)"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TxHash"),
        parser.in_header.index("TxSrc"),
        parser.in_header.index("TxDest"),
    )

    tag = row_dict["Tag"]
    from_amount = row_dict["From Amount"]
    to_amount = row_dict["To Amount"]
    has_from = bool(from_amount) and Decimal(from_amount) != 0
    has_to = bool(to_amount) and Decimal(to_amount) != 0

    value = _get_koinly_value(
        row_dict["Net Value (read-only)"],
        row_dict["Value Currency (read-only)"],
        data_row.timestamp,
    ) or _get_koinly_value(
        row_dict["Net Worth Amount"], row_dict["Net Worth Currency"], data_row.timestamp
    )

    if row_dict["Fee Amount"]:
        fee_quantity = Decimal(row_dict["Fee Amount"])
        fee_asset = _strip_koinly_id(row_dict["Fee Currency"])
    else:
        fee_quantity = None
        fee_asset = ""

    fee_value = _get_koinly_value(
        row_dict["Fee Value (read-only)"],
        row_dict["Value Currency (read-only)"],
        data_row.timestamp,
    ) or _get_koinly_value(
        row_dict["Fee Worth Amount"], row_dict["Fee Worth Currency"], data_row.timestamp
    )

    if has_from and has_to:
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(to_amount),
            buy_asset=_strip_koinly_id(row_dict["To Currency"]),
            buy_value=value,
            sell_quantity=Decimal(from_amount),
            sell_asset=_strip_koinly_id(row_dict["From Currency"]),
            sell_value=value,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            fee_value=fee_value,
            wallet=_strip_koinly_id(row_dict["To Wallet (read-only)"]),
            note=row_dict["Description"],
        )
    elif has_to:
        if tag == "":
            t_type: Union[TrType, UnmappedType] = TrType.DEPOSIT
        else:
            t_type = KOINLY_D_MAPPING.get(tag, UnmappedType(f"_{tag}"))

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            buy_quantity=Decimal(to_amount),
            buy_asset=_strip_koinly_id(row_dict["To Currency"]),
            buy_value=value,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            fee_value=fee_value,
            wallet=_strip_koinly_id(row_dict["To Wallet (read-only)"]),
            note=row_dict["Description"],
        )
    elif has_from:
        if tag == "":
            t_type = TrType.WITHDRAWAL
        else:
            t_type = KOINLY_W_MAPPING.get(tag, UnmappedType(f"_{tag}"))

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            sell_quantity=Decimal(from_amount),
            sell_asset=_strip_koinly_id(row_dict["From Currency"]),
            sell_value=value,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            fee_value=fee_value,
            wallet=_strip_koinly_id(row_dict["From Wallet (read-only)"]),
            note=row_dict["Description"],
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    ParserType.ACCOUNTING,
    "Koinly",
    [
        "ID (read-only)",
        "Parent ID (read-only)",
        "Date (UTC)",
        "Type",
        "Tag",
        "From Wallet (read-only)",
        "From Wallet ID",
        "From Amount",
        "From Currency",
        "To Wallet (read-only)",
        "To Wallet ID",
        "To Amount",
        "To Currency",
        "Fee Amount",
        "Fee Currency",
        "Net Worth Amount",
        "Net Worth Currency",
        "Fee Worth Amount",
        "Fee Worth Currency",
        "Net Value (read-only)",
        "Fee Value (read-only)",
        "Value Currency (read-only)",
        "Deleted",
        "From Source (read-only)",
        "To Source (read-only)",
        "Negative Balances (read-only)",
        "Missing Rates (read-only)",
        "Missing Cost Basis (read-only)",
        "Synced To Accounting At (UTC read-only)",
        "TxSrc",
        "TxDest",
        "TxHash",
        "Description",
    ],
    worksheet_name="Koinly",
    row_handler=parse_koinly_bulk_edit,
)
