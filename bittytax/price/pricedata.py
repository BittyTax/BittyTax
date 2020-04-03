# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import os

from ..version import __version__
from ..config import config
from .datasource import ExchangeRatesAPI, RatesAPI, CoinDesk, CryptoCompare, CoinGecko, CoinPaprika

log = logging.getLogger()

class PriceData(object):
    def __init__(self):
        self.data_sources = {}

        if not os.path.exists(config.CACHE_DIR):
            os.mkdir(config.CACHE_DIR)

        data_sources_required = set(config.data_source_fiat +
                                    config.data_source_crypto) | \
                                {x for v in config.data_source_select.values() for x in v}

        for data_source in data_sources_required:
            try:
                self.data_sources[data_source] = globals()[data_source]()
            except KeyError:
                raise ValueError("Data source: %s not recognised" % [data_source])

    @staticmethod
    def data_source_priority(asset):
        if asset in config.data_source_select:
            return config.data_source_select[asset]
        elif asset in config.fiat_list:
            return config.data_source_fiat
        else:
            return config.data_source_crypto

    def get_latest_ds(self, data_source, asset, quote):
        if data_source in self.data_sources:
            if asset in self.data_sources[data_source].assets:
                return self.data_sources[data_source].get_latest(asset, quote), \
                       self.data_sources[data_source].assets[asset]

            return None, None
        else:
            raise ValueError("Data source: %s not recognised" % [data_source])

    def get_historical_ds(self, data_source, asset, quote, timestamp):
        if data_source in self.data_sources:
            if asset in self.data_sources[data_source].assets:
                date = timestamp.strftime('%Y-%m-%d')
                pair = asset + '/' + quote

                if not config.args.nocache:
                    # check cache first
                    if pair in self.data_sources[data_source].prices and \
                       date in self.data_sources[data_source].prices[pair]:
                        return self.data_sources[data_source].prices[pair][date]['price'], \
                               self.data_sources[data_source].assets[asset], \
                               self.data_sources[data_source].prices[pair][date]['url']

                self.data_sources[data_source].get_historical(asset, quote, timestamp)
                if pair in self.data_sources[data_source].prices and \
                   date in self.data_sources[data_source].prices[pair]:
                    return self.data_sources[data_source].prices[pair][date]['price'], \
                           self.data_sources[data_source].assets[asset], \
                           self.data_sources[data_source].prices[pair][date]['url']
                else:
                    return None, self.data_sources[data_source].assets[asset], None
            else:
                return None, None, None
        else:
            raise ValueError("Data source: %s not recognised" % [data_source])

    def get_latest(self, asset, quote):
        price = name = data_source = None
        for data_source in self.data_source_priority(asset):
            price, name = self.get_latest_ds(data_source, asset, quote)
            if price is not None:
                log.debug("Price (latest), 1 %s=%s %s via %s (%s)",
                          asset,
                          '{:0,f}'.format(price.normalize()),
                          quote,
                          data_source,
                          name)
                break

        return price, name, data_source

    def get_historical(self, asset, quote, timestamp):
        price = name = data_source = None
        for data_source in self.data_source_priority(asset):
            price, name, url = self.get_historical_ds(data_source, asset, quote, timestamp)
            if price is not None:
                log.debug("Price on %s, 1 %s=%s %s via %s (%s)",
                          timestamp.strftime('%Y-%m-%d'),
                          asset,
                          '{:0,f}'.format(price.normalize()),
                          quote,
                          data_source,
                          name)
                break

        return price, name, data_source, url
