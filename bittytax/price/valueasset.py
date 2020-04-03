# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
from decimal import Decimal
from datetime import datetime

from ..version import __version__
from ..config import config
from ..tax import which_tax_year
from .pricedata import PriceData

log = logging.getLogger()

class ValueAsset(object):
    def __init__(self):
        self.price_data = PriceData()
        self.price_report = {}

    def get_value(self, asset, timestamp, quantity):
        if asset == config.CCY:
            return quantity, True

        asset_price_ccy, _, _ = self.get_historical_price(asset, timestamp)
        if asset_price_ccy is not None:
            value = asset_price_ccy * quantity
            log.debug("Price on %s, 1 %s=%s%s %s, %s %s=%s%s %s",
                      timestamp.strftime('%Y-%m-%d'),
                      asset,
                      config.sym(), '{:0,.2f}'.format(asset_price_ccy), config.CCY,
                      '{:0,f}'.format(quantity),
                      asset,
                      config.sym(), '{:0,.2f}'.format(value), config.CCY)
            return value, False
        else:
            log.debug("Price at %s for %s is not available",
                      timestamp.strftime('%Y-%m-%d'), asset)
            return Decimal(0), False

    def get_current_value(self, asset, quantity):
        asset_price_ccy, name, data_source = self.get_latest_price(asset)
        if asset_price_ccy is not None:
            return asset_price_ccy * quantity, name, data_source

        return None, None, None

    def get_historical_price(self, asset, timestamp):
        asset_price_ccy = None

        if timestamp.date() >= datetime.now().date():
            raise Exception("Date is not in the past: " + timestamp.strftime('%Y-%m-%d'))

        if asset == "BTC" or asset in config.fiat_list:
            asset_price_ccy, name, data_source, url = self.price_data.get_historical(asset,
                                                                                     config.CCY,
                                                                                     timestamp)
            self.price_report_cache(asset, timestamp, name, data_source, url, asset_price_ccy)
        else:
            btc_price_ccy, name, data_source, url = self.price_data.get_historical("BTC",
                                                                                   config.CCY,
                                                                                   timestamp)
            self.price_report_cache("BTC", timestamp, name, data_source, url, btc_price_ccy)

            if btc_price_ccy is not None:
                asset_price_btc, name, data_source, url = self.price_data.get_historical(asset,
                                                                                         "BTC",
                                                                                         timestamp)
                if asset_price_btc is not None:
                    asset_price_ccy = btc_price_ccy * asset_price_btc

                self.price_report_cache(asset, timestamp, name, data_source, url,
                                        asset_price_ccy, asset_price_btc)

        return asset_price_ccy, name, data_source

    def get_latest_price(self, asset):
        asset_price_ccy = None

        if asset == "BTC" or asset in config.fiat_list:
            asset_price_ccy, name, data_source = self.price_data.get_latest(asset, config.CCY)
        else:
            btc_price_ccy, _, _ = self.price_data.get_latest("BTC", config.CCY)

            if btc_price_ccy is not None:
                asset_price_btc, name, data_source = self.price_data.get_latest(asset, "BTC")
                if asset_price_btc is not None:
                    asset_price_ccy = btc_price_ccy * asset_price_btc

        return asset_price_ccy, name, data_source

    def price_report_cache(self, asset, timestamp, name, data_source, url,
                           price_ccy, price_btc=None):
        tax_year = which_tax_year(timestamp)

        if tax_year not in self.price_report:
            self.price_report[tax_year] = {}

        if asset not in self.price_report[tax_year]:
            self.price_report[tax_year][asset] = {}

        date = timestamp.strftime('%Y-%m-%d')
        if date not in self.price_report[tax_year][asset]:
            self.price_report[tax_year][asset][date] = {'name': name,
                                                        'data_source': data_source,
                                                        'url': url,
                                                        'price_ccy': price_ccy,
                                                        'price_btc': price_btc}
