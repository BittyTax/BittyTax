# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Dict, List, NamedTuple, Optional

import dateutil.parser
from colorama import Back, Fore

from .bt_types import AssetSymbol, Note, Timestamp, TrType, Wallet
from .config import config
from .constants import TZ_UTC
from .exceptions import (
    DataValueError,
    MissingDataError,
    TimestampParserError,
    TransactionParserError,
    UnexpectedDataError,
    UnexpectedTransactionTypeError,
)
from .t_record import TransactionRecord
from .tax import TaxCalculator
from .transactions import Buy, Sell


class FieldRequired(Enum):
    OPTIONAL = "Optional"
    MANDATORY = "Mandatory"
    NOT_REQUIRED = "Not Required"


class FieldValidation(NamedTuple):
    t_type: FieldRequired
    buy_quantity: FieldRequired
    buy_asset: FieldRequired
    buy_value: FieldRequired
    sell_quantity: FieldRequired
    sell_asset: FieldRequired
    sell_value: FieldRequired
    fee_quantity: FieldRequired
    fee_asset: FieldRequired
    fee_value: FieldRequired


@dataclass
class TxRaw:
    tx_hash: str = ""
    tx_src: str = ""
    tx_dest: str = ""


class TransactionRow:
    HEADER = [
        "Type",
        "Buy Quantity",
        "Buy Asset",
        "Buy Value",
        "Sell Quantity",
        "Sell Asset",
        "Sell Value",
        "Fee Quantity",
        "Fee Asset",
        "Fee Value",
        "Wallet",
        "Timestamp",
        "Note",
    ]

    TYPE_VALIDATION: Dict[TrType, FieldValidation] = {
        TrType.DEPOSIT: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.UNSTAKE: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.MINING: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.STAKING_REWARD: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.STAKING: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.INTEREST: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.DIVIDEND: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.INCOME: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.GIFT_RECEIVED: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.FORK: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.AIRDROP: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.REFERRAL: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.CASHBACK: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.FEE_REBATE: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.NOT_REQUIRED,
            sell_asset=FieldRequired.NOT_REQUIRED,
            sell_value=FieldRequired.NOT_REQUIRED,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.WITHDRAWAL: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.NOT_REQUIRED,
            buy_asset=FieldRequired.NOT_REQUIRED,
            buy_value=FieldRequired.NOT_REQUIRED,
            sell_quantity=FieldRequired.MANDATORY,
            sell_asset=FieldRequired.MANDATORY,
            sell_value=FieldRequired.OPTIONAL,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.STAKE: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.NOT_REQUIRED,
            buy_asset=FieldRequired.NOT_REQUIRED,
            buy_value=FieldRequired.NOT_REQUIRED,
            sell_quantity=FieldRequired.MANDATORY,
            sell_asset=FieldRequired.MANDATORY,
            sell_value=FieldRequired.OPTIONAL,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.SPEND: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.NOT_REQUIRED,
            buy_asset=FieldRequired.NOT_REQUIRED,
            buy_value=FieldRequired.NOT_REQUIRED,
            sell_quantity=FieldRequired.MANDATORY,
            sell_asset=FieldRequired.MANDATORY,
            sell_value=FieldRequired.OPTIONAL,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.GIFT_SENT: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.NOT_REQUIRED,
            buy_asset=FieldRequired.NOT_REQUIRED,
            buy_value=FieldRequired.NOT_REQUIRED,
            sell_quantity=FieldRequired.MANDATORY,
            sell_asset=FieldRequired.MANDATORY,
            sell_value=FieldRequired.OPTIONAL,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.GIFT_SPOUSE: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.NOT_REQUIRED,
            buy_asset=FieldRequired.NOT_REQUIRED,
            buy_value=FieldRequired.NOT_REQUIRED,
            sell_quantity=FieldRequired.MANDATORY,
            sell_asset=FieldRequired.MANDATORY,
            sell_value=FieldRequired.OPTIONAL,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.CHARITY_SENT: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.NOT_REQUIRED,
            buy_asset=FieldRequired.NOT_REQUIRED,
            buy_value=FieldRequired.NOT_REQUIRED,
            sell_quantity=FieldRequired.MANDATORY,
            sell_asset=FieldRequired.MANDATORY,
            sell_value=FieldRequired.OPTIONAL,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.LOST: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.NOT_REQUIRED,
            buy_asset=FieldRequired.NOT_REQUIRED,
            buy_value=FieldRequired.NOT_REQUIRED,
            sell_quantity=FieldRequired.MANDATORY,
            sell_asset=FieldRequired.MANDATORY,
            sell_value=FieldRequired.OPTIONAL,
            fee_quantity=FieldRequired.NOT_REQUIRED,
            fee_asset=FieldRequired.NOT_REQUIRED,
            fee_value=FieldRequired.NOT_REQUIRED,
        ),
        TrType.TRADE: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.MANDATORY,
            sell_asset=FieldRequired.MANDATORY,
            sell_value=FieldRequired.OPTIONAL,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
        TrType.SWAP: FieldValidation(
            t_type=FieldRequired.MANDATORY,
            buy_quantity=FieldRequired.MANDATORY,
            buy_asset=FieldRequired.MANDATORY,
            buy_value=FieldRequired.OPTIONAL,
            sell_quantity=FieldRequired.MANDATORY,
            sell_asset=FieldRequired.MANDATORY,
            sell_value=FieldRequired.OPTIONAL,
            fee_quantity=FieldRequired.OPTIONAL,
            fee_asset=FieldRequired.OPTIONAL,
            fee_value=FieldRequired.OPTIONAL,
        ),
    }

    TRANSFER_TYPES = (TrType.DEPOSIT, TrType.WITHDRAWAL)

    def __init__(
        self,
        row: List[str],
        row_num: int,
        filename: Optional[str] = None,
        worksheet_name: Optional[str] = None,
    ):
        self.row = row
        self.row_dict = dict(zip(self.HEADER, row))
        self.row_num = row_num
        self.filename = filename
        self.worksheet_name = worksheet_name
        self.t_record: Optional[TransactionRecord] = None
        self.tx_raw: Optional[TxRaw] = None
        self.failure: Optional[TransactionParserError] = None

    def parse(self) -> None:
        if all(not self.row[i] for i in range(len(self.row) - 1)):
            # Skip empty rows
            return

        buy = sell = fee = None
        try:
            t_type = TrType(self.row_dict["Type"])
        except ValueError as e:
            raise UnexpectedTransactionTypeError(
                self.HEADER.index("Type"), "Type", self.row_dict["Type"]
            ) from e

        buy_quantity = sell_quantity = fee_quantity = None
        buy_asset = sell_asset = fee_asset = AssetSymbol("")
        buy_value = sell_value = fee_value = None

        for pos, required in enumerate(self.TYPE_VALIDATION[t_type]):
            if pos == self.HEADER.index("Buy Quantity"):
                buy_quantity = self.validate_quantity("Buy Quantity", required)
            elif pos == self.HEADER.index("Buy Asset"):
                buy_asset = self.validate_asset("Buy Asset", required)
            elif pos == self.HEADER.index("Buy Value"):
                buy_value = self.validate_value("Buy Value", required)
            elif pos == self.HEADER.index("Sell Quantity"):
                sell_quantity = self.validate_quantity("Sell Quantity", required)
            elif pos == self.HEADER.index("Sell Asset"):
                sell_asset = self.validate_asset("Sell Asset", required)
            elif pos == self.HEADER.index("Sell Value"):
                sell_value = self.validate_value("Sell Value", required)
            elif pos == self.HEADER.index("Fee Quantity"):
                fee_quantity = self.validate_quantity("Fee Quantity", required)
            elif pos == self.HEADER.index("Fee Asset"):
                fee_asset = self.validate_asset("Fee Asset", required)
            elif pos == self.HEADER.index("Fee Value"):
                fee_value = self.validate_value("Fee Value", required)

        if buy_value and buy_asset == config.ccy and buy_value != buy_quantity:
            raise DataValueError(self.HEADER.index("Buy Value"), "Buy Value", buy_value)

        if sell_value and sell_asset == config.ccy and sell_value != sell_quantity:
            raise DataValueError(self.HEADER.index("Sell Value"), "Sell Value", sell_value)

        if fee_value and fee_asset == config.ccy and fee_value != fee_quantity:
            raise DataValueError(self.HEADER.index("Fee Value"), "Fee Value", fee_value)

        if fee_quantity is not None and not fee_asset:
            raise MissingDataError(self.HEADER.index("Fee Asset"), "Fee Asset")

        if fee_quantity is None and fee_asset:
            raise MissingDataError(self.HEADER.index("Fee Quantity"), "Fee Quantity")

        if buy_asset:
            if buy_quantity is None:
                raise RuntimeError("Missing buy_quantity")

            if t_type is TrType.FORK:
                if t_type not in TaxCalculator.INCOME_TYPES:
                    buy_value = Decimal(0)

            buy = Buy(t_type, buy_quantity, buy_asset, buy_value)
        if sell_asset:
            if sell_quantity is None:
                raise RuntimeError("Missing sell_quantity")

            if t_type is TrType.LOST:
                if t_type not in TaxCalculator.NO_GAIN_NO_LOSS_TYPES:
                    if sell_value is None:
                        sell_value = Decimal(0)

                sell = Sell(t_type, sell_quantity, sell_asset, sell_value)
                if config.lost_buyback:
                    buy = Buy(t_type, sell_quantity, sell_asset, sell_value)
                    buy.acquisition = True
            else:
                sell = Sell(t_type, sell_quantity, sell_asset, sell_value)
        if fee_asset:
            if fee_quantity is None:
                raise RuntimeError("Missing fee_quantity")

            # Fees are added as a separate spend transaction
            fee = Sell(TrType.SPEND, fee_quantity, fee_asset, fee_value)

            # Transfers fees are a special case
            if t_type in self.TRANSFER_TYPES:
                if config.transfers_include:
                    # Not a disposal, fees removed from the pool at zero cost
                    fee.disposal = False
                else:
                    # Not a disposal (unless configured otherwise)
                    if not config.transfer_fee_disposal:
                        fee.disposal = False

        self.t_record = TransactionRecord(
            t_type,
            buy,
            sell,
            fee,
            Wallet(self.row_dict["Wallet"]),
            self.parse_timestamp(),
            Note(self.row_dict["Note"]),
            self,
        )

    def parse_timestamp(self) -> Timestamp:
        try:
            timestamp = dateutil.parser.parse(self.row_dict["Timestamp"])
        except ValueError as e:
            raise TimestampParserError(
                self.HEADER.index("Timestamp"), "Timestamp", self.row_dict["Timestamp"]
            ) from e

        if timestamp.tzinfo is None:
            # Default to UTC if no timezone is specified
            timestamp = timestamp.replace(tzinfo=TZ_UTC)

        return Timestamp(timestamp)

    def validate_quantity(self, quantity_hdr: str, required: FieldRequired) -> Optional[Decimal]:
        if self.row_dict[quantity_hdr]:
            if required is FieldRequired.NOT_REQUIRED:
                raise UnexpectedDataError(
                    self.HEADER.index(quantity_hdr),
                    quantity_hdr,
                    self.row_dict[quantity_hdr],
                )

            try:
                quantity = Decimal(self.strip_non_digits(self.row_dict[quantity_hdr]))
            except InvalidOperation as e:
                raise DataValueError(
                    self.HEADER.index(quantity_hdr),
                    quantity_hdr,
                    self.row_dict[quantity_hdr],
                ) from e

            if quantity < 0:
                raise DataValueError(self.HEADER.index(quantity_hdr), quantity_hdr, quantity)
            return quantity

        if required is FieldRequired.MANDATORY:
            raise MissingDataError(self.HEADER.index(quantity_hdr), quantity_hdr)

        return None

    def validate_asset(self, asset_hdr: str, required: FieldRequired) -> AssetSymbol:
        if self.row_dict[asset_hdr]:
            if required is FieldRequired.NOT_REQUIRED:
                raise UnexpectedDataError(
                    self.HEADER.index(asset_hdr), asset_hdr, self.row_dict[asset_hdr]
                )

            return AssetSymbol(self.row_dict[asset_hdr])

        if required is FieldRequired.MANDATORY:
            raise MissingDataError(self.HEADER.index(asset_hdr), asset_hdr)

        return AssetSymbol("")

    def validate_value(self, value_hdr: str, required: FieldRequired) -> Optional[Decimal]:
        if self.row_dict[value_hdr]:
            if required is FieldRequired.NOT_REQUIRED:
                raise UnexpectedDataError(
                    self.HEADER.index(value_hdr), value_hdr, self.row_dict[value_hdr]
                )

            try:
                value = Decimal(self.strip_non_digits(self.row_dict[value_hdr]))
            except InvalidOperation as e:
                raise DataValueError(
                    self.HEADER.index(value_hdr),
                    value_hdr,
                    self.row_dict[value_hdr],
                ) from e

            if value < 0:
                raise DataValueError(self.HEADER.index(value_hdr), value_hdr, value)

            return value

        if required is FieldRequired.MANDATORY:
            raise MissingDataError(self.HEADER.index(value_hdr), value_hdr)

        return None

    @staticmethod
    def strip_non_digits(string: str) -> str:
        return string.strip("£€$").replace(",", "")

    def __str__(self) -> str:
        if self.t_record and self.t_record.tid:
            tid_str = f" {Fore.MAGENTA}[TID:{self.t_record.tid[0]}]"
        else:
            tid_str = ""

        if self.worksheet_name:
            worksheet_str = f"'{self.worksheet_name}' "
        else:
            worksheet_str = ""

        row_str = ", ".join(
            [
                (
                    f"{Back.RED}'{data}'{Back.RESET}"
                    if self.failure and self.failure.col_num == num
                    else f"'{data}'"
                )
                for num, data in enumerate(self.row)
            ]
        )

        return f"{worksheet_str}row[{self.row_num}] [{row_str}]{tid_str}"
