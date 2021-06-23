# -*- coding: utf-8 -*-

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError, UnexpectedContentError

WALLET = 'Helium'
HNT = 'HNT'

TYPE = 'type'
TAG = 'Tag'
REWARD_TYPE = 'Reward Type'

# By its design the Helium blockchain has been tied to USD:
#
#   1. Helium Data Credits (DC) are pegged to USD (1 Data Credit = $0.00001)
# 
#   2. The decentralized Helium HNT Price Oracles supply the USD $ to HNT prices
#      for on-chain burning of Data Credits.
#
# Therefore, the fiat currency for all asset values output should be hardcoded to USD.
# See https://docs.helium.com/blockchain/oracles/ for more information.

# Parse transaction exports from Helium Explorer (use HNT fees instead of DC)
# NOTE: The Explorer export does not include HNT/USD Oracle pricing associated with the block
def parse_helium_explorer_export(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date'])

    note = 'Block ' + row_dict['Block']
    if row_dict['Note']:
        note = note + '; Note=' + row_dict['Note']

    if row_dict['Received Quantity']:
        received_quantity = Decimal(row_dict['Received Quantity'])
    else:
        received_quantity = 0

    if row_dict['Sent Quantity']:
        sent_quantity = Decimal(row_dict['Sent Quantity'])
    else:
        sent_quantity = 0

    if row_dict[TAG] == 'mined':
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_MINING,
                                                data_row.timestamp,
                                                buy_quantity=received_quantity,
                                                buy_asset=row_dict['Received Currency'],
                                                note=note,
                                                wallet=WALLET)

    elif row_dict[TAG] == 'payment' and received_quantity > 0:
        note = note + '; Received from ' + row_dict['Received From']
        fee = Decimal(row_dict['Fee Amount'])

        # only fee currency in HNT is supported to ensure gross calculation is correct
        if row_dict['Fee Currency'] != row_dict['Received Currency']:
            raise UnexpectedContentError(parser.in_header.index('Fee Currency'), 'Fee Currency',
                                         row_dict['Fee Currency'])

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                data_row.timestamp,
                                                buy_quantity=received_quantity + fee,
                                                buy_asset=row_dict['Received Currency'],
                                                fee_quantity=fee,
                                                fee_asset=row_dict['Fee Currency'],
                                                note=note,
                                                wallet=WALLET)

    elif row_dict[TAG] == 'payment' and sent_quantity > 0:
        note = note + '; Sent to ' + row_dict['Sent To']
        fee = Decimal(row_dict['Fee Amount'])

        # only fee currency in HNT is supported to ensure gross calculation is correct
        if row_dict['Fee Currency'] != row_dict['Sent Currency']:
            raise UnexpectedContentError(parser.in_header.index('Fee Currency'), 'Fee Currency',
                                         row_dict['Fee Currency'])

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                data_row.timestamp,
                                                sell_quantity=sent_quantity + fee,
                                                sell_asset=row_dict['Sent Currency'],
                                                fee_quantity=fee,
                                                fee_asset=row_dict['Fee Currency'],
                                                note=note,
                                                wallet=WALLET)

    else:
        raise UnexpectedTypeError(parser.in_header.index(TAG), TAG, row_dict[TAG])

# Parse Fairspot Helium transaction exports from https://www.fairspot.host/hnt-export-mining-tax
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
           [ 'Date', 'Received Quantity', 'Received From', 'Received Currency', 
             'Sent Quantity', 'Sent To', 'Sent Currency', 'Fee Amount', 'Fee Currency', 
             'Tag', 'Note', 'Hotspot', 'Reward Type', 'Block', 'Hash' ],
           worksheet_name='Helium',
           row_handler=parse_helium_explorer_export)

DataParser(DataParser.TYPE_WALLET,
           'Helium',
           [ 'block', 'date', 'type', 'transaction_hash', 'hnt_amount', 'hnt_fee',
             'usd_oracle_price', 'usd_amount', 'usd_fee', 'payer', 'payee' ],
           worksheet_name='Helium',
           row_handler=parse_helium_fairspot)
