# -*- coding: utf-8 -*-

import sys
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from decimal import Decimal

WALLET = "StakeTax"

# Stake.tax default csv
# timestamp,tx_type,taxable,received_amount,received_currency,sent_amount,sent_currency,fee,fee_currency,comment,txid,url,exchange,wallet_address

def parse_staketax(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['timestamp'])

    if row_dict['tx_type'] in ["TRADE", "_BOND"]:        
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['received_amount'],
                                                 buy_asset=row_dict['received_currency'],
                                                 sell_quantity=row_dict['sent_amount'],
                                                 sell_asset=row_dict['sent_currency'],
                                                 fee_quantity=row_dict['fee'],
                                                 fee_asset=row_dict['fee_currency'],                                                 
                                                 wallet=wallet_name(row_dict['wallet_address']))
    elif row_dict['tx_type'] in ["_LP_DEPOSIT", "_LP_WITHDRAW"]:
        if len(row_dict['fee_currency']) > 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['received_amount'],
                                                 buy_asset=row_dict['received_currency'],
                                                 sell_quantity=row_dict['sent_amount'],
                                                 sell_asset=row_dict['sent_currency'],
                                                 fee_quantity=row_dict['fee'],
                                                 fee_asset=row_dict['fee_currency'],                                                                                                                                        
                                                 wallet=wallet_name(row_dict['wallet_address']))
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['received_amount'],
                                                 buy_asset=row_dict['received_currency'],
                                                 sell_quantity=row_dict['sent_amount'],
                                                 sell_asset=row_dict['sent_currency'],                                                 
                                                 wallet=wallet_name(row_dict['wallet_address']))

    elif row_dict['tx_type'] == "TRANSFER":
        if row_dict['received_amount'] and Decimal(row_dict['received_amount']) > 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                    data_row.timestamp,
                                                    buy_quantity=row_dict['received_amount'],
                                                    buy_asset=row_dict['received_currency'],
                                                    wallet=wallet_name(row_dict['wallet_address']))
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                    data_row.timestamp,
                                                    sell_quantity=row_dict['sent_amount'],
                                                    sell_asset=row_dict['sent_currency'],
                                                    fee_quantity=row_dict['fee'],
                                                    fee_asset=row_dict['fee_currency'],
                                                    wallet=wallet_name(row_dict['wallet_address']))   
    elif row_dict['tx_type'] == "_BORROW":
        # Waiting on https://github.com/BittyTax/BittyTax/issues/135 for proper types
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                data_row.timestamp,
                                                buy_quantity=row_dict['received_amount'],
                                                buy_asset=row_dict['received_currency'],
                                                fee_quantity=row_dict['fee'],
                                                fee_asset=row_dict['fee_currency'],
                                                wallet=wallet_name(row_dict['wallet_address']))
    elif row_dict['tx_type'] == "_REPAY":
        # Waiting on https://github.com/BittyTax/BittyTax/issues/135 for proper types
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_SPOUSE,
                                                data_row.timestamp,
                                                sell_quantity=row_dict['sent_amount'],
                                                sell_asset=row_dict['sent_currency'],
                                                fee_quantity=row_dict['fee'],
                                                fee_asset=row_dict['fee_currency'],
                                                wallet=wallet_name(row_dict['wallet_address']))
    elif row_dict['tx_type'] in ["_STAKING_DELEGATE", "_STAKING_REDELEGATE", "_STAKING_UNDELEGATE", "_STAKING_WITHDRAW_REWARD",
                                 "_DEPOSIT_COLLATERAL", "_WITHDRAW_COLLATERAL",
                                 "_LP_STAKE", "_LP_UNSTAKE", 
                                 "_GOV", "_GOV_STAKE", "_GOV_UNSTAKE",
                                 "_VOTE"]:
        # These are not taxable events because they're not disposals but there's usually a fee
        # Since you can't have a SPEND for a zero amount, we use the `sell` to represent the fee
        if len(row_dict['fee']) > 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                    data_row.timestamp,
                                                    sell_quantity=row_dict['fee'],
                                                    sell_asset=row_dict['fee_currency'],
                                                    wallet=wallet_name(row_dict['wallet_address']))
    elif row_dict['tx_type'] == "AIRDROP":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_AIRDROP,
                                                data_row.timestamp,
                                                buy_quantity=row_dict['received_amount'],
                                                buy_asset=row_dict['received_currency'],
                                                fee_quantity=row_dict['fee'],
                                                fee_asset=row_dict['fee_currency'],                                                 
                                                wallet=wallet_name(row_dict['wallet_address']))
    elif row_dict['tx_type'] == "STAKING":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_STAKING,
                                                data_row.timestamp,
                                                buy_quantity=row_dict['received_amount'],
                                                buy_asset=row_dict['received_currency'],
                                                fee_quantity=row_dict['fee'] if len(row_dict['fee']) > 0 else None,
                                                fee_asset=row_dict['fee_currency'] if row_dict['fee_currency'] is not None else None,                                                 
                                                wallet=wallet_name(row_dict['wallet_address']))

def wallet_name(wallet):
    if not wallet:
        return WALLET
    return wallet

DataParser(DataParser.TYPE_WALLET,
           "StakeTax",
           ['timestamp','tx_type','taxable','received_amount','received_currency','sent_amount','sent_currency','fee','fee_currency','comment','txid','url','exchange','wallet_address'],
           worksheet_name="StakeTax",
           row_handler=parse_staketax)
