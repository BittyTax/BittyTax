# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2025

import re
from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Coinbase Prime"


def parse_coinbase_prime_orders(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["initiated time"])

    if row_dict["status"] != "Completed":
        return

    if row_dict["side"] == "BUY":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["filled base quantity"]),
            buy_asset=row_dict["market"].split("/")[0],
            sell_quantity=Decimal(row_dict["filled quote quantity"]),
            sell_asset=row_dict["market"].split("/")[1],
            fee_quantity=Decimal(row_dict["total fees and commissions"]),
            fee_asset=row_dict["market"].split("/")[1],
            wallet=WALLET,
        )
    elif row_dict["side"] == "SELL":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["filled quote quantity"]),
            buy_asset=row_dict["market"].split("/")[1],
            sell_quantity=Decimal(row_dict["filled base quantity"]),
            sell_asset=row_dict["market"].split("/")[0],
            fee_quantity=Decimal(row_dict["total fees and commissions"]),
            fee_asset=row_dict["market"].split("/")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("side"), "side", row_dict["side"])


def parse_coinbase_prime_staking(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date/Time of Reward"])

    amount_ccy = DataParser.convert_currency(
        row_dict["Amount of Reward (notional USD)"],
        "USD",
        data_row.timestamp,
    )

    data_row.t_record = TransactionOutRecord(
        TrType.STAKING_REWARD,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount of Reward"]),
        buy_asset=row_dict["Reward Currency"],
        buy_value=amount_ccy,
        wallet=WALLET,
    )


def parse_coinbase_prime_transactions(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["initiated time"])

    if row_dict["transaction value"]:
        quantity = Decimal(row_dict["transaction value"].replace(",", ""))
    else:
        return

    if row_dict["activity type"] == "Deposit":
        if "Reward" in row_dict["activity title"]:
            t_type = TrType.STAKING_REWARD
        elif "Refund" in row_dict["activity title"]:
            t_type = TrType.FEE_REBATE
        else:
            t_type = TrType.DEPOSIT

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            buy_quantity=quantity,
            buy_asset=row_dict["transaction currency"],
            wallet=WALLET,
        )
    elif row_dict["activity type"] == "Withdrawal":
        if "Payment" in row_dict["activity title"]:
            t_type = TrType.SPEND
        elif "Adjustment" in row_dict["activity title"]:
            t_type = TrType.SPEND
        else:
            t_type = TrType.WITHDRAWAL

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            sell_quantity=quantity,
            sell_asset=row_dict["transaction currency"],
            wallet=WALLET,
        )
    elif row_dict["activity type"] == "Stake":
        data_row.t_record = TransactionOutRecord(
            TrType.STAKE,
            data_row.timestamp,
            sell_quantity=quantity,
            sell_asset=row_dict["transaction currency"],
            wallet=WALLET,
        )
    elif row_dict["activity type"] == "Unstake":
        data_row.t_record = TransactionOutRecord(
            TrType.UNSTAKE,
            data_row.timestamp,
            buy_quantity=quantity,
            buy_asset=row_dict["transaction currency"],
            wallet=WALLET,
        )
    elif row_dict["activity type"] == "Conversion":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=quantity,
            buy_asset=_get_convert_asset(row_dict["activity title"]),
            sell_quantity=quantity,
            sell_asset=row_dict["transaction currency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("activity type"), "activity type", row_dict["activity type"]
        )


def _get_convert_asset(activity_title: str) -> str:
    match = re.match(r"^Convert (\w+)/(\w+)$", activity_title)

    if match:
        return match.group(2)
    return ""


DataParser(
    ParserType.EXCHANGE,
    "Coinbase Prime Orders",
    [
        "order id",
        "status",
        "market",
        "side",
        "type",
        "limit price",
        "total order quantity",
        "order currency",
        "filled base quantity",
        "filled quote quantity",
        "average fill price",
        "total fees and commissions",
        "initiated by",
        "initiated time",
        "last updated time",
        "activity level",
        "portfolio name",
        "portfolio id",
        "entity name",
        "entity id",
    ],
    worksheet_name="Coinbase Prime T",
    row_handler=parse_coinbase_prime_orders,
)

DataParser(
    ParserType.EXCHANGE,
    "Coinbase Prime Staking Rewards",
    [
        "Portfolio",
        "Portfolio ID",
        "Entity Name",
        "Entity ID",
        "Wallet Name",
        "Wallet ID",
        "Wallet Address",
        "Reward Address",
        "Wallet Type",
        "Staked Asset",
        "Reward Currency",
        "Date/Time of Reward",
        "Type of Reward",
        "Transaction ID",
        "Blockchain Explorer Link",
        "Amount of Reward",
        "Validator Address",
        "Validator Type",
        "Amount of Reward (notional USD)",
    ],
    worksheet_name="Coinbase Prime S",
    row_handler=parse_coinbase_prime_staking,
)

DataParser(
    ParserType.EXCHANGE,
    "Coinbase Prime Transactions",
    [
        "activity id",
        "final status",
        "activity title",
        "activity type",
        "asset",
        "wallet name",
        "transaction value",
        "transaction currency",
        "initiated by",
        "approved by",
        "rejected by",
        "initiated time",
        "last updated time",
        "activity level",
        "portfolio name",
        "portfolio id",
        "entity name",
        "entity id",
    ],
    worksheet_name="Coinbase Prime D,W",
    row_handler=parse_coinbase_prime_transactions,
)
