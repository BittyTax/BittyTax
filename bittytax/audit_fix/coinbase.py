# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

def find_missing_asset(raw_row):
    ''' parse the notes in the transaction extracting the fiat currency amount used to buy asset.
    For example: "Bought 0.01327044 BTC for £40.00 GBP" is deducted as 40 GBP missing asset
    '''
    asset = None
    quantity = None
    found = False
    if len(raw_row) == 21:
        notes = raw_row[20]
        if notes.startswith('Bought') and 'for' in notes:
            asset = notes.split()[-1]
            quantity = Decimal(''.join([x for x in notes.split()[-2] if x.isdigit() or x == '.']))
            found = True
    
    return found, asset, quantity
