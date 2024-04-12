# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import argparse
import csv
import os
import sys
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional, Union

import _csv
from colorama import Fore

from ..bt_types import TrType, UnmappedType
from ..config import config
from ..constants import FORMAT_RECAP
from .out_record import TransactionOutRecord

if TYPE_CHECKING:
    from .datafile import DataFile


class OutputBase:  # pylint: disable=too-few-public-methods
    DEFAULT_FILENAME = "BittyTax_Records"
    BITTYTAX_OUT_HEADER = [
        "Type",
        "Buy Quantity",
        "Buy Asset",
        "Buy Value in " + config.ccy,
        "Sell Quantity",
        "Sell Asset",
        "Sell Value in " + config.ccy,
        "Fee Quantity",
        "Fee Asset",
        "Fee Value in " + config.ccy,
        "Wallet",
        "Timestamp",
        "Note",
    ]

    def __init__(self, data_files: List["DataFile"]) -> None:
        self.data_files = data_files
        self.filename: Optional[str] = None

    @staticmethod
    def get_output_filename(filename: str, extension_type: str) -> str:
        if filename:
            filepath, file_extension = os.path.splitext(filename)
            if file_extension != extension_type:
                filepath = f"{filepath}.{extension_type}"
        else:
            filepath = f"{OutputBase.DEFAULT_FILENAME}.{extension_type}"

        if not os.path.exists(filepath):
            return filepath

        filepath, file_extension = os.path.splitext(filepath)
        i = 2
        new_fname = f"{filepath}-{i}{file_extension}"
        while os.path.exists(new_fname):
            i += 1
            new_fname = f"{filepath}-{i}{file_extension}"

        return new_fname


class OutputCsv(OutputBase):
    FILE_EXTENSION = "csv"
    RECAP_OUT_HEADER = [
        "Type",
        "Date",
        "InOrBuyAmount",
        "InOrBuyCurrency",
        "OutOrSellAmount",
        "OutOrSellCurrency",
        "FeeAmount",
        "FeeCurrency",
    ]

    RECAP_TYPE_MAPPING = {
        TrType.DEPOSIT: "Deposit",
        TrType.MINING: "Mining",
        TrType.STAKING: "StakingReward",
        TrType.INTEREST: "LoanInterest",
        TrType.DIVIDEND: "Income",
        TrType.INCOME: "Income",
        TrType.GIFT_RECEIVED: "Gift",
        TrType.FORK: "Fork",
        TrType.AIRDROP: "Airdrop",
        TrType.REFERRAL: "Referral",
        TrType.CASHBACK: "Cashback",
        TrType.FEE_REBATE: "FeeRebate",
        TrType.WITHDRAWAL: "Withdrawal",
        TrType.SPEND: "Purchase",
        TrType.GIFT_SENT: "Gift",
        TrType.GIFT_SPOUSE: "Spouse",
        TrType.CHARITY_SENT: "Donation",
        TrType.LOST: "Lost",
        TrType.TRADE: "Trade",
    }

    def __init__(self, data_files: List["DataFile"], args: argparse.Namespace) -> None:
        super().__init__(data_files)
        if args.output_filename:
            self.filename = self.get_output_filename(args.output_filename, self.FILE_EXTENSION)

        self.csv_format = args.format
        self.sort = args.sort
        self.no_header = args.noheader
        self.append_raw_data = args.append

    def out_header(self) -> List[str]:
        if self.csv_format == FORMAT_RECAP:
            return self.RECAP_OUT_HEADER

        return self.BITTYTAX_OUT_HEADER

    def in_header(self, in_header: List[str]) -> List[str]:
        if self.csv_format == FORMAT_RECAP:
            return [name if name not in self.out_header() else name + "_" for name in in_header]

        return in_header

    def write_csv(self) -> None:
        if self.filename:
            with open(self.filename, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file, lineterminator="\n")
                self.write_rows(writer)

            sys.stderr.write(f"{Fore.WHITE}output CSV file created: {Fore.YELLOW}{self.filename}\n")
        else:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
            writer = csv.writer(sys.stdout, lineterminator="\n")
            self.write_rows(writer)

    def write_rows(self, writer: "_csv._writer") -> None:
        data_rows = []
        for data_file in self.data_files:
            data_rows.extend(data_file.data_rows)

        if self.sort:
            data_rows = sorted(data_rows, key=lambda dr: dr.timestamp, reverse=False)

        if not self.no_header:
            if self.append_raw_data:
                writer.writerow(
                    self.out_header() + self.in_header(self.data_files[0].parser.in_header)
                )
            else:
                writer.writerow(self.out_header())

        for data_row in data_rows:
            if self.append_raw_data:
                if data_row.t_record:
                    writer.writerow(self._to_csv(data_row.t_record) + data_row.row)
                else:
                    writer.writerow([None] * len(self.out_header()) + data_row.row)
            else:
                if data_row.t_record:
                    writer.writerow(self._to_csv(data_row.t_record))

    def _to_csv(self, t_record: TransactionOutRecord) -> List[str]:
        if self.csv_format == FORMAT_RECAP:
            return self._to_recap_csv(t_record)

        return self._to_bittytax_csv(t_record)

    @staticmethod
    def _format_type(t_type: Union[TrType, UnmappedType]) -> str:
        if isinstance(t_type, TrType):
            return t_type.value
        return t_type

    @staticmethod
    def _format_decimal(decimal: Optional[Decimal]) -> str:
        if decimal is None:
            return ""
        return f"{decimal.normalize():0f}"

    @staticmethod
    def _format_timestamp(timestamp: datetime) -> str:
        if timestamp.microsecond:
            return f"{timestamp:%Y-%m-%dT%H:%M:%S.%f %Z}"
        return f"{timestamp:%Y-%m-%dT%H:%M:%S %Z}"

    @staticmethod
    def _to_bittytax_csv(tr: TransactionOutRecord) -> List[str]:
        return [
            OutputCsv._format_type(tr.t_type),
            OutputCsv._format_decimal(tr.buy_quantity),
            tr.buy_asset,
            OutputCsv._format_decimal(tr.buy_value),
            OutputCsv._format_decimal(tr.sell_quantity),
            tr.sell_asset,
            OutputCsv._format_decimal(tr.sell_value),
            OutputCsv._format_decimal(tr.fee_quantity),
            tr.fee_asset,
            OutputCsv._format_decimal(tr.fee_value),
            tr.wallet,
            OutputCsv._format_timestamp(tr.timestamp),
            tr.note,
        ]

    @staticmethod
    def _to_recap_csv(tr: TransactionOutRecord) -> List[str]:
        if isinstance(tr.t_type, TrType):
            r_type = OutputCsv.RECAP_TYPE_MAPPING[tr.t_type]
        else:
            r_type = tr.t_type

        return [
            r_type,
            f"{tr.timestamp:%Y-%m-%d %H:%M:%S}",
            OutputCsv._format_decimal(tr.buy_quantity),
            tr.buy_asset,
            OutputCsv._format_decimal(tr.sell_quantity),
            tr.sell_asset,
            OutputCsv._format_decimal(tr.fee_quantity),
            tr.fee_asset,
        ]
