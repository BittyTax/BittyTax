# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import sys
from decimal import Decimal

from colorama import Fore, Back

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Celsius"


def parse_celsius(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[1])

    if in_row[8] != "Yes" and not config.args.unconfirmed:
        sys.stderr.write("%srow[%s] %s\n" % (
            Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
        sys.stderr.write("%sWARNING%s Skipping unconfirmed transaction, "
                         "use the [-uc] option to include it\n" % (
                             Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW))
        return

    transaction_type = in_row[2]
    symbol = in_row[3]
    quantity = Decimal(in_row[4])
    value = abs(Decimal(in_row[5])) if config.CCY == "USD" else None

    if transaction_type == "deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=quantity,
                                                 buy_asset=symbol,
                                                 wallet=WALLET)

    elif transaction_type == "interest":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                 data_row.timestamp,
                                                 buy_quantity=quantity,
                                                 buy_asset=symbol,
                                                 buy_value=value,
                                                 wallet=WALLET)

    elif transaction_type in ("referred_award", "referrer_award", "promo_code_reward"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=quantity,
                                                 buy_asset=symbol,
                                                 buy_value=value,
                                                 wallet=WALLET)

    elif transaction_type == "withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(quantity),
                                                 sell_asset=symbol,
                                                 wallet=WALLET)

    else:
        raise UnexpectedTypeError(2, parser.in_header[2], transaction_type)


DataParser(DataParser.TYPE_WALLET,
           "Celsius",
           ['Internal id', ' Date and time', ' Transaction type', ' Coin type', ' Coin amount',
            ' USD Value', ' Original Interest Coin', ' Interest Amount In Original Coin', ' Confirmed'],
           worksheet_name="Celsius",
           row_handler=parse_celsius)
