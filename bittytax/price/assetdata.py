# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import os

from ..config import config
from .datasource import DataSourceBase, ExchangeRatesAPI, RatesAPI
from .exceptions import UnexpectedDataSourceError

class AssetData(object):
    FIAT_DATASOURCES = (ExchangeRatesAPI.__name__, RatesAPI.__name__)

    def __init__(self):
        self.data_sources = {}

        if not os.path.exists(config.CACHE_DIR):
            os.mkdir(config.CACHE_DIR)

        for data_source_class in DataSourceBase.__subclasses__():
            self.data_sources[data_source_class.__name__.upper()] = data_source_class()

    def get_assets(self, req_symbol, req_data_source, search_terms):
        if not req_data_source or req_data_source == 'ALL':
            data_sources = self.data_sources
        else:
            data_sources = [req_data_source]

        asset_data = []
        for ds in data_sources:
            if not req_symbol:
                assets = self.data_sources[ds].get_list()
            else:
                assets = {}
                assets[req_symbol] = self.data_sources[ds].get_list().get(req_symbol, [])
            for symbol in assets:
                for asset_id in assets[symbol]:
                    if search_terms:
                        match = self.do_search(symbol, asset_id['name'], search_terms)
                    else:
                        match = True

                    if match:
                        asset_data.append({'symbol':symbol,
                                           'name': asset_id['name'],
                                           'data_source': self.data_sources[ds].name(),
                                           'id': asset_id['id'],
                                           'priority': self._is_priority(symbol,
                                                                         asset_id['id'], ds)})

        return sorted(asset_data, key=lambda a: a['symbol'].lower())

    def _is_priority(self, symbol, asset_id, data_source):
        if symbol in config.data_source_select:
            ds_priority = [ds.split(':')[0] for ds in config.data_source_select[symbol]]
        elif symbol in config.fiat_list:
            ds_priority = config.data_source_fiat
        else:
            ds_priority = config.data_source_crypto

        for ds in ds_priority:
            if ds.upper() in self.data_sources:
                if symbol in self.data_sources[ds.upper()].assets:
                    if ds.upper() == data_source.upper() and \
                            self.data_sources[ds.upper()].assets[symbol].get('id') == asset_id:
                        return True
                    return False
            else:
                raise UnexpectedDataSourceError(ds, DataSourceBase)
        return False

    @staticmethod
    def do_search(symbol, name, search_terms):
        for search_term in search_terms:
            if search_term.upper() not in symbol.upper() + ' ' + name.upper():
                return False

        return True

    def get_latest_price_ds(self, req_symbol, req_data_source):
        if req_data_source == 'ALL':
            data_sources = self.data_sources
        else:
            data_sources = [req_data_source]

        all_assets = []
        for ds in data_sources:
            for asset_id in self.data_sources[ds].get_list().get(req_symbol, []):
                asset_id['symbol'] = req_symbol
                asset_id['data_source'] = self.data_sources[ds].name()
                asset_id['priority'] = self._is_priority(asset_id['symbol'],
                                                         asset_id['id'],
                                                         asset_id['data_source'])

                if req_symbol == 'BTC' or asset_id['data_source'] in self.FIAT_DATASOURCES:
                    asset_id['quote'] = config.ccy
                else:
                    asset_id['quote'] = 'BTC'

                asset_id['price'] = self.data_sources[ds].get_latest(req_symbol,
                                                                     asset_id['quote'],
                                                                     asset_id['id'])
                all_assets.append(asset_id)
        return all_assets

    def get_historic_price_ds(self, req_symbol, req_date, req_data_source, no_cache=False):
        if req_data_source == 'ALL':
            data_sources = self.data_sources
        else:
            data_sources = [req_data_source]

        all_assets = []
        for ds in data_sources:
            for asset_id in self.data_sources[ds].get_list().get(req_symbol, []):
                asset_id['symbol'] = req_symbol
                asset_id['data_source'] = self.data_sources[ds].name()
                asset_id['priority'] = self._is_priority(asset_id['symbol'],
                                                         asset_id['id'],
                                                         asset_id['data_source'])

                if req_symbol == 'BTC' or asset_id['data_source'] in self.FIAT_DATASOURCES:
                    asset_id['quote'] = config.ccy
                else:
                    asset_id['quote'] = 'BTC'

                date = req_date.strftime('%Y-%m-%d')
                pair = req_symbol + '/' + asset_id['quote']

                if not no_cache:
                    # check cache first
                    if pair in self.data_sources[ds].prices and \
                            date in self.data_sources[ds].prices[pair]:
                        asset_id['price'] = self.data_sources[ds].prices[pair][date]['price']
                        all_assets.append(asset_id)
                        continue

                self.data_sources[ds].get_historical(req_symbol, asset_id['quote'],
                                                     req_date, asset_id['id'])
                if pair in self.data_sources[ds].prices and \
                       date in self.data_sources[ds].prices[pair]:
                    asset_id['price'] = self.data_sources[ds].prices[pair][date]['price']
                else:
                    asset_id['price'] = None

                all_assets.append(asset_id)
        return all_assets
