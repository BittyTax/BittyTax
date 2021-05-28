# -*- coding: utf-8 -*-

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = 'Helium'

HNT = 'HNT'
ASSETS = [ HNT, 'HST', 'DC' ]

TYPE = 'type'

# By its design the Helium blockchain has been tied to USD:
#
#   1. Helium Data Credits (DC) are pegged to USD (1 Data Credit = $0.00001)
# 
#   2. The decentralized Helium HNT Price Oracles supply the USD $ to HNT prices
#      for on-chain burning of Data Credits.
#
# Therefore, the fiat currency for all asset values output should be hardcoded to USD.
# See https://docs.helium.com/blockchain/oracles/ for more information.

# TODO:
# - Should the wallet be the actual Helium wallet id (payee or payer), or just "Helium"?
#   Some miners have many wallets for privacy, scaling, hosting agreements, and other reasons.

# Supports Helium transaction exports from https://www.fairspot.host/hnt-export-mining-tax
def parse_helium_fairspot(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['date'])

    usd_price = Decimal(row_dict['usd_oracle_price'])
    quantity = Decimal(row_dict['hnt_amount'])

    if row_dict[TYPE] == 'rewards_v1':
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_MINING,
                                                data_row.timestamp,
                                                buy_quantity=quantity,
                                                buy_asset=HNT,
                                                buy_value=usd_price * quantity,
                                                #value_fiat='USD',
                                                note='USD Fiat',
                                                wallet=WALLET)

    elif row_dict[TYPE] == 'payment_v1':
        wallet = row_dict['payee']
        hnt_fee = Decimal(row_dict['hnt_fee'])
        gross_quantity = quantity + hnt_fee

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                data_row.timestamp,
                                                buy_quantity=gross_quantity,
                                                buy_asset=HNT,
                                                buy_value=usd_price * gross_quantity,
                                                fee_quantity=hnt_fee,
                                                fee_asset=HNT,
                                                fee_value=usd_price * hnt_fee,
                                                #value_fiat='USD',
                                                note='USD Fiat',
                                                wallet=WALLET)

    elif row_dict[TYPE] == 'payment_v2':
        wallet = row_dict['payer']
        hnt_fee = Decimal(row_dict['hnt_fee'])
        gross_quantity = quantity + hnt_fee

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                data_row.timestamp,
                                                sell_quantity=gross_quantity,
                                                sell_asset=HNT,
                                                sell_value=usd_price * gross_quantity,
                                                fee_quantity=hnt_fee,
                                                fee_asset=HNT,
                                                fee_value=usd_price * hnt_fee,
                                                #value_fiat='USD',
                                                note='USD Fiat',
                                                wallet=WALLET)

    else:
        raise UnexpectedTypeError(parser.in_header.index(TYPE), TYPE, row_dict[TYPE])

DataParser(DataParser.TYPE_WALLET,
           'Helium',
           [ 'block', 'date', 'type', 'transaction_hash', 'hnt_amount', 'hnt_fee',
             'usd_oracle_price', 'usd_amount', 'usd_fee', 'payer', 'payee' ],
           worksheet_name='Helium',
           row_handler=parse_helium_fairspot)
