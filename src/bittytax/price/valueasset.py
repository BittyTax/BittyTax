# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from datetime import datetime
from decimal import Decimal

from colorama import Back, Fore, Style
from tqdm import tqdm

from ..config import config
from .pricedata import PriceData


class ValueAsset(object):
    def __init__(self, price_tool=False):
        self.price_tool = price_tool
        self.price_report = {}
        data_sources_required = set(config.data_source_fiat + config.data_source_crypto) | {
            x.split(":")[0] for v in config.data_source_select.values() for x in v
        }
        self.price_data = PriceData(data_sources_required, price_tool)

    def get_value(self, asset, timestamp, quantity):
        if asset == config.ccy:
            return quantity, True

        if quantity == 0:
            return Decimal(0), False

        asset_price_ccy, _, _ = self.get_historical_price(asset, timestamp)
        if asset_price_ccy is not None:
            value = asset_price_ccy * quantity
            if config.debug:
                print(
                    "%sprice: %s, 1 %s=%s %s, %s %s=%s%s %s%s"
                    % (
                        Fore.YELLOW,
                        timestamp.strftime("%Y-%m-%d"),
                        asset,
                        config.sym() + "{:0,.2f}".format(asset_price_ccy),
                        config.ccy,
                        "{:0,f}".format(quantity.normalize()),
                        asset,
                        Style.BRIGHT,
                        config.sym() + "{:0,.2f}".format(value),
                        config.ccy,
                        Style.NORMAL,
                    )
                )
            return value, False

        tqdm.write(
            "%sWARNING%s Price for %s on %s is not available, using price of %s"
            % (
                Back.YELLOW + Fore.BLACK,
                Back.RESET + Fore.YELLOW,
                asset,
                timestamp.strftime("%Y-%m-%d"),
                config.sym() + "{:0,.2f}".format(0),
            )
        )
        return Decimal(0), False

    def get_current_value(self, asset, quantity):
        asset_price_ccy, name, data_source = self.get_latest_price(asset)
        if asset_price_ccy is not None:
            return asset_price_ccy * quantity, name, data_source

        return None, None, None

    def get_historical_price(self, asset, timestamp, no_cache=False):
        asset_price_ccy = None

        if not self.price_tool and timestamp.date() >= datetime.now().date():
            tqdm.write(
                "%sWARNING%s Price for %s on %s, no historic price available, "
                "using latest price"
                % (
                    Back.YELLOW + Fore.BLACK,
                    Back.RESET + Fore.YELLOW,
                    asset,
                    timestamp.strftime("%Y-%m-%d"),
                )
            )
            return self.get_latest_price(asset)

        if asset == "BTC" or asset in config.fiat_list:
            asset_price_ccy, name, data_source, url = self.price_data.get_historical(
                asset, config.ccy, timestamp, no_cache
            )
            self.price_report_cache(asset, timestamp, name, data_source, url, asset_price_ccy)
        else:
            asset_price_btc, name, data_source, url = self.price_data.get_historical(
                asset, "BTC", timestamp, no_cache
            )
            if asset_price_btc is not None:
                (
                    btc_price_ccy,
                    name2,
                    data_source2,
                    url2,
                ) = self.price_data.get_historical("BTC", config.ccy, timestamp, no_cache)
                if btc_price_ccy is not None:
                    asset_price_ccy = btc_price_ccy * asset_price_btc

                self.price_report_cache("BTC", timestamp, name2, data_source2, url2, btc_price_ccy)

            self.price_report_cache(
                asset,
                timestamp,
                name,
                data_source,
                url,
                asset_price_ccy,
                asset_price_btc,
            )

        return asset_price_ccy, name, data_source

    def get_latest_price(self, asset):
        asset_price_ccy = None

        if asset == "BTC" or asset in config.fiat_list:
            asset_price_ccy, name, data_source = self.price_data.get_latest(asset, config.ccy)
        else:
            asset_price_btc, name, data_source = self.price_data.get_latest(asset, "BTC")

            if asset_price_btc is not None:
                btc_price_ccy, _, _ = self.price_data.get_latest("BTC", config.ccy)
                if btc_price_ccy is not None:
                    asset_price_ccy = btc_price_ccy * asset_price_btc

        return asset_price_ccy, name, data_source

    def price_report_cache(
        self, asset, timestamp, name, data_source, url, price_ccy, price_btc=None
    ):
        if timestamp > config.get_tax_year_end(timestamp.year):
            tax_year = timestamp.year + 1
        else:
            tax_year = timestamp.year

        if tax_year not in self.price_report:
            self.price_report[tax_year] = {}

        if asset not in self.price_report[tax_year]:
            self.price_report[tax_year][asset] = {}

        date = timestamp.strftime("%Y-%m-%d")
        if date not in self.price_report[tax_year][asset]:
            self.price_report[tax_year][asset][date] = {
                "name": name,
                "data_source": data_source,
                "url": url,
                "price_ccy": price_ccy,
                "price_btc": price_btc,
            }
