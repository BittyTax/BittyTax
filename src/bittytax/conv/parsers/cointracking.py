# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "CoinTracking"

COINTRACKING_D_MAPPING = {
    "Income": TrType.INCOME,
    "Gift/Tip": TrType.GIFT_RECEIVED,
    "Reward/Bonus": TrType.AIRDROP,
    "Mining": TrType.MINING,
    "Airdrop": TrType.AIRDROP,
    "Staking": TrType.STAKING,
    "Masternode": TrType.STAKING,
}

COINTRACKING_W_MAPPING = {
    "Spend": TrType.SPEND,
    "Donation": TrType.CHARITY_SENT,
    "Gift": TrType.GIFT_SENT,
    "Stolen": TrType.LOST,
    "Lost": TrType.LOST,
}


def parse_cointracking(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(
        row_dict["Date"], dayfirst=config.date_is_day_first
    )

    if row_dict["Type"] == "Trade":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Buy"]),
            buy_asset=data_row.row[2],
            buy_value=Decimal(data_row.row[4]),
            sell_quantity=Decimal(row_dict["Sell"]),
            sell_asset=data_row.row[6],
            sell_value=Decimal(data_row.row[8]),
            wallet=_wallet_name(row_dict["Exchange"]),
        )
    elif row_dict["Type"] == "Deposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Buy"]),
            buy_asset=data_row.row[2],
            wallet=_wallet_name(row_dict["Exchange"]),
        )
    elif row_dict["Type"] in COINTRACKING_D_MAPPING:
        data_row.t_record = TransactionOutRecord(
            COINTRACKING_D_MAPPING[row_dict["Type"]],
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Buy"]),
            buy_asset=data_row.row[2],
            buy_value=Decimal(data_row.row[4]),
            wallet=_wallet_name(row_dict["Exchange"]),
        )
    elif row_dict["Type"] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Sell"]),
            sell_asset=data_row.row[6],
            wallet=_wallet_name(row_dict["Exchange"]),
        )
    elif row_dict["Type"] in COINTRACKING_W_MAPPING:
        if row_dict["Type"] in ("Stolen", "Lost"):
            sell_value = None
        else:
            sell_value = Decimal(data_row.row[8])

        data_row.t_record = TransactionOutRecord(
            COINTRACKING_W_MAPPING[row_dict["Type"]],
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Sell"]),
            sell_asset=data_row.row[6],
            sell_value=sell_value,
            wallet=_wallet_name(row_dict["Exchange"]),
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _wallet_name(wallet: str) -> str:
    if not wallet:
        return WALLET
    return wallet


DataParser(
    ParserType.ACCOUNTING,
    "CoinTracking",
    [
        "Type",
        "Buy",
        "Cur.",
        "Value in BTC",
        "Value in GBP",
        "Sell",
        "Cur.",
        "Value in BTC",
        "Value in GBP",
        "Spread",
        "Exchange",
        "Group",
        "Date",
    ],
    worksheet_name="CoinTracking",
    row_handler=parse_cointracking,
)
