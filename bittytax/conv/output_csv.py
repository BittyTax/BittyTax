# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import csv
import sys
import os

from ..config import config
from .out_record import TransactionOutRecord

log = logging.getLogger()

class OutputBase(object):
    DEFAULT_FILENAME = 'BittyTax_Records'
    EXCEL_PRECISION = 15
    BITTYTAX_OUT_HEADER = ['Type',
                           'Buy Quantity', 'Buy Asset', 'Buy Value',
                           'Sell Quantity', 'Sell Asset', 'Sell Value',
                           'Fee Quantity', 'Fee Asset', 'Fee Value',
                           'Wallet', 'Timestamp']

    RECAP_OUT_HEADER = ['Type', 'Date',
                        'InOrBuyAmount', 'InOrBuyCurrency',
                        'OutOrSellAmount', 'OutOrSellCurrency',
                        'FeeAmount', 'FeeCurrency']

    def __init__(self, datafiles):
        self.data_files = datafiles

    def out_header(self):
        if config.args.format == config.FORMAT_RECAP:
            return self.RECAP_OUT_HEADER

        return self.BITTYTAX_OUT_HEADER

    def in_header(self, in_header):
        if config.args.format == config.FORMAT_RECAP:
            return [name if name not in self.out_header()
                    else name + '_' for name in in_header]

        return in_header

    @staticmethod
    def get_output_filename(extension_type):
        if config.args.output_filename:
            filepath, file_extension = os.path.splitext(config.args.output_filename)
            if file_extension != extension_type:
                filepath = filepath + '.' + extension_type
        else:
            filepath = OutputBase.DEFAULT_FILENAME + '.' + extension_type

        if not os.path.exists(filepath):
            return filepath

        filepath, file_extension = os.path.splitext(filepath)
        i = 2
        new_fname = '{}-{}{}'.format(filepath, i, file_extension)
        while os.path.exists(new_fname):
            i += 1
            new_fname = '{}-{}{}'.format(filepath, i, file_extension)

        return new_fname

class OutputCsv(OutputBase):
    FILE_EXTENSION = 'csv'
    RECAP_TYPE_MAPPING = {TransactionOutRecord.TYPE_DEPOSIT: 'Deposit',
                          TransactionOutRecord.TYPE_MINING: 'Mining',
                          TransactionOutRecord.TYPE_INCOME: 'Income',
                          TransactionOutRecord.TYPE_GIFT_RECEIVED: 'Gift',
                          TransactionOutRecord.TYPE_WITHDRAWAL: 'Withdrawal',
                          TransactionOutRecord.TYPE_SPEND: 'Purchase',
                          TransactionOutRecord.TYPE_GIFT_SENT: 'Gift',
                          TransactionOutRecord.TYPE_CHARITY_SENT: 'Donation',
                          TransactionOutRecord.TYPE_TRADE: 'Trade'}
    def write_csv(self):
        if config.args.output_filename:
            filename = self.get_output_filename(self.FILE_EXTENSION)

            if sys.version_info[0] >= 3:
                with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
                    writer = csv.writer(csv_file, lineterminator='\n')
                    self.write_rows(writer)
            else:
                with open(filename, 'wb') as csv_file:
                    writer = csv.writer(csv_file, lineterminator='\n')
                    self.write_rows(writer)

            log.info("Output CSV file created: %s", filename)
        else:
            if sys.version_info[0] >= 3:
                sys.stdout.reconfigure(encoding='utf-8')

            writer = csv.writer(sys.stdout, lineterminator='\n')
            self.write_rows(writer)

    def write_rows(self, writer):
        data_rows = []
        for data_file in self.data_files:
            data_rows.extend(data_file.data_rows)

        if config.args.sort:
            data_rows = sorted(data_rows, key=lambda dr: dr.timestamp, reverse=False)

        if not config.args.noheader:
            if config.args.append:
                writer.writerow(self.out_header() +
                                self.in_header(self.data_files[0].parser.in_header))
            else:
                writer.writerow(self.out_header())

        for data_row in data_rows:
            if config.args.append:
                if data_row.t_record:
                    writer.writerow(self._to_csv(data_row.t_record) + data_row.in_row)
                else:
                    writer.writerow([None] * len(self.out_header()) + data_row.in_row)
            else:
                if data_row.t_record:
                    writer.writerow(self._to_csv(data_row.t_record))

    def _to_csv(self, t_record):
        if config.args.format == config.FORMAT_RECAP:
            return self._to_recap_csv(t_record)

        return self._to_bittytax_csv(t_record)

    @staticmethod
    def _to_bittytax_csv(tr):
        if tr.buy_quantity is not None and \
                len(tr.buy_quantity.normalize().as_tuple().digits) > OutputBase.EXCEL_PRECISION:
            log.warning("%d-digit precision exceeded for Buy Quantity: %s",
                        OutputBase.EXCEL_PRECISION, tr.format_quantity(tr.buy_quantity))

        if tr.sell_quantity is not None and \
                len(tr.sell_quantity.normalize().as_tuple().digits) > OutputBase.EXCEL_PRECISION:
            log.warning("%d-digit precision exceeded for Sell Quantity: %s",
                        OutputBase.EXCEL_PRECISION, tr.format_quantity(tr.sell_quantity))

        if tr.fee_quantity is not None and \
                len(tr.fee_quantity.normalize().as_tuple().digits) > OutputBase.EXCEL_PRECISION:
            log.warning("%d-digit precision exceeded for Fee Quantity: %s",
                        OutputBase.EXCEL_PRECISION, tr.format_quantity(tr.fee_quantity))

        return [tr.t_type,
                '{0:f}'.format(tr.buy_quantity.normalize()) if tr.buy_quantity is not None \
                                                            else None,
                tr.buy_asset,
                '{0:f}'.format(tr.buy_value.normalize()) if tr.buy_value is not None \
                                                         else None,
                '{0:f}'.format(tr.sell_quantity.normalize()) if tr.sell_quantity is not None \
                                                             else None,
                tr.sell_asset,
                '{0:f}'.format(tr.sell_value.normalize()) if tr.sell_value is not None \
                                                          else None,
                '{0:f}'.format(tr.fee_quantity.normalize()) if tr.fee_quantity is not None \
                                                            else None,
                tr.fee_asset,
                '{0:f}'.format(tr.fee_value.normalize()) if tr.fee_value is not None \
                                                         else None,
                tr.wallet,
                tr.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z')]

    @staticmethod
    def _to_recap_csv(tr):
        return [OutputCsv.RECAP_TYPE_MAPPING[tr.t_type],
                tr.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                '{0:f}'.format(tr.buy_quantity.normalize()) if tr.buy_quantity is not None \
                                                            else None,
                tr.buy_asset,
                '{0:f}'.format(tr.sell_quantity.normalize()) if tr.sell_quantity is not None \
                                                             else None,
                tr.sell_asset,
                '{0:f}'.format(tr.fee_quantity.normalize()) if tr.fee_quantity is not None \
                                                            else None,
                tr.fee_asset]
