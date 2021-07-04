# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = 'Helium'

def parse_helium_fairspot(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['date'])
    amount_ccy = DataParser.convert_currency(row_dict['usd_amount'], 'USD', data_row.timestamp)
    fee_ccy = DataParser.convert_currency(row_dict['usd_fee'], 'USD', data_row.timestamp)

    # append Block number into transaction notes to support auditing
    note = row_dict.get('Note')
    if note:
        note += f"; Block {row_dict['Block']}"
    else:
        note = f"Block {row_dict['Block']}"
        
    if row_dict['type'] == 'rewards_v1':
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_MINING,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['hnt_amount'],
                                                 buy_asset='HNT',
                                                 buy_value=amount_ccy,
                                                 note=note,
                                                 wallet=WALLET)
    elif row_dict['type'] == 'payment_v2':
        # to support auditing, include wallet id where payment was received from                                                                       
        if row_dict['Received From']:                                                                                                                  
            note += f"; Received from {row_dict['Received From']}"
            
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['hnt_amount'],
                                                 buy_asset='HNT',
                                                 buy_value=amount_ccy,
                                                 fee_quantity=row_dict['hnt_fee'],
                                                 fee_asset='HNT',
                                                 fee_value=fee_ccy,
                                                 note=note,
                                                 wallet=WALLET)
    elif row_dict['type'] == 'payment_v1':
        # to support auditing, include wallet id where payment was sent to                                                                       
        if row_dict['Sent To']:                                                                                                                        
            note += f"; Sent to {row_dict['Sent To']}"
        
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['hnt_amount'],
                                                 sell_asset='HNT',
                                                 sell_value=amount_ccy,
                                                 fee_quantity=row_dict['hnt_fee'],
                                                 fee_asset='HNT',
                                                 fee_value=fee_ccy,
                                                 note=note,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('type', 'type', row_dict['type']))

def parse_helium_explorer(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date'])
    
    # append Block number into transaction notes to support auditing
    note = row_dict.get('Note')
    if note:
        note += f"; Block {row_dict['Block']}"
    else:
        note = f"Block {row_dict['Block']}"
    
    if row_dict['Tag'] == 'mined':
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_MINING,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Received Quantity'],
                                                 buy_asset=row_dict['Received Currency'],
                                                 fee_quantity=row_dict['Fee Amount'],
                                                 fee_asset=row_dict['Fee Currency'],
                                                 note=note,
                                                 wallet=WALLET)

    elif row_dict['Tag'] == 'payment' and row_dict['Received Quantity']:
        # to support auditing, include wallet id where payment was received from                                                                       
        if row_dict['Received From']:                                                                                                                  
            note += f"; Received from {row_dict['Received From']}"
        
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Received Quantity'],
                                                 buy_asset=row_dict['Received Currency'],
                                                 fee_quantity=row_dict['Fee Amount'],
                                                 fee_asset=row_dict['Fee Currency'],
                                                 note=note,
                                                 wallet=WALLET)

    elif row_dict['Tag'] == 'payment' and row_dict['Sent Quantity']:
        # to support auditing, include wallet id where payment was sent to                                                                       
        if row_dict['Sent To']:                                                                                                                        
            note += f"; Sent to {row_dict['Sent To']}"      
        
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Sent Quantity'],
                                                 sell_asset=row_dict['Sent Currency'],
                                                 fee_quantity=row_dict['Fee Amount'],
                                                 fee_asset=row_dict['Fee Currency'],
                                                 note=note,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Tag'), 'Tag', row_dict['Tag'])

DataParser(DataParser.TYPE_WALLET,
           'Helium',
           ['block', 'date', 'type', 'transaction_hash', 'hnt_amount', 'hnt_fee',
            'usd_oracle_price', 'usd_amount', 'usd_fee', 'payer', 'payee'],
           worksheet_name='Helium',
           row_handler=parse_helium_fairspot)

DataParser(DataParser.TYPE_EXPLORER,
           'Helium Explorer',
           ['Date', 'Received Quantity', 'Received From', 'Received Currency',
            'Sent Quantity', 'Sent To', 'Sent Currency', 'Fee Amount', 'Fee Currency',
            'Tag', 'Note', 'Hotspot', 'Reward Type', 'Block', 'Hash'],
           worksheet_name='Helium',
           row_handler=parse_helium_explorer)
