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
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

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
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] in ("viban_purchase", "van_purchase",
                       "crypto_viban_exchange", "crypto_exchange"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=in_row[4],
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] in ("crypto_purchase", "dust_conversion_debited", "dust_conversion_credited"):
        if Decimal(in_row[3]) > 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[3],
                                                     buy_asset=in_row[2],
                                                     sell_quantity=in_row[7],
                                                     sell_asset=in_row[6],
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=abs(Decimal(in_row[7])),
                                                     buy_asset=in_row[6],
                                                     sell_quantity=abs(Decimal(in_row[3])),
                                                     sell_asset=in_row[2],
                                                     wallet=WALLET)
    elif in_row[9] in ("referral_bonus", "referral_card_cashback", "reimbursement",
                       "gift_card_reward", "transfer_cashback", "admin_wallet_credited",
                       "referral_gift", "campaign_reward"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 wallet=WALLET)

    elif in_row[9] in ("card_cashback_reverted", "reimbursement_reverted"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_SENT,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] in ("crypto_payment", "card_top_up"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 wallet=WALLET)
    elif in_row[9] in ("crypto_withdrawal", "crypto_to_exchange_transfer"):
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
    elif in_row[9] in ("crypto_earn_program_created", "crypto_earn_program_withdrawn",
                       "lockup_lock", "lockup_upgrade",
                       "lockup_swap_credited", "lockup_swap_debited",
                       "dynamic_coin_swap_credited", "dynamic_coin_swap_debited",
                       "dynamic_coin_swap_bonus_exchange_deposit",
                       "interest_swap_credited", "interest_swap_debited",
                       "crypto_wallet_swap_credited", "crypto_wallet_swap_debited",
                       "supercharger_deposit", "supercharger_withdrawal"):
        return
    elif in_row[9] == "":
        # Could be a fiat transaction
        if "Deposit" in in_row[1]:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[3],
                                                     buy_asset=in_row[2],
                                                     wallet=WALLET)
        elif "Withdrawal" in in_row[1]:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                     data_row.timestamp,
                                                     sell_quantity=abs(Decimal(in_row[3])),
                                                     sell_asset=in_row[2],
                                                     wallet=WALLET)
    else:
        raise UnexpectedTypeError(9, parser.in_header[9], in_row[9])

def get_value(in_row):
    if in_row[6] == config.ccy:
        return abs(Decimal(in_row[7]))
    return None

DataParser(DataParser.TYPE_EXCHANGE,
           "Crypto.com",
           ['Timestamp (UTC)', 'Transaction Description', 'Currency', 'Amount', 'To Currency',
            'To Amount', 'Native Currency', 'Native Amount', 'Native Amount (in USD)',
            'Transaction Kind'],
           worksheet_name="Crypto.com",
           row_handler=parse_crypto_com)
