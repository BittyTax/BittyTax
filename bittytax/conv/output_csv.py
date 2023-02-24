# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import csv
import os
import sys

from colorama import Back, Fore

from ..config import config
from .out_record import TransactionOutRecord


class OutputBase(object):  # pylint: disable=too-few-public-methods
    DEFAULT_FILENAME = "BittyTax_Records"
    EXCEL_PRECISION = 15
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

    def __init__(self, data_files):
        self.data_files = data_files

    @staticmethod
    def get_output_filename(filename, extension_type):
        if filename:
            filepath, file_extension = os.path.splitext(filename)
            if file_extension != extension_type:
                filepath = filepath + "." + extension_type
        else:
            filepath = OutputBase.DEFAULT_FILENAME + "." + extension_type

        if not os.path.exists(filepath):
            return filepath

        filepath, file_extension = os.path.splitext(filepath)
        i = 2
        new_fname = "%s-%s%s" % (filepath, i, file_extension)
        while os.path.exists(new_fname):
            i += 1
            new_fname = "%s-%s%s" % (filepath, i, file_extension)

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
        TransactionOutRecord.TYPE_DEPOSIT: "Deposit",
        TransactionOutRecord.TYPE_MINING: "Mining",
        TransactionOutRecord.TYPE_STAKING: "StakingReward",
        TransactionOutRecord.TYPE_INTEREST: "LoanInterest",
        TransactionOutRecord.TYPE_DIVIDEND: "Income",
        TransactionOutRecord.TYPE_INCOME: "Income",
        TransactionOutRecord.TYPE_GIFT_RECEIVED: "Gift",
        TransactionOutRecord.TYPE_AIRDROP: "Airdrop",
        TransactionOutRecord.TYPE_WITHDRAWAL: "Withdrawal",
        TransactionOutRecord.TYPE_SPEND: "Purchase",
        TransactionOutRecord.TYPE_GIFT_SENT: "Gift",
        TransactionOutRecord.TYPE_GIFT_SPOUSE: "Spouse",
        TransactionOutRecord.TYPE_CHARITY_SENT: "Donation",
        TransactionOutRecord.TYPE_LOST: "Lost",
        TransactionOutRecord.TYPE_TRADE: "Trade",
    }

    def __init__(self, data_files, args):
        super(OutputCsv, self).__init__(data_files)
        if args.output_filename:
            self.filename = self.get_output_filename(args.output_filename, self.FILE_EXTENSION)
        else:
            self.filename = None

        self.csv_format = args.format
        self.sort = args.sort
        self.no_header = args.noheader
        self.append_raw_data = args.append

    def out_header(self):
        if self.csv_format == config.FORMAT_RECAP:
            return self.RECAP_OUT_HEADER

        return self.BITTYTAX_OUT_HEADER

    def in_header(self, in_header):
        if self.csv_format == config.FORMAT_RECAP:
            return [name if name not in self.out_header() else name + "_" for name in in_header]

        return in_header

    def write_csv(self):
        if self.filename:
            if sys.version_info[0] >= 3:
                with open(self.filename, "w", newline="", encoding="utf-8") as csv_file:
                    writer = csv.writer(csv_file, lineterminator="\n")
                    self.write_rows(writer)
            else:
                with open(self.filename, "wb") as csv_file:
                    writer = csv.writer(csv_file, lineterminator="\n")
                    self.write_rows(writer)

            sys.stderr.write(
                "%soutput CSV file created: %s%s\n" % (Fore.WHITE, Fore.YELLOW, self.filename)
            )
        else:
            if sys.version_info[0] > 3:
                sys.stdout.reconfigure(encoding="utf-8")

            writer = csv.writer(sys.stdout, lineterminator="\n")
            self.write_rows(writer)

    def write_rows(self, writer):
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

    def _to_csv(self, t_record):
        if self.csv_format == config.FORMAT_RECAP:
            return self._to_recap_csv(t_record)

        return self._to_bittytax_csv(t_record)

    @staticmethod
    def _format_timestamp(timestamp):
        if timestamp.microsecond:
            return timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f %Z")
        return timestamp.strftime("%Y-%m-%dT%H:%M:%S %Z")

    @staticmethod
    def _to_bittytax_csv(tr):
        if (
            tr.buy_quantity is not None
            and len(tr.buy_quantity.normalize().as_tuple().digits) > OutputBase.EXCEL_PRECISION
        ):
            sys.stderr.write(
                "%sWARNING%s %d-digit precision exceeded for Buy Quantity: %s%s\n"
                % (
                    Back.YELLOW + Fore.BLACK,
                    Back.RESET + Fore.YELLOW,
                    OutputBase.EXCEL_PRECISION,
                    tr.format_quantity(tr.buy_quantity),
                    Fore.RESET,
                )
            )

        if (
            tr.sell_quantity is not None
            and len(tr.sell_quantity.normalize().as_tuple().digits) > OutputBase.EXCEL_PRECISION
        ):
            sys.stderr.write(
                "%sWARNING%s %d-digit precision exceeded for Sell Quantity: %s%s\n"
                % (
                    Back.YELLOW + Fore.BLACK,
                    Back.RESET + Fore.YELLOW,
                    OutputBase.EXCEL_PRECISION,
                    tr.format_quantity(tr.sell_quantity),
                    Fore.RESET,
                )
            )

        if (
            tr.fee_quantity is not None
            and len(tr.fee_quantity.normalize().as_tuple().digits) > OutputBase.EXCEL_PRECISION
        ):
            sys.stderr.write(
                "%sWARNING%s %d-digit precision exceeded for Fee Quantity: %s%s\n"
                % (
                    Back.YELLOW + Fore.BLACK,
                    Back.RESET + Fore.YELLOW,
                    OutputBase.EXCEL_PRECISION,
                    tr.format_quantity(tr.fee_quantity),
                    Fore.RESET,
                )
            )
        return [
            tr.t_type,
            "{0:f}".format(tr.buy_quantity.normalize()) if tr.buy_quantity is not None else None,
            tr.buy_asset,
            "{0:f}".format(tr.buy_value.normalize()) if tr.buy_value is not None else None,
            "{0:f}".format(tr.sell_quantity.normalize()) if tr.sell_quantity is not None else None,
            tr.sell_asset,
            "{0:f}".format(tr.sell_value.normalize()) if tr.sell_value is not None else None,
            "{0:f}".format(tr.fee_quantity.normalize()) if tr.fee_quantity is not None else None,
            tr.fee_asset,
            "{0:f}".format(tr.fee_value.normalize()) if tr.fee_value is not None else None,
            tr.wallet,
            OutputCsv._format_timestamp(tr.timestamp),
            tr.note,
        ]

    @staticmethod
    def _to_recap_csv(tr):
        return [
            OutputCsv.RECAP_TYPE_MAPPING[tr.t_type],
            tr.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "{0:f}".format(tr.buy_quantity.normalize()) if tr.buy_quantity is not None else None,
            tr.buy_asset,
            "{0:f}".format(tr.sell_quantity.normalize()) if tr.sell_quantity is not None else None,
            tr.sell_asset,
            "{0:f}".format(tr.fee_quantity.normalize()) if tr.fee_quantity is not None else None,
            tr.fee_asset,
        ]
