# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Crypto.com"

def parse_crypto_com(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0], dayfirst=True)

    if in_row[9] == "crypto_deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] == "crypto_transfer":
        if Decimal(in_row[3]) > 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[3],
                                                     buy_asset=in_row[2],
                                                     buy_value=get_value(in_row),
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                     data_row.timestamp,
                                                     sell_quantity=abs(Decimal(in_row[3])),
                                                     sell_asset=in_row[2],
                                                     sell_value=get_value(in_row),
                                                     wallet=WALLET)
    elif in_row[9] in ("crypto_earn_interest_paid", "mco_stake_reward"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INCOME,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] in ("viban_purchase", "crypto_exchange", "van_purchase"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=in_row[4],
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] == "referral_bonus":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] in ("crypto_earn_program_created", "crypto_earn_program_withdrawn",
                       "lockup_lock"):
        return
    else:
        raise UnexpectedTypeError(9, parser.in_header[9], in_row[9])

def get_value(in_row):
    if in_row[6] == config.CCY:
        return abs(Decimal(in_row[7]))
    return None

DataParser(DataParser.TYPE_EXCHANGE,
           "Crypto.com",
           ['Timestamp (UTC)', 'Transaction Description', 'Currency', 'Amount', 'To Currency',
            'To Amount', 'Native Currency', 'Native Amount', 'Native Amount (in USD)',
            'Transaction Kind'],
           worksheet_name="Crypto.com",
           row_handler=parse_crypto_com)
