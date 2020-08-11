# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import os

from colorama import Fore

from ..version import __version__
from ..config import config
from .datasource import DataSourceBase
from .exceptions import UnexpectedDataSourceError

class PriceData(object):
    def __init__(self):
        self.data_sources = {}

        if not os.path.exists(config.CACHE_DIR):
            os.mkdir(config.CACHE_DIR)

        data_sources_required = set(config.data_source_fiat +
                                    config.data_source_crypto) | \
                                {x for v in config.data_source_select.values() for x in v}

        for data_source in DataSourceBase.__subclasses__():
            if data_source.__name__.upper() in [ds.upper() for ds in data_sources_required]:
                self.data_sources[data_source.__name__.upper()] = data_source()

    @staticmethod
    def data_source_priority(asset):
        if asset in config.data_source_select:
            return config.data_source_select[asset]
        elif asset in config.fiat_list:
            return config.data_source_fiat
        else:
            return config.data_source_crypto

    def get_latest_ds(self, data_source, asset, quote):
        if data_source.upper() in self.data_sources:
            if asset in self.data_sources[data_source.upper()].assets:
                return self.data_sources[data_source.upper()].get_latest(asset, quote), \
                       self.data_sources[data_source.upper()].assets[asset]

            return None, None
        else:
            raise UnexpectedDataSourceError(data_source)

    def get_historical_ds(self, data_source, asset, quote, timestamp):
        if data_source.upper() in self.data_sources:
            if asset in self.data_sources[data_source.upper()].assets:
                date = timestamp.strftime('%Y-%m-%d')
                pair = asset + '/' + quote

                if not config.args.nocache:
                    # check cache first
                    if pair in self.data_sources[data_source.upper()].prices and \
                       date in self.data_sources[data_source.upper()].prices[pair]:
                        return self.data_sources[data_source.upper()].prices[pair][date]['price'], \
                              self.data_sources[data_source.upper()].assets[asset], \
                              self.data_sources[data_source.upper()].prices[pair][date]['url']

                self.data_sources[data_source.upper()].get_historical(asset, quote, timestamp)
                if pair in self.data_sources[data_source.upper()].prices and \
                   date in self.data_sources[data_source.upper()].prices[pair]:
                    return self.data_sources[data_source.upper()].prices[pair][date]['price'], \
                           self.data_sources[data_source.upper()].assets[asset], \
                           self.data_sources[data_source.upper()].prices[pair][date]['url']
                else:
                    return None, self.data_sources[data_source.upper()].assets[asset], None
            else:
                return None, None, None
        else:
            raise UnexpectedDataSourceError(data_source)

    def get_latest(self, asset, quote):
        price = name = data_source = None
        for data_source in self.data_source_priority(asset):
            price, name = self.get_latest_ds(data_source, asset, quote)
            if price is not None:
                if config.args.debug:
                    print("%sprice: <latest>, 1 %s=%s %s via %s (%s)" % (
                        Fore.YELLOW,
                        asset,
                        '{:0,f}'.format(price.normalize()),
                        quote,
                        self.data_sources[data_source.upper()].name(),
                        name))
                break

        return price, name, self.data_sources[data_source.upper()].name()

    def get_historical(self, asset, quote, timestamp):
        price = name = data_source = url = None
        for data_source in self.data_source_priority(asset):
            price, name, url = self.get_historical_ds(data_source, asset, quote, timestamp)
            if price is not None:
                if config.args.debug:
                    print("%sprice: %s, 1 %s=%s %s via %s (%s)" % (
                        Fore.YELLOW,
                        timestamp.strftime('%Y-%m-%d'),
                        asset,
                        '{:0,f}'.format(price.normalize()),
                        quote,
                        self.data_sources[data_source.upper()].name(),
                        name))
                break

        return price, name, self.data_sources[data_source.upper()].name(), url
