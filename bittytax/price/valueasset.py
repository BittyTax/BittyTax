# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
from decimal import Decimal
from datetime import datetime

from ..version import __version__
from ..config import config
from .pricedata import PriceData

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
