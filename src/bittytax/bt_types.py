# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

from datetime import date, datetime
from enum import Enum
from typing import NewType


class TrType(Enum):
    DEPOSIT = "Deposit"
    MINING = "Mining"
    STAKING = "Staking"
    INTEREST = "Interest"
    DIVIDEND = "Dividend"
    INCOME = "Income"
    GIFT_RECEIVED = "Gift-Received"
    FORK = "Fork"
    AIRDROP = "Airdrop"
    REFERRAL = "Referral"
    CASHBACK = "Cashback"
    FEE_REBATE = "Fee-Rebate"
    WITHDRAWAL = "Withdrawal"
    SPEND = "Spend"
    GIFT_SENT = "Gift-Sent"
    GIFT_SPOUSE = "Gift-Spouse"
    CHARITY_SENT = "Charity-Sent"
    LOST = "Lost"
    TRADE = "Trade"


class DisposalType(Enum):
    SAME_DAY = "Same Day"
    TEN_DAY = "Ten Day"
    BED_AND_BREAKFAST = "Bed & Breakfast"
    SECTION_104 = "Section 104"
    UNPOOLED = "Unpooled"
    NO_GAIN_NO_LOSS = "No Gain/No Loss"
    LONG_TERM = "Long-Term"
    SHORT_TERM = "Short-Term"


BUY_TYPES = (
    TrType.DEPOSIT,
    TrType.MINING,
    TrType.STAKING,
    TrType.INTEREST,
    TrType.DIVIDEND,
    TrType.INCOME,
    TrType.GIFT_RECEIVED,
    TrType.FORK,
    TrType.AIRDROP,
    TrType.REFERRAL,
    TrType.CASHBACK,
    TrType.FEE_REBATE,
    TrType.TRADE,
)

SELL_TYPES = (
    TrType.WITHDRAWAL,
    TrType.SPEND,
    TrType.GIFT_SENT,
    TrType.GIFT_SPOUSE,
    TrType.CHARITY_SENT,
    TrType.LOST,
    TrType.TRADE,
)

UnmappedType = NewType("UnmappedType", str)

AssetSymbol = NewType("AssetSymbol", str)
FixedValue = NewType("FixedValue", bool)
Wallet = NewType("Wallet", str)
Timestamp = NewType("Timestamp", datetime)
Note = NewType("Note", str)

DataSourceName = NewType("DataSourceName", str)
SourceUrl = NewType("SourceUrl", str)

TradingPair = NewType("TradingPair", str)
QuoteSymbol = NewType("QuoteSymbol", str)

AssetId = NewType("AssetId", str)
AssetName = NewType("AssetName", str)

Date = NewType("Date", date)
Year = NewType("Year", int)

FileId = NewType("FileId", str)
