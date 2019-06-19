# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
import csv
import copy
from decimal import Decimal

import dateutil.parser

from .config import log, config
from .record import TransactionRecord
from .convert import utf_8_encoder

PRECISION = Decimal('0.00')

def load_transaction_records(import_file):
    log.info("==IMPORT TRANSACTION RECORDS==")
    transaction_records = []

    if sys.version_info[0] < 3:
        # Special handling required for utf-8 encoded csv files
        reader = csv.reader(utf_8_encoder(import_file))
    else:
        reader = csv.reader(import_file)

    next(reader, None) # skip headers
    for row in reader:
        record = _parse_row(row)
        record.validate()
        record.normalise_to_localtime()
        record.include_fees()
        log.debug(record)
        transaction_records.append(record)

    log.info("Total transaction records=%s", len(transaction_records))
    return transaction_records

def _parse_row(row):
    timestamp = dateutil.parser.parse(row[11], tzinfos=config.TZ_INFOS)

    if timestamp.tzinfo is None:
        # Default to UTC if no timezone is specified
        timestamp = timestamp.replace(tzinfo=config.TZ_UTC)

    return TransactionRecord(row[0],
                             timestamp,
                             buy_quantity=_strip_non_digits(row[1]) if row[1] else None,
                             buy_asset=row[2],
                             buy_value=_strip_non_digits(row[3]) if row[3] else None,
                             sell_quantity=_strip_non_digits(row[4]) if row[4] else None,
                             sell_asset=row[5],
                             sell_value=_strip_non_digits(row[6]) if row[6] else None,
                             fee_quantity=_strip_non_digits(row[7]) if row[7] else None,
                             fee_asset=row[8],
                             fee_value=_strip_non_digits(row[9]) if row[9] else None,
                             wallet=row[10])

def _strip_non_digits(string):
    return string.strip('£€$').replace(',', '')

def _format_quantity(quantity):
    if quantity is None:
        return '-'

    return '{:0,f}'.format(quantity.normalize())

def _format_value(value):
    if value is not None:
        return ' (' + config.sym() + '{:0,.2f} {})'.format(value, config.CCY)

    return ''

def _format_pooled(pooled):
    if len(pooled) > 1:
        return " [" + str(len(pooled)) + "]"

    return ''

class TransactionHistory(object):
    def __init__(self, transaction_records):
        self.transaction_records = transaction_records

    def split_transaction_records(self, value_asset):
        log.debug("==SPLIT TRANSACTION RECORDS==")

        transactions = []
        for tr in self.transaction_records:
            if tr.sell_asset and tr.sell_asset not in config.fiat_list:
                value = self.which_asset_value(tr, value_asset)
                sell = Sell(tr.line_num, tr.t_type, tr.wallet, tr.timestamp,
                            tr.sell_quantity, tr.sell_asset, value)
                transactions.append(sell)
                log.debug(sell)

            if tr.buy_asset and tr.buy_asset not in config.fiat_list:
                value = self.which_asset_value(tr, value_asset)
                buy = Buy(tr.line_num, tr.t_type, tr.wallet, tr.timestamp,
                          tr.buy_quantity, tr.buy_asset, value)
                transactions.append(buy)
                log.debug(buy)

        log.debug("Total transactions=%s", len(transactions))
        return transactions

    @staticmethod
    def which_asset_value(tr, value_asset):
        value = None
        if tr.t_type in tr.BUY_TYPES:
            value = value_asset.get_value(tr.buy_asset,
                                          tr.timestamp,
                                          tr.buy_quantity,
                                          tr.buy_value)
        elif tr.t_type in tr.SELL_TYPES:
            value = value_asset.get_value(tr.sell_asset,
                                          tr.timestamp,
                                          tr.sell_quantity,
                                          tr.sell_value)
        elif tr.t_type == tr.TYPE_TRADE:
            if config.trade_asset_type == config.TRADE_ASSET_TYPE_BUY:
                value = value_asset.get_value(tr.buy_asset,
                                              tr.timestamp,
                                              tr.buy_quantity,
                                              tr.buy_value)
            elif config.trade_asset_type == config.TRADE_ASSET_TYPE_SELL:
                value = value_asset.get_value(tr.sell_asset,
                                              tr.timestamp,
                                              tr.sell_quantity,
                                              tr.sell_value)
            else:
                pos_sell_asset = pos_buy_asset = len(config.asset_priority) + 1

                if tr.sell_asset in config.asset_priority:
                    pos_sell_asset = config.asset_priority.index(tr.sell_asset)
                if tr.buy_asset in config.asset_priority:
                    pos_buy_asset = config.asset_priority.index(tr.buy_asset)

                if pos_sell_asset <= pos_buy_asset:
                    value = value_asset.get_value(tr.sell_asset,
                                                  tr.timestamp,
                                                  tr.sell_quantity,
                                                  tr.sell_value)
                else:
                    value = value_asset.get_value(tr.buy_asset,
                                                  tr.timestamp,
                                                  tr.buy_quantity,
                                                  tr.buy_value)
        if value is not None:
            value = value.quantize(PRECISION)

        return value

class TransactionBase(object):
    def __init__(self, tid, t_type, asset, wallet, timestamp):
        self.tid = [tid, 0]
        self.t_type = t_type
        self.asset = asset
        self.wallet = wallet
        self.timestamp = timestamp
        self.matched = False
        self.pooled = []

    def _format_match_status(self):
        return " (M)" if self.matched else ""

    def _format_tid(self):
        if self.tid[1] == 0:
            return str(self.tid[0])
        return str(self.tid[0]) + "." + str(self.tid[1])

    def __eq__(self, other):
        return (self.asset, self.timestamp) == (other.asset, other.timestamp)

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return (self.asset, self.timestamp) < (other.asset, other.timestamp)

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        return result

class Buy(TransactionBase):
    TYPE_DEPOSIT = TransactionRecord.TYPE_DEPOSIT
    TYPE_MINING = TransactionRecord.TYPE_MINING
    TYPE_INCOME = TransactionRecord.TYPE_INCOME
    TYPE_GIFT_RECEIVED = TransactionRecord.TYPE_GIFT_RECEIVED
    TYPE_TRADE = TransactionRecord.TYPE_TRADE

    ACQUISITION_TYPES = {TYPE_MINING, TYPE_INCOME, TYPE_GIFT_RECEIVED, TYPE_TRADE}

    def __init__(self, tid, t_type, wallet, timestamp, buy_quantity, buy_asset, buy_value):
        super(Buy, self).__init__(tid, t_type, buy_asset, wallet, timestamp)
        self.buy_quantity = buy_quantity
        self.cost = buy_value

        self.pooled.append(copy.deepcopy(self))

    def __iadd__(self, other):
        # Pool buys
        if self.asset != other.asset:
            raise Exception
        self.buy_quantity += other.buy_quantity
        self.cost += other.cost

        if other.timestamp < self.timestamp:
            # Keep timestamp of earliest transaction
            self.timestamp = other.timestamp

        if other.wallet != self.wallet:
            self.wallet = "<pooled>"

        self.pooled.append(other)
        return self

    def is_acquisition(self):
        return self.t_type in self.ACQUISITION_TYPES

    def split_buy(self, sell_quantity):
        remainder = copy.deepcopy(self)
        remainder.tid[1] += 1

        self.cost = Decimal(self.cost * (sell_quantity /
                                         self.buy_quantity)).quantize(PRECISION)
        self.buy_quantity = sell_quantity

        remainder.cost = remainder.cost - self.cost
        remainder.buy_quantity = remainder.buy_quantity - sell_quantity

        log.debug("split: %s", self)
        log.debug("split: %s", remainder)

        return remainder

    def __str__(self):
        return "[TID:" + self._format_tid() + "] " + \
               type(self).__name__ + " (" + \
               self.t_type + "): " + \
               _format_quantity(self.buy_quantity) + " " + \
               self.asset + \
               _format_value(self.cost) + " \"" + \
               self.wallet + "\" " + \
               self.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z') + \
               _format_pooled(self.pooled) + \
               self._format_match_status()

class Sell(TransactionBase):
    TYPE_WITHDRAWAL = TransactionRecord.TYPE_WITHDRAWAL
    TYPE_SPEND = TransactionRecord.TYPE_SPEND
    TYPE_GIFT_SENT = TransactionRecord.TYPE_GIFT_SENT
    TYPE_CHARITY_SENT = TransactionRecord.TYPE_CHARITY_SENT
    TYPE_TRADE = TransactionRecord.TYPE_TRADE

    DISPOSAL_TYPES = {TYPE_SPEND, TYPE_GIFT_SENT, TYPE_CHARITY_SENT, TYPE_TRADE}

    def __init__(self, tid, t_type, wallet, timestamp, sell_quantity, sell_asset, sell_value):
        super(Sell, self).__init__(tid, t_type, sell_asset, wallet, timestamp)
        self.sell_quantity = sell_quantity
        self.proceeds = sell_value

        self.pooled.append(copy.deepcopy(self))

    def __iadd__(self, other):
	# Pool sells
        if self.asset != other.asset:
            raise Exception
        self.sell_quantity += other.sell_quantity
        self.proceeds += other.proceeds

        if other.timestamp > self.timestamp:
            # Keep timestamp of latest transaction
            self.timestamp = other.timestamp

        if other.wallet != self.wallet:
            self.wallet = "<pooled>"

        self.pooled.append(other)
        return self

    def is_disposal(self):
        return self.t_type in self.DISPOSAL_TYPES

    def split_sell(self, buy_quantity):
        remainder = copy.deepcopy(self)
        remainder.tid[1] += 1

        self.proceeds = Decimal(self.proceeds * (buy_quantity /
                                                 self.sell_quantity)).quantize(PRECISION)
        self.sell_quantity = buy_quantity

        remainder.proceeds = remainder.proceeds - self.proceeds
        remainder.sell_quantity = remainder.sell_quantity - buy_quantity

        log.debug("split: %s", self)
        log.debug("split: %s", remainder)

        return remainder

    def __str__(self):
        return "[TID:" + self._format_tid() + "] " + \
               type(self).__name__ + " (" + \
               self.t_type + "): " + \
               _format_quantity(self.sell_quantity) + " " + \
               self.asset + \
               _format_value(self.proceeds) + " \"" + \
               self.wallet + "\" " + \
               self.timestamp.strftime('%Y-%m-%dT%H:%M:%S %Z') + \
               _format_pooled(self.pooled) + \
               self._format_match_status()
