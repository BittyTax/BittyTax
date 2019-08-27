# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import csv
import sys

from ..record import TransactionRecordBase
from ..config import config

log = logging.getLogger()

EXCEL_PRECISION = 15

class TransactionOutRecord(TransactionRecordBase):
    RECAP_TYPE_MAPPING = {TransactionRecordBase.TYPE_DEPOSIT: 'Deposit',
                          TransactionRecordBase.TYPE_MINING: 'Mining',
                          TransactionRecordBase.TYPE_INCOME: 'Income',
                          TransactionRecordBase.TYPE_GIFT_RECEIVED: 'Gift',
                          TransactionRecordBase.TYPE_WITHDRAWAL: 'Withdrawal',
                          TransactionRecordBase.TYPE_SPEND: 'Purchase',
                          TransactionRecordBase.TYPE_GIFT_SENT: 'Gift',
                          TransactionRecordBase.TYPE_CHARITY_SENT: 'Donation',
                          TransactionRecordBase.TYPE_TRADE: 'Trade'}

    BITTYTAX_OUT_HEADER = ['Type',
                           'Buy Quantity', 'Buy Asset', 'Buy Value',
                           'Sell Quantity', 'Sell Asset', 'Sell Value',
                           'Fee Quantity', 'Fee Asset', 'Fee Value',
                           'Wallet', 'Timestamp']

    RECAP_OUT_HEADER = ['Type', 'Date',
                        'InOrBuyAmount', 'InOrBuyCurrency',
                        'OutOrSellAmount', 'OutOrSellCurrency',
                        'FeeAmount', 'FeeCurrency']

    def to_csv(self):
        if config.args.format == config.FORMAT_RECAP:
            return self._to_recap()
        else:
            return self._to_bittytax()

    def _to_bittytax(self):
        if self.buy_quantity is not None and \
                len(self.buy_quantity.normalize().as_tuple().digits) > EXCEL_PRECISION:
            log.warning("%d-digit precision exceeded! %s", EXCEL_PRECISION, self)

        if self.sell_quantity is not None and \
                len(self.sell_quantity.normalize().as_tuple().digits) > EXCEL_PRECISION:
            log.warning("%d-digit precision exceeded! %s", EXCEL_PRECISION, self)

        if self.fee_quantity is not None and \
                len(self.fee_quantity.normalize().as_tuple().digits) > EXCEL_PRECISION:
            log.warning("%d-digit precision exceeded! %s", EXCEL_PRECISION, self)

        return [self.t_type,
                '{0:f}'.format(self.buy_quantity) if self.buy_quantity is not None else None,
                self.buy_asset,
                '{0:f}'.format(self.buy_value) if self.buy_value is not None else None,
                '{0:f}'.format(self.sell_quantity) if self.sell_quantity is not None else None,
                self.sell_asset,
                '{0:f}'.format(self.sell_value) if self.sell_value is not None else None,
                '{0:f}'.format(self.fee_quantity) if self.fee_quantity is not None else None,
                self.fee_asset,
                '{0:f}'.format(self.fee_value) if self.fee_value is not None else None,
                self.wallet,
                self.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z')]

    def _to_recap(self):
        return [self.RECAP_TYPE_MAPPING[self.t_type],
                self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                '{0:f}'.format(self.buy_quantity) if self.buy_quantity is not None else None,
                self.buy_asset,
                '{0:f}'.format(self.sell_quantity) if self.sell_quantity is not None else None,
                self.sell_asset,
                '{0:f}'.format(self.fee_quantity) if self.fee_quantity is not None else None,
                self.fee_asset]

    @classmethod
    def out_header(cls):
        if config.args.format == config.FORMAT_RECAP:
            return cls.RECAP_OUT_HEADER
        else:
            return cls.BITTYTAX_OUT_HEADER

    @classmethod
    def in_header(cls, in_header):
        if config.args.format == config.FORMAT_RECAP:
            return [name if name not in cls.out_header() else name + '_' for name in in_header]
        else:
            return in_header

    @classmethod
    def prepend(cls):
        if config.args.format == config.FORMAT_RECAP:
            return True
        else:
            return False

    @classmethod
    def sort_key(cls):
        if config.args.format == config.FORMAT_RECAP:
            return lambda c: c[cls.RECAP_OUT_HEADER.index('Date')]
        else:
            return lambda c: c[-1]

    @classmethod
    def csv_file(cls, all_in_row, t_records, in_header):
        if config.args.append:
            if cls.prepend():
                out_rows = [t_record.to_csv() + in_row if t_record
                            else [None] * len(cls.out_header()) + in_row
                            for in_row, t_record in zip(all_in_row, t_records)]
            else:
                out_rows = [in_row + t_record.to_csv() if t_record else in_row
                            for in_row, t_record in zip(all_in_row, t_records)]
        else:
            out_rows = [t_record.to_csv() for t_record in t_records if t_record]

        if config.args.sort:
            out_rows.sort(key=cls.sort_key(), reverse=False)

        if sys.version_info[0] >= 3:
            sys.stdout.reconfigure(encoding='utf-8')

        writer = csv.writer(sys.stdout, lineterminator='\n')
        if not config.args.noheader:
            if config.args.append:
                if cls.prepend():
                    writer.writerow(cls.out_header() + cls.in_header(in_header))
                else:
                    writer.writerow(cls.in_header(in_header) + cls.out_header())
            else:
                writer.writerow(cls.out_header())

        writer.writerows(out_rows)
