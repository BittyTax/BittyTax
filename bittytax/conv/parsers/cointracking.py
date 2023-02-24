# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

WALLET = "CoinTracking"

COINTRACKING_D_MAPPING = {
    "Income": TransactionOutRecord.TYPE_INCOME,
    "Gift/Tip": TransactionOutRecord.TYPE_GIFT_RECEIVED,
    "Reward/Bonus": TransactionOutRecord.TYPE_GIFT_RECEIVED,
    "Mining": TransactionOutRecord.TYPE_MINING,
    "Airdrop": TransactionOutRecord.TYPE_AIRDROP,
    "Staking": TransactionOutRecord.TYPE_STAKING,
    "Masternode": TransactionOutRecord.TYPE_STAKING,
}

COINTRACKING_W_MAPPING = {
    "Spend": TransactionOutRecord.TYPE_SPEND,
    "Donation": TransactionOutRecord.TYPE_CHARITY_SENT,
    "Gift": TransactionOutRecord.TYPE_GIFT_SENT,
    "Stolen": TransactionOutRecord.TYPE_LOST,
    "Lost": TransactionOutRecord.TYPE_LOST,
}


def parse_cointracking(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"], dayfirst=True)

    if row_dict["Type"] == "Trade":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=row_dict["Buy"],
            buy_asset=data_row.row[2],
            buy_value=data_row.row[4],
            sell_quantity=row_dict["Sell"],
            sell_asset=data_row.row[6],
            sell_value=data_row.row[8],
            wallet=wallet_name(row_dict["Exchange"]),
        )
    elif row_dict["Type"] == "Deposit":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["Buy"],
            buy_asset=data_row.row[2],
            wallet=wallet_name(row_dict["Exchange"]),
        )
    elif row_dict["Type"] in COINTRACKING_D_MAPPING:
        data_row.t_record = TransactionOutRecord(
            COINTRACKING_D_MAPPING[row_dict["Type"]],
            data_row.timestamp,
            buy_quantity=row_dict["Buy"],
            buy_asset=data_row.row[2],
            buy_value=data_row.row[4],
            wallet=wallet_name(row_dict["Exchange"]),
        )
    elif row_dict["Type"] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=row_dict["Sell"],
            sell_asset=data_row.row[6],
            wallet=wallet_name(row_dict["Exchange"]),
        )
    elif row_dict["Type"] in COINTRACKING_W_MAPPING:
        if row_dict["Type"] in ("Stolen", "Lost"):
            sell_value = None
        else:
            sell_value = data_row.row[8]

        data_row.t_record = TransactionOutRecord(
            COINTRACKING_W_MAPPING[row_dict["Type"]],
            data_row.timestamp,
            sell_quantity=row_dict["Sell"],
            sell_asset=data_row.row[6],
            sell_value=sell_value,
            wallet=wallet_name(row_dict["Exchange"]),
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def wallet_name(wallet):
    if not wallet:
        return WALLET
    return wallet


DataParser(
    DataParser.TYPE_ACCOUNTING,
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
