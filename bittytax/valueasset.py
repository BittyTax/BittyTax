# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import os
from decimal import Decimal
from datetime import datetime

from .version import __version__
from .config import config
from .datasource import ExchangeRatesAPI, RatesAPI, CoinDesk, CryptoCompare, CoinGecko, CoinPaprika

log = logging.getLogger()

class ValueAsset(object):
    def __init__(self):
        self.price_data = PriceData()

    def get_value(self, asset, timestamp, quantity, fixed_value):
        if asset == config.CCY:
            return quantity

        if fixed_value is None:
            price_ccy, _, _ = self.get_historical_price(asset, timestamp)
            if price_ccy is not None:
                value = price_ccy * quantity
                log.debug("Price on %s, 1 %s=%s%s %s, %s %s=%s%s %s",
                          timestamp.strftime('%Y-%m-%d'),
                          asset,
                          config.sym(), '{:0,.2f}'.format(price_ccy), config.CCY,
                          str(quantity),
                          asset,
                          config.sym(), '{:0,.2f}'.format(value), config.CCY)
            else:
                value = Decimal(0)
                log.warning("Price at %s for %s is not available",
                            timestamp.strftime('%Y-%m-%d'),
                            asset)
        else:
            value = fixed_value
            log.debug("Using fixed value, %s %s=%s%s %s",
                      str(quantity),
                      asset,
                      config.sym(), '{:0,.2f}'.format(value), config.CCY)

        return value

    def get_current_value(self, asset, quantity):
        price_ccy, name, data_source = self.get_latest_price(asset)
        if price_ccy is not None:
            return price_ccy * quantity, name, data_source

        return Decimal(0), None, None

    def get_historical_price(self, asset, timestamp):
        if timestamp.date() >= datetime.now().date():
            raise Exception("Date is not in the past: " + timestamp.strftime('%Y-%m-%d'))

        if asset == "BTC" or asset in config.fiat_list:
            price_ccy, name, data_source = self.price_data.get_historical(asset,
                                                                          config.CCY,
                                                                          timestamp)
        else:
            price_btc, _, _ = self.price_data.get_historical("BTC",
                                                             config.CCY,
                                                             timestamp)
            if price_btc is not None:
                price_ccy, name, data_source = self.price_data.get_historical(asset,
                                                                              "BTC",
                                                                              timestamp)
                if price_ccy is not None:
                    price_ccy = price_btc * price_ccy

        return price_ccy, name, data_source

    def get_latest_price(self, asset):
        if asset == "BTC" or asset in config.fiat_list:
            price_ccy, name, data_source = self.price_data.get_latest(asset, config.CCY)
        else:
            price_btc, _, _ = self.price_data.get_latest("BTC", config.CCY)

            if price_btc is not None:
                price_ccy, name, data_source = self.price_data.get_latest(asset, "BTC")
                if price_ccy is not None:
                    price_ccy = price_btc * price_ccy

        return price_ccy, name, data_source

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
                        return self.data_sources[data_source].prices[pair][date], \
                               self.data_sources[data_source].assets[asset]

                self.data_sources[data_source].get_historical(asset, quote, timestamp)
                if pair in self.data_sources[data_source].prices and \
                   date in self.data_sources[data_source].prices[pair]:
                    return self.data_sources[data_source].prices[pair][date], \
                           self.data_sources[data_source].assets[asset]
                else:
                    return None, self.data_sources[data_source].assets[asset]
            else:
                return None, None
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
            price, name = self.get_historical_ds(data_source, asset, quote, timestamp)
            if price is not None:
                log.debug("Price on %s, 1 %s=%s %s via %s (%s)",
                          timestamp.strftime('%Y-%m-%d'),
                          asset,
                          '{:0,f}'.format(price.normalize()),
                          quote,
                          data_source,
                          name)
                break

        return price, name, data_source
