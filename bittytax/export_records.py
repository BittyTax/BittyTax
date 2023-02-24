# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import csv
import os
import sys

from colorama import Fore


class ExportRecords(object):
    DEFAULT_FILENAME = "BittyTax_Export"
    FILE_EXTENSION = "csv"
    OUT_HEADER = [
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

    def __init__(self, transaction_records):
        self.transaction_records = transaction_records

    @staticmethod
    def get_output_filename():
        filepath = ExportRecords.DEFAULT_FILENAME + "." + ExportRecords.FILE_EXTENSION

        if not os.path.exists(filepath):
            return filepath

        filepath, file_extension = os.path.splitext(filepath)
        i = 2
        new_fname = "%s-%s%s" % (filepath, i, file_extension)
        while os.path.exists(new_fname):
            i += 1
            new_fname = "%s-%s%s" % (filepath, i, file_extension)

        return new_fname

    def write_csv(self):
        filename = self.get_output_filename()

        if sys.version_info[0] >= 3:
            with open(filename, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file, lineterminator="\n")
                self.write_rows(writer)
        else:
            with open(filename, "wb") as csv_file:
                writer = csv.writer(csv_file, lineterminator="\n")
                self.write_rows(writer)

        sys.stderr.write("%sexport file created: %s%s\n" % (Fore.WHITE, Fore.YELLOW, filename))

    def write_rows(self, writer):
        writer.writerow(self.OUT_HEADER)

        for tr in self.transaction_records:
            writer.writerow(tr.to_csv())
