# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Crypto.com"

def parse_crypto_com(data_row, parser, filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])
    comment = in_row[1]

    if "fiat" in filename.lower():
        # FIAT wallet export is required for proper FIAT audit.
        if in_row[9] not in ("viban_card_top_up", "viban_withdrawal", "viban_deposit"):
            # We need to ignore the duplicates already found in the "transactions" file.
            return
        if in_row[9] == "viban_card_top_up":
            # Moving from fiat wallet to card wallet requires parsing the "card" csv file. Until someone volunteers to
            # do that accurately, we'll just spend the money on the card.
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                     data_row.timestamp,
                                                     sell_quantity=abs(Decimal(in_row[3])),
                                                     sell_asset=in_row[2],
                                                     sell_value=get_value(in_row),
                                                     wallet=WALLET, note=comment)
            return

    if in_row[9] in ("crypto_transfer", "airdrop_locked"):
        if Decimal(in_row[3]) > 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[3],
                                                     buy_asset=in_row[2],
                                                     buy_value=get_value(in_row),
                                                     wallet=WALLET, note=comment)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_SENT,
                                                     data_row.timestamp,
                                                     sell_quantity=abs(Decimal(in_row[3])),
                                                     sell_asset=in_row[2],
                                                     sell_value=get_value(in_row),
                                                     wallet=WALLET, note=comment)
    elif in_row[9] in ("crypto_earn_interest_paid", "mco_stake_reward",
                       "crypto_earn_extra_interest_paid"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 wallet=WALLET, note=comment)
    elif in_row[9] in ("viban_purchase", "van_purchase",
                       "crypto_viban_exchange", "crypto_exchange"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=in_row[4],
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 wallet=WALLET, note=comment)
    elif in_row[9] in ("crypto_wallet_swap_credited", "crypto_wallet_swap_debited",
                       "interest_swap_credited", "interest_swap_debited",
                       "lockup_swap_credited", "lockup_swap_debited",
                       "dust_conversion_debited",
                       "dust_conversion_credited"):
        if Decimal(in_row[3]) > 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[3],
                                                     buy_asset=in_row[2],
                                                     sell_quantity=0,
                                                     sell_asset=in_row[6],
                                                     wallet=WALLET, note=comment)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=0,
                                                     buy_asset=in_row[6],
                                                     sell_quantity=abs(Decimal(in_row[3])),
                                                     sell_asset=in_row[2],
                                                     wallet=WALLET, note=comment)
    elif in_row[9] == "crypto_purchase":
        # This is a purchase of crypto with a credit card. Do NOT subtract from fiat.
        # For tax purposes, this needs to be a deposit, not a trade with a price of zero.
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 sell_quantity=None,
                                                 sell_asset='',
                                                 wallet=WALLET, note=comment)
    elif in_row[9] in ("referral_bonus", "referral_card_cashback", "referral_commission", "reimbursement",
                       "gift_card_reward", "transfer_cashback", "admin_wallet_credited",
                       "referral_gift", "campaign_reward"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 wallet=WALLET, note=comment)

    elif in_row[9] in ("card_cashback_reverted", "reimbursement_reverted"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_SENT,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 wallet=WALLET, note=comment)
    elif in_row[9] in ("crypto_payment", "card_top_up"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 wallet=WALLET, note=comment)
    elif in_row[9] in ("crypto_withdrawal", "crypto_to_exchange_transfer", "airdrop_to_exchange_transfer",
                       "invest_deposit", "viban_withdrawal"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 wallet=WALLET, note=comment)
    elif in_row[9] in ("crypto_deposit", "exchange_to_crypto_transfer", "invest_withdrawal", "viban_deposit"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 wallet=WALLET, note=comment)
    elif in_row[9] in ("crypto_earn_program_created", "crypto_earn_program_withdrawn",
                     "lockup_lock", "lockup_upgrade", "lockup_unlock",
                     "supercharger_deposit", "supercharger_withdrawal"):
        # These are CDC app specific functions, but the balance remains the same.
        # Only skip app/functionality rows that do not affect your total balance.
        return
    elif in_row[9] in ("dynamic_coin_swap_credited", "dynamic_coin_swap_debited"):
        # This is just information but it doesn't actually change your balance.
        return
    elif in_row[9] == "dynamic_coin_swap_bonus_exchange_deposit":
        # This is a gift created out of thin air and immediately transferred to the exchange.
        # Therefore it's a gift followed by a withdrawal, which requires two records but we only have one.
        # One solution is to ignore this, and leave it up to the exchange audit to mark the deposit as gift.
        return
    elif in_row[9] == "":
        # This is not supposed to happen
        # Could be a fiat transaction
        if "Deposit" in in_row[1]:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[3],
                                                     buy_asset=in_row[2],
                                                     wallet=WALLET, note=comment)
        elif "Withdrawal" in in_row[1]:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                     data_row.timestamp,
                                                     sell_quantity=abs(Decimal(in_row[3])),
                                                     sell_asset=in_row[2],
                                                     wallet=WALLET, note=comment)
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
