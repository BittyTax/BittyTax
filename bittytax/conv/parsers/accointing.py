# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

ACCOINTING_D_MAPPING = {'add_funds': TransactionOutRecord.TYPE_DEPOSIT,
                        'airdrop': TransactionOutRecord.TYPE_AIRDROP,
                        'bounty': TransactionOutRecord.TYPE_INCOME,
                        'gambling_income': TransactionOutRecord.TYPE_GIFT_RECEIVED,
                        'gift_received': TransactionOutRecord.TYPE_GIFT_RECEIVED,
                        'hard_fork': TransactionOutRecord.TYPE_GIFT_RECEIVED,
                        'ignored': None,
                        'income': TransactionOutRecord.TYPE_INCOME,
                        'internal': TransactionOutRecord.TYPE_DEPOSIT,
                        'lending_income': TransactionOutRecord.TYPE_INTEREST,
                        'liquidity_pool': TransactionOutRecord.TYPE_STAKING,
                        'margin_gain': None,
                        'master_node': TransactionOutRecord.TYPE_STAKING,
                        'mined': TransactionOutRecord.TYPE_MINING,
                        'staked': TransactionOutRecord.TYPE_STAKING,
                        'swap': TransactionOutRecord.TYPE_DEPOSIT}

ACCOINTING_W_MAPPING = {'remove_funds': TransactionOutRecord.TYPE_WITHDRAWAL,
                        'fee': TransactionOutRecord.TYPE_SPEND,
                        'gambling_used': TransactionOutRecord.TYPE_SPEND,
                        'gift_sent': TransactionOutRecord.TYPE_GIFT_SENT,
                        'ignored': None,
                        'interest_paid': TransactionOutRecord.TYPE_SPEND,
                        'internal': TransactionOutRecord.TYPE_WITHDRAWAL,
                        'lending': None,
                        'lost': TransactionOutRecord.TYPE_LOST,
                        'margin_fee': None,
                        'margin_loss': None,
                        'payment': TransactionOutRecord.TYPE_SPEND}

def parse_accointing(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['timeExecuted'])

    if row_dict['feeCurrency']:
        fee_quantity = row_dict['feeQuantity']
    else:
        fee_quantity = None

    if row_dict['boughtQuantity'] and row_dict['soldQuantity']:
        # Trade
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['boughtQuantity'],
                                                 buy_asset=row_dict['boughtCurrency'],
                                                 sell_quantity=row_dict['soldQuantity'],
                                                 sell_asset=row_dict['soldCurrency'],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=row_dict['feeCurrency'],
                                                 wallet=row_dict['walletName'])
    elif row_dict['boughtQuantity']:
        # Deposit
        if not row_dict['classification']:
            t_type = TransactionOutRecord.TYPE_DEPOSIT
        elif row_dict['classification'] == 'ignored':
            # skip
            return
        elif row_dict['classification'] in ACCOINTING_D_MAPPING and \
                ACCOINTING_D_MAPPING[row_dict['classification']]:
            t_type = ACCOINTING_D_MAPPING[row_dict['classification']]
        else:
            raise UnexpectedTypeError(parser.in_header.index('classification'), 'classification',
                                      row_dict['classification'])

        data_row.t_record = TransactionOutRecord(t_type,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['boughtQuantity'],
                                                 buy_asset=row_dict['boughtCurrency'],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=row_dict['feeCurrency'],
                                                 wallet=row_dict['walletName'])
    elif row_dict['soldQuantity']:
        # Withdrawal
        if not row_dict['classification']:
            t_type = TransactionOutRecord.TYPE_WITHDRAWAL
        elif row_dict['classification'] == 'ignored':
            # skip
            return
        elif row_dict['classification'] in ACCOINTING_W_MAPPING and \
                ACCOINTING_W_MAPPING[row_dict['classification']]:
            t_type = ACCOINTING_W_MAPPING[row_dict['classification']]
        else:
            raise UnexpectedTypeError(parser.in_header.index('classification'), 'classification',
                                      row_dict['classification'])

        data_row.t_record = TransactionOutRecord(t_type,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['soldQuantity'],
                                                 sell_asset=row_dict['soldCurrency'],
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=row_dict['feeCurrency'],
                                                 wallet=row_dict['walletName'])

DataParser(DataParser.TYPE_ACCOUNTING,
           "Accointing",
           ['timeExecuted', 'type', 'boughtQuantity', 'boughtCurrency', 'boughtCurrencyId',
            'soldQuantity', 'soldCurrency', 'soldCurrencyId', 'feeQuantity', 'feeCurrency',
            'feeCurrencyId', 'classification', 'walletName', 'walletProvider', 'txId',
            'primaryAddress', 'otherAddress', 'temporaryCurrencyName', 'temporaryFeeCurrencyName',
            'temporaryBoughtCurrencyTicker', 'temporarySoldCurrencyTicker',
            'temporaryFeeCurrencyTicker', 'id', 'associatedTransferId', 'comments'],
           worksheet_name="Accointing",
           row_handler=parse_accointing)
