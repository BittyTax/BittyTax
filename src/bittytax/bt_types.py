# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

from datetime import date, datetime
from enum import Enum
from typing import NewType


class TaxRules(Enum):
    UK_INDIVIDUAL = "UK Individual"
    UK_COMPANY_JAN = "UK Company (Jan)"
    UK_COMPANY_FEB = "UK Company (Feb)"
    UK_COMPANY_MAR = "UK Company (Mar)"
    UK_COMPANY_APR = "UK Company (Apr)"
    UK_COMPANY_MAY = "UK Company (May)"
    UK_COMPANY_JUN = "UK Company (Jun)"
    UK_COMPANY_JUL = "UK Company (Jul)"
    UK_COMPANY_AUG = "UK Company (Aug)"
    UK_COMPANY_SEP = "UK Company (Sep)"
    UK_COMPANY_OCT = "UK Company (Oct)"
    UK_COMPANY_NOV = "UK Company (Nov)"
    UK_COMPANY_DEC = "UK Company (Dec)"


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
    LOAN = "Loan"
    MARGIN_GAIN = "Margin-Gain"
    MARGIN_FEE_REBATE = "Margin-Fee-Rebate"
    WITHDRAWAL = "Withdrawal"
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


class DisposalType(Enum):
    SAME_DAY = "Same Day"
    TEN_DAY = "Ten Day"
    BED_AND_BREAKFAST = "Bed & Breakfast"
    SECTION_104 = "Section 104"
    UNPOOLED = "Unpooled"
    NO_GAIN_NO_LOSS = "No Gain/No Loss"


class TrRecordPart(Enum):
    BUY = "Buy"
    SELL = "Sell"
    FEE = "Fee"


TAX_RULES_UK_COMPANY = [
    TaxRules.UK_COMPANY_JAN,
    TaxRules.UK_COMPANY_FEB,
    TaxRules.UK_COMPANY_MAR,
    TaxRules.UK_COMPANY_APR,
    TaxRules.UK_COMPANY_MAY,
    TaxRules.UK_COMPANY_JUN,
    TaxRules.UK_COMPANY_JUL,
    TaxRules.UK_COMPANY_AUG,
    TaxRules.UK_COMPANY_SEP,
    TaxRules.UK_COMPANY_OCT,
    TaxRules.UK_COMPANY_NOV,
    TaxRules.UK_COMPANY_DEC,
]

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
    TrType.LOAN,
    TrType.MARGIN_GAIN,
    TrType.MARGIN_FEE_REBATE,
    TrType.TRADE,
)

SELL_TYPES = (
    TrType.WITHDRAWAL,
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
)

TRANSFER_TYPES = (TrType.DEPOSIT, TrType.WITHDRAWAL)

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
