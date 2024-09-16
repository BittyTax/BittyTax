# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

from datetime import date, datetime
from enum import Enum
from typing import NewType


class TrType(Enum):
    DEPOSIT = "Deposit"
    UNSTAKE = "Unstake"
    MINING = "Mining"
    STAKING_REWARD = "Staking-Reward"
    STAKING = "Staking"  # Deprecated
    INTEREST = "Interest"
    DIVIDEND = "Dividend"
    INCOME = "Income"
    GIFT_RECEIVED = "Gift-Received"
    FORK = "Fork"
    AIRDROP = "Airdrop"
    REFERRAL = "Referral"
    CASHBACK = "Cashback"
    FEE_REBATE = "Fee-Rebate"
    LOAN = "Loan"
    MARGIN_GAIN = "Margin-Gain"
    WITHDRAWAL = "Withdrawal"
    STAKE = "Stake"
    SPEND = "Spend"
    GIFT_SENT = "Gift-Sent"
    GIFT_SPOUSE = "Gift-Spouse"
    CHARITY_SENT = "Charity-Sent"
    LOST = "Lost"
    LOAN_REPAYMENT = "Loan-Repayment"
    LOAN_INTEREST = "Loan-Interest"
    MARGIN_LOSS = "Margin-Loss"
    MARGIN_FEE = "Margin-Fee"
    TRADE = "Trade"
    SWAP = "Swap"
    CRYPTO_CRYPTO = 'crypto-crypto'


class DisposalType(Enum):
    SAME_DAY = "Same Day"
    TEN_DAY = "Ten Day"
    BED_AND_BREAKFAST = "Bed & Breakfast"
    SECTION_104 = "Section 104"
    UNPOOLED = "Unpooled"
    NO_GAIN_NO_LOSS = "No Gain/No Loss"
    LONG_TERM = "Long-Term"
    SHORT_TERM = "Short-Term"


class TrRecordPart(Enum):
    BUY = "Buy"
    SELL = "Sell"
    FEE = "Fee"


BUY_TYPES = (
    TrType.DEPOSIT,
    TrType.UNSTAKE,
    TrType.MINING,
    TrType.STAKING_REWARD,
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
    TrType.LOAN,
    TrType.MARGIN_GAIN,
    TrType.TRADE,
    TrType.SWAP,
    TrType.CRYPTO_CRYPTO,
)

SELL_TYPES = (
    TrType.WITHDRAWAL,
    TrType.STAKE,
    TrType.SPEND,
    TrType.GIFT_SENT,
    TrType.GIFT_SPOUSE,
    TrType.CHARITY_SENT,
    TrType.LOST,
    TrType.LOAN_REPAYMENT,
    TrType.LOAN_INTEREST,
    TrType.MARGIN_LOSS,
    TrType.MARGIN_FEE,
    TrType.TRADE,
    TrType.SWAP,
    TrType.CRYPTO_CRYPTO,
)

BUY_AND_SELL_TYPES = [t for t in BUY_TYPES if t in SELL_TYPES]

TRANSFER_TYPES = (TrType.DEPOSIT, TrType.WITHDRAWAL)

DEPRECATED_TYPES = (TrType.STAKING,)

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
