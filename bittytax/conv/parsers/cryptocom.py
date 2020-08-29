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

    if in_row[9] == "crypto_transfer":
        if Decimal(in_row[3]) > 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[3],
                                                     buy_asset=in_row[2],
                                                     buy_value=get_value(in_row),
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_SENT,
                                                     data_row.timestamp,
                                                     sell_quantity=abs(Decimal(in_row[3])),
                                                     sell_asset=in_row[2],
                                                     sell_value=get_value(in_row),
                                                     wallet=WALLET)
    elif in_row[9] in ("crypto_earn_interest_paid", "mco_stake_reward",
                       "crypto_earn_extra_interest_paid"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INCOME,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] in ("viban_purchase", "crypto_exchange", "van_purchase",
                       "crypto_viban_exchange"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=in_row[4],
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] in ("referral_bonus", "referral_card_cashback", "reimbursement",
                       "gift_card_reward"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 wallet=WALLET)

    elif in_row[9] == "card_cashback_reverted":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_SENT,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] == "crypto_payment":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] == "crypto_to_exchange_transfer":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] in ("crypto_deposit", "exchange_to_crypto_transfer"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] in ("dust_conversion_credited", "dust_conversion_debited"):
        # TBD
        return
    elif in_row[9] in ("crypto_earn_program_created", "crypto_earn_program_withdrawn",
                       "lockup_lock", "lockup_swap_debited"):
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
