# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from ..out_record import TransactionOutRecord as TxOutRec
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

ACCOINTING_D_MAPPING = {'add_funds': TxOutRec.TYPE_DEPOSIT,
                        'airdrop': TxOutRec.TYPE_AIRDROP,
                        'bounty': TxOutRec.TYPE_INCOME,
                        'gambling_income': TxOutRec.TYPE_GIFT_RECEIVED,
                        'gift_received': TxOutRec.TYPE_GIFT_RECEIVED,
                        'hard_fork': TxOutRec.TYPE_GIFT_RECEIVED,
                        'ignored': None,
                        'income': TxOutRec.TYPE_INCOME,
                        'internal': TxOutRec.TYPE_DEPOSIT,
                        'lending_income': TxOutRec.TYPE_INTEREST,
                        'liquidity_pool': TxOutRec.TYPE_STAKING,
                        'margin_gain': '_margin_gain',
                        'master_node': TxOutRec.TYPE_STAKING,
                        'mined': TxOutRec.TYPE_MINING,
                        'staked': TxOutRec.TYPE_STAKING,
                        'swap': '_swap'}

ACCOINTING_W_MAPPING = {'remove_funds': TxOutRec.TYPE_WITHDRAWAL,
                        'fee': TxOutRec.TYPE_SPEND,
                        'gambling_used': TxOutRec.TYPE_SPEND,
                        'gift_sent': TxOutRec.TYPE_GIFT_SENT,
                        'ignored': None,
                        'interest_paid': TxOutRec.TYPE_SPEND,
                        'internal': TxOutRec.TYPE_WITHDRAWAL,
                        'lending': '_lending',
                        'lost': TxOutRec.TYPE_LOST,
                        'margin_fee': '_margin_fee',
                        'margin_loss': '_margin_loss',
                        'payment': TxOutRec.TYPE_SPEND}

def parse_accointing(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['timeExecuted'])

    if row_dict['feeCurrency']:
        fee_quantity = row_dict['feeQuantity']
    else:
        fee_quantity = None

    if row_dict['boughtQuantity'] and row_dict['soldQuantity']:
        # Trade
        data_row.t_record = TxOutRec(TxOutRec.TYPE_TRADE,
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
            t_type = TxOutRec.TYPE_DEPOSIT
        elif row_dict['classification'] == 'ignored':
            # skip
            return
        elif row_dict['classification'] in ACCOINTING_D_MAPPING and \
                ACCOINTING_D_MAPPING[row_dict['classification']]:
            t_type = ACCOINTING_D_MAPPING[row_dict['classification']]
        else:
            raise UnexpectedTypeError(parser.in_header.index('classification'), 'classification',
                                      row_dict['classification'])

        data_row.t_record = TxOutRec(t_type,
                                     data_row.timestamp,
                                     buy_quantity=row_dict['boughtQuantity'],
                                     buy_asset=row_dict['boughtCurrency'],
                                     fee_quantity=fee_quantity,
                                     fee_asset=row_dict['feeCurrency'],
                                     wallet=row_dict['walletName'])
    elif row_dict['soldQuantity']:
        # Withdrawal
        if not row_dict['classification']:
            t_type = TxOutRec.TYPE_WITHDRAWAL
        elif row_dict['classification'] == 'ignored':
            # skip
            return
        elif row_dict['classification'] in ACCOINTING_W_MAPPING and \
                ACCOINTING_W_MAPPING[row_dict['classification']]:
            t_type = ACCOINTING_W_MAPPING[row_dict['classification']]
        else:
            raise UnexpectedTypeError(parser.in_header.index('classification'), 'classification',
                                      row_dict['classification'])

        data_row.t_record = TxOutRec(t_type,
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
            'feeCurrencyId', 'classification', 'walletName', 'walletProvider', 'providerId',
            'txId', 'primaryAddress', 'otherAddress', 'temporaryCurrencyName',
            'temporaryFeeCurrencyName', 'temporaryBoughtCurrencyTicker',
            'temporarySoldCurrencyTicker', 'temporaryFeeCurrencyTicker', 'id',
            'associatedTransferId', 'comments', 'fiatValueOverwrite', 'feeFiatValueOverwrite'],
           worksheet_name="Accointing",
           row_handler=parse_accointing)

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
