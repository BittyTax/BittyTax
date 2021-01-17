# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from . import coinbase

class Asset(object):
    ''' Search for missing asset '''
    COINBASE_WALLET = 'Coinbase'

    @staticmethod
    def find_missing_asset(transaction):
        if transaction.wallet == Asset.COINBASE_WALLET:
            return coinbase.find_missing_asset(transaction.raw_row)
       
        return False, None, None
