# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Crypto.com"


def parse_crypto_com(data_row, parser, filename):
    """
    Use crypto_transactions.svg. If you ever used your fiat wallet, also use crypto_fiat.svg or the audit will fail.
    The headers are the same, so the fiat file will be detected from the name. Don't rename the file (or keep 'fiat').

    IMPORTANT NOTE!

    There is an error in the csv export where any MCO left in "Earn" during the CRO swap around August 2020 does
    not have a corresponding record for the swap to CRO. The first CRO withdrawal from "Earn" after the swap
    divided by the MCO-CRO rate at the time probably shows exactly how much you had in earn. You need to manually
    add a transaction for this using mco_early_swap_value = 27.64389999999996. Only if you had MCO in earn.

    E.g. if your transaction looks like this:
        2020-10-01 01:30:32,Crypto Earn Withdrawal,CRO,8293.17,,,EUR,1080.39,1287.88,crypto_earn_program_withdrawn
    Add the following conversion:
        2020-10-01 01:30:31,MANUAL FIX SWAP STUCK MCO EARN,MCO,-300,CRO,8293.17,EUR,1080.39,1287.88,crypto_exchange
    Or save it to a separate file called crypto_manual_fixes.cvs and load it into bittytax_conv together with the
    transactions.csv and fiat.csv.
    """
    in_row = data_row.in_row
    header = parser.header
    timestamp = data_row.timestamp = DataParser.parse_timestamp(in_row[header.index('Timestamp (UTC)')])
    comment = in_row[header.index('Transaction Description')]
    tx_type = in_row[header.index('Transaction Kind')]
    asset = in_row[header.index('Currency')]
    quantity = in_row[header.index('Amount')]
    to_asset = in_row[header.index('To Currency')]
    to_quantity = in_row[header.index('To Amount')]
    fiat_asset = in_row[header.index('Native Currency')]
    fiat_quantity = abs(Decimal(in_row[header.index('Native Amount')])) if fiat_asset == config.CCY else None

    # Defaults
    t_type = TransactionOutRecord.TYPE_TRADE
    buy_quantity = sell_quantity = fee_quantity = None
    buy_value = sell_value = None
    buy_asset = sell_asset = fee_asset = ''

    if "fiat" in filename.lower():
        # FIAT wallet export is required for proper FIAT audit.
        if tx_type not in ("viban_card_top_up", "viban_withdrawal", "viban_deposit"):
            # We need to ignore the duplicates already found in the "transactions" file.
            return


    if tx_type == "viban_card_top_up":
        # Moving from fiat wallet to card wallet requires parsing the "card" csv file. Until someone volunteers to
        # do that accurately, we'll just spend the money on the card.  
        t_type = TransactionOutRecord.TYPE_SPEND
        sell_quantity = abs(Decimal(quantity))
        sell_asset = asset
        sell_value = fiat_quantity
    elif tx_type in ("crypto_transfer", "airdrop_locked"):
        if Decimal(quantity) > 0:
            t_type = TransactionOutRecord.TYPE_GIFT_RECEIVED
            buy_quantity = quantity
            buy_asset = asset
            buy_value = fiat_quantity
        else:
            t_type = TransactionOutRecord.TYPE_GIFT_SENT
            sell_quantity = abs(Decimal(quantity))
            sell_asset = asset
            sell_value = fiat_quantity
    elif tx_type in ("crypto_earn_interest_paid", "crypto_earn_extra_interest_paid", "mco_stake_reward"):
        t_type = TransactionOutRecord.TYPE_INTEREST
        buy_quantity = quantity
        buy_asset = asset
        buy_value = fiat_quantity
    elif tx_type in ("viban_purchase", "van_purchase",
                     "crypto_viban_exchange", "crypto_exchange"):
        buy_quantity = to_quantity
        buy_asset = to_asset
        sell_quantity = abs(Decimal(quantity))
        sell_asset = asset
        sell_value = fiat_quantity
    elif tx_type in ("crypto_wallet_swap_credited", "crypto_wallet_swap_debited",
                     "interest_swap_credited", "interest_swap_debited",
                     "lockup_swap_credited", "lockup_swap_debited",
                     "dust_conversion_debited",
                     "dust_conversion_credited"):
        if Decimal(quantity) > 0:
            buy_quantity = quantity
            buy_asset = asset
            sell_quantity = 0
            sell_asset = fiat_asset
        else:
            buy_quantity = 0
            buy_asset = fiat_asset
            sell_quantity = abs(Decimal(quantity))
            sell_asset = asset
    elif tx_type == "crypto_purchase":
        # This is a purchase of crypto with a credit card. Do NOT subtract from fiat.
        # For tax purposes, this needs to be a deposit, not a trade with a price of zero.
        t_type = TransactionOutRecord.TYPE_DEPOSIT
        buy_quantity = quantity
        buy_asset = asset
        sell_quantity = None
        sell_asset = ''
    elif tx_type in ("referral_bonus", "referral_card_cashback", "referral_commission", "reimbursement",
                     "gift_card_reward", "transfer_cashback", "admin_wallet_credited",
                     "referral_gift", "campaign_reward"):
        t_type = TransactionOutRecord.TYPE_GIFT_RECEIVED
        buy_quantity = quantity
        buy_asset = asset
        buy_value = fiat_quantity
    elif tx_type in ("card_cashback_reverted", "reimbursement_reverted"):
        t_type = TransactionOutRecord.TYPE_GIFT_SENT
        sell_quantity = abs(Decimal(quantity))
        sell_asset = asset
        sell_value = fiat_quantity
    elif tx_type in ("crypto_payment", "card_top_up"):
        t_type = TransactionOutRecord.TYPE_SPEND
        sell_quantity = abs(Decimal(quantity))
        sell_asset = asset
        sell_value = fiat_quantity
    elif tx_type in ("crypto_withdrawal", "crypto_to_exchange_transfer", "airdrop_to_exchange_transfer",
                     "invest_deposit", "viban_withdrawal"):
        t_type = TransactionOutRecord.TYPE_WITHDRAWAL
        sell_quantity = abs(Decimal(quantity))
        sell_asset = asset
        sell_value = fiat_quantity
    elif tx_type in ("crypto_deposit", "exchange_to_crypto_transfer", "invest_withdrawal", "viban_deposit"):
        t_type = TransactionOutRecord.TYPE_DEPOSIT
        buy_quantity = quantity
        buy_asset = asset
        buy_value = fiat_quantity
    elif tx_type in ("crypto_earn_program_created", "crypto_earn_program_withdrawn",
                     "lockup_lock", "lockup_upgrade", "lockup_unlock",
                     "supercharger_deposit", "supercharger_withdrawal"):
        # These are CDC app specific functions, but the balance remains the same.
        # Only skip app/functionality rows that do not affect your total balance.
        return
    elif tx_type in ("dynamic_coin_swap_credited", "dynamic_coin_swap_debited"):
        # This is just information but it doesn't actually change your balance.
        return
    elif tx_type == "dynamic_coin_swap_bonus_exchange_deposit":
        # This is a gift created out of thin air and immediately transferred to the exchange.
        # Therefore it's a gift followed by a withdrawal, which requires two records but we only have one.
        # One solution is to ignore this, and leave it up to the exchange audit to mark the deposit as gift.
        return
    elif tx_type == "":
        # This is not supposed to happen
        # Could be a fiat transaction
        if "Deposit" in in_row[1]:
            t_type = TransactionOutRecord.TYPE_DEPOSIT
            buy_quantity = quantity
            buy_asset = asset
        elif "Withdrawal" in in_row[1]:
            t_type = TransactionOutRecord.TYPE_WITHDRAWAL
            sell_quantity = abs(Decimal(quantity))
            sell_asset = asset
    else:
        raise UnexpectedTypeError(9, parser.in_header[9], tx_type)

    data_row.t_record = TransactionOutRecord(t_type, timestamp,
                                             buy_quantity, buy_asset, buy_value,
                                             sell_quantity, sell_asset, sell_value,
                                             fee_quantity, fee_asset, None,
                                             WALLET, comment)

DataParser(DataParser.TYPE_EXCHANGE,
           "Crypto.com",
           ['Timestamp (UTC)', 'Transaction Description', 'Currency', 'Amount', 'To Currency',
            'To Amount', 'Native Currency', 'Native Amount', 'Native Amount (in USD)',
            'Transaction Kind'],
           worksheet_name="Crypto.com",
           row_handler=parse_crypto_com)
