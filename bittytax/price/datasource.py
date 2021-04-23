# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import os
import atexit
import json
from decimal import Decimal
from datetime import datetime, timedelta

from colorama import Fore, Back
import dateutil.parser
import requests

from ..version import __version__
from ..config import config
from .exceptions import UnexpectedDataSourceAssetIdError

CRYPTOCOMPARE_MAX_DAYS = 2000
COINPAPRIKA_MAX_DAYS = 5000

class DataSourceBase(object):
    USER_AGENT = 'BittyTax/v%s' % __version__
    TIME_OUT = 30

    def __init__(self):
        self.assets = {}
        self.ids = {}
        self.prices = self.load_prices()

        for pair in sorted(self.prices):
            if config.debug:
                print("%sprice: %s (%s) data cache loaded" % (Fore.YELLOW, self.name(), pair))

        atexit.register(self.dump_prices)

    def name(self):
        return self.__class__.__name__

    def get_json(self, url):
        if config.debug:
            print("%sprice: GET %s" % (Fore.YELLOW, url))

        response = requests.get(url, headers={'User-Agent': self.USER_AGENT}, timeout=self.TIME_OUT)

        if response.status_code in [429, 502, 503, 504]:
            response.raise_for_status()

        if response:
            return response.json()
        return {}

    def update_prices(self, pair, prices, timestamp):
        if pair not in self.prices:
            self.prices[pair] = {}

        # We are not interested in today's latest price, only the days closing price, also need to
        #  filter any erroneous future dates returned
        prices = {k: v
                  for k, v in prices.items()
                  if dateutil.parser.parse(k).date() < datetime.now().date()}

        # We might not receive data for the date requested, if so set to None to prevent repeat
        #  lookups, assuming date is in the past
        date = timestamp.strftime('%Y-%m-%d')
        if date not in prices and timestamp.date() < datetime.now().date():
            prices[date] = {'price': None,
                            'url': None}

        self.prices[pair].update(prices)

    def load_prices(self):
        filename = os.path.join(config.CACHE_DIR, self.name() + '.json')
        if not os.path.exists(filename):
            return {}

        try:
            with open(filename, 'r') as price_cache:
                json_prices = json.load(price_cache)
                return {pair: {date: {'price': self.str_to_decimal(price['price']),
                                      'url': price['url']}
                               for date, price in json_prices[pair].items()}
                        for pair in json_prices}
        except:
            print("%sWARNING%s Data cached for %s could not be loaded" % (
                Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, self.name()))
            return {}

    def dump_prices(self):
        with open(os.path.join(config.CACHE_DIR, self.name() + '.json'), 'w') as price_cache:
            json_prices = {pair: {date: {'price': self.decimal_to_str(price['price']),
                                         'url': price['url']}
                                  for date, price in self.prices[pair].items()}
                           for pair in self.prices}
            json.dump(json_prices, price_cache, indent=4, sort_keys=True)

    def get_config_assets(self):
        for symbol in config.data_source_select:
            for ds in config.data_source_select[symbol]:
                if ds.upper().startswith(self.name().upper() + ':'):
                    if symbol in self.assets:
                        self._update_asset(symbol, ds)
                    else:
                        self._add_asset(symbol, ds)

    def _update_asset(self, symbol, data_source):
        asset_id = data_source.split(':')[1]
        # Update an existing symbol, validate id belongs to that symbol
        if asset_id in self.ids and self.ids[asset_id]['symbol'] == symbol:
            self.assets[symbol] = {'id': asset_id, 'name': self.ids[asset_id]['name']}

            if config.debug:
                print("%sprice: %s updated as %s [ID:%s] (%s)" % (
                    Fore.YELLOW,
                    symbol,
                    self.name(),
                    asset_id,
                    self.ids[asset_id]['name']))
        else:
            raise UnexpectedDataSourceAssetIdError(data_source, symbol)

    def _add_asset(self, symbol, data_source):
        asset_id = data_source.split(':')[1]
        # You can only add a new symbol for an id not being used
        if asset_id in self.ids and self.assets[self.ids[asset_id]['symbol']]['id'] != asset_id:
            self.assets[symbol] = {'id': asset_id, 'name': self.ids[asset_id]['name']}
            self.ids[asset_id] = {'symbol': symbol, 'name': self.ids[asset_id]['name']}

            if config.debug:
                print("%sprice: %s added as %s [ID:%s] (%s)" % (
                    Fore.YELLOW,
                    symbol,
                    self.name(),
                    asset_id,
                    self.ids[asset_id]['name']))
        else:
            raise UnexpectedDataSourceAssetIdError(data_source, symbol)

    def get_list(self):
        if self.ids:
            asset_list = {}
            for c in self.ids:
                symbol = self.ids[c]['symbol']
                if symbol not in asset_list:
                    asset_list[symbol] = []

                asset_list[symbol].append({'id': c, 'name': self.ids[c]['name']})
            return asset_list
        return {k: [{'id':None, 'name': v['name']}] for k, v in self.assets.items()}

    @staticmethod
    def pair(asset, quote):
        return asset + '/' + quote

    @staticmethod
    def str_to_decimal(price):
        if price:
            return Decimal(price)

        return None

    @staticmethod
    def decimal_to_str(price):
        if price:
            return '{0:f}'.format(price)

        return None

    @staticmethod
    def epoch_time(timestamp):
        epoch = (timestamp - datetime(1970, 1, 1, tzinfo=config.TZ_UTC)).total_seconds()
        return int(epoch)

class ExchangeRatesAPI(DataSourceBase):
    def __init__(self):
        super(ExchangeRatesAPI, self).__init__()
        currencies = ['EUR', 'USD', 'JPY', 'BGN', 'CYP', 'CZK', 'DKK', 'EEK', 'GBP', 'HUF',
                      'LTL', 'LVL', 'MTL', 'PLN', 'ROL', 'RON', 'SEK', 'SIT', 'SKK', 'CHF',
                      'ISK', 'NOK', 'HRK', 'RUB', 'TRL', 'TRY', 'AUD', 'BRL', 'CAD', 'CNY',
                      'HKD', 'IDR', 'ILS', 'INR', 'KRW', 'MXN', 'MYR', 'NZD', 'PHP', 'SGD',
                      'THB', 'ZAR']
        self.assets = {c: {'name': 'Fiat ' + c} for c in currencies}

    def get_latest(self, asset, quote, _asset_id=None):
        url = "https://api.exchangeratesapi.io/latest?base=%s&symbols=%s" % (asset, quote)
        json_resp = self.get_json(url)
        return Decimal(repr(json_resp['rates'][quote])) \
                if 'rates' in json_resp and quote in json_resp['rates'] else None

    def get_historical(self, asset, quote, timestamp, _asset_id=None):
        url = "https://api.exchangeratesapi.io/%s?base=%s&symbols=%s" % (
            timestamp.strftime('%Y-%m-%d'), asset, quote)
        json_resp = self.get_json(url)
        pair = self.pair(asset, quote)
        # Date returned in response might not be date requested due to weekends/holidays
        self.update_prices(pair,
                           {timestamp.strftime('%Y-%m-%d'): {
                               'price': Decimal(repr(json_resp['rates'][quote])) \
                                        if 'rates' in json_resp and quote \
                                        in json_resp['rates'] else None,
                               'url': url}},
                           timestamp)

    def get_list(self):
        return {k: [{'id':None, 'name': v['name']}] for k, v in self.assets.items()}

class RatesAPI(DataSourceBase):
    def __init__(self):
        super(RatesAPI, self).__init__()
        # https://github.com/MicroPyramid/ratesapi/blob/master/scripts/pusher.py
        currencies = ['EUR', 'USD', 'JPY', 'BGN', 'CYP', 'CZK', 'DKK', 'EEK', 'GBP', 'HUF',
                      'LTL', 'LVL', 'MTL', 'PLN', 'ROL', 'RON', 'SEK', 'SIT', 'SKK', 'CHF',
                      'ISK', 'NOK', 'HRK', 'RUB', 'TRL', 'TRY', 'AUD', 'BRL', 'CAD', 'CNY',
                      'HKD', 'IDR', 'ILS', 'INR', 'KRW', 'MXN', 'MYR', 'NZD', 'PHP', 'SGD',
                      'THB', 'ZAR']
        self.assets = {c: {'name': 'Fiat ' + c} for c in currencies}

    def get_latest(self, asset, quote, _asset_id=None):
        json_resp = self.get_json(
            "https://api.ratesapi.io/api/latest?base=%s&symbols=%s" % (asset, quote)
        )
        return Decimal(repr(json_resp['rates'][quote])) \
                if 'rates' in json_resp and quote in json_resp['rates'] else None

    def get_historical(self, asset, quote, timestamp, _asset_id=None):
        url = "https://api.ratesapi.io/api/%s?base=%s&symbols=%s" % (
            timestamp.strftime('%Y-%m-%d'), asset, quote)
        json_resp = self.get_json(url)
        pair = self.pair(asset, quote)
        # Date returned in response might not be date requested due to weekends/holidays
        self.update_prices(pair,
                           {timestamp.strftime('%Y-%m-%d'): {
                               'price': Decimal(repr(json_resp['rates'][quote])) \
                                        if 'rates' in json_resp and quote \
                                        in json_resp['rates'] else None,
                               'url': url}},
                           timestamp)

class CoinDesk(DataSourceBase):
    def __init__(self):
        super(CoinDesk, self).__init__()
        self.assets = {'BTC': {'name': 'Bitcoin'}}

    def get_latest(self, _asset, quote, _asset_id=None):
        json_resp = self.get_json("https://api.coindesk.com/v1/bpi/currentprice.json")
        return Decimal(repr(json_resp['bpi'][quote]['rate_float'])) \
                if 'bpi' in json_resp and quote in json_resp['bpi'] else None

    def get_historical(self, asset, quote, timestamp, _asset_id=None):
        url = "https://api.coindesk.com/v1/bpi/historical/close.json" \
              "?start=%s&end=%s&currency=%s" % (
                  timestamp.strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d'), quote)
        json_resp = self.get_json(url)
        pair = self.pair(asset, quote)
        if 'bpi' in json_resp:
            self.update_prices(pair,
                               {k: {
                                   'price': Decimal(repr(v)) if v else None,
                                   'url': url} for k, v in json_resp['bpi'].items()},
                               timestamp)

class CryptoCompare(DataSourceBase):
    def __init__(self):
        super(CryptoCompare, self).__init__()
        json_resp = self.get_json("https://min-api.cryptocompare.com/data/all/coinlist")
        self.assets = {c[1]['Symbol'].strip().upper(): {'name': c[1]['CoinName'].strip()}
                       for c in json_resp['Data'].items()}
        # CryptoCompare symbols are unique, so no ID required

    def get_latest(self, asset, quote, _asset_id=None):
        json_resp = self.get_json("https://min-api.cryptocompare.com/data/price" \
            "?extraParams=%s&fsym=%s&tsyms=%s" % (self.USER_AGENT, asset, quote))
        return Decimal(repr(json_resp[quote])) if quote in json_resp else None

    def get_historical(self, asset, quote, timestamp, _asset_id=None):
        url = "https://min-api.cryptocompare.com/data/histoday?aggregate=1&extraParams=%s" \
              "&fsym=%s&tsym=%s&limit=%s&toTs=%d" % (
                  self.USER_AGENT, asset, quote, CRYPTOCOMPARE_MAX_DAYS,
                  self.epoch_time(timestamp + timedelta(days=CRYPTOCOMPARE_MAX_DAYS)))

        json_resp = self.get_json(url)
        pair = self.pair(asset, quote)
        # Warning - CryptoCompare returns 0 as data for missing dates, convert these to None.
        if 'Data' in json_resp:
            self.update_prices(pair,
                               {datetime.fromtimestamp(d['time']).strftime('%Y-%m-%d'): {
                                   'price': Decimal(repr(d['close'])) if 'close' in d and \
                                           d['close'] else None,
                                   'url': url} for d in json_resp['Data']},
                               timestamp)

    def get_list(self):
        return {k: [{'id':None, 'name': v['name']}] for k, v in self.assets.items()}

class CoinGecko(DataSourceBase):
    def __init__(self):
        super(CoinGecko, self).__init__()
        json_resp = self.get_json("https://api.coingecko.com/api/v3/coins/list")
        self.ids = {c['id']: {'symbol': c['symbol'].strip().upper(), 'name': c['name'].strip()}
                    for c in json_resp}
        self.assets = {c['symbol'].strip().upper(): {'id': c['id'], 'name': c['name'].strip()}
                       for c in json_resp}
        self.get_config_assets()

    def get_latest(self, asset, quote, asset_id=None):
        if asset_id is None:
            asset_id = self.assets[asset]['id']

        json_resp = self.get_json("https://api.coingecko.com/api/v3/coins/%s?localization=false" \
            "&community_data=false&developer_data=false" % asset_id)
        return Decimal(repr(json_resp['market_data']['current_price'][quote.lower()])) \
                if 'market_data' in json_resp and 'current_price' in json_resp['market_data'] and \
                quote.lower() in json_resp['market_data']['current_price'] else None

    def get_historical(self, asset, quote, timestamp, asset_id=None):
        if asset_id is None:
            asset_id = self.assets[asset]['id']

        url = "https://api.coingecko.com/api/v3/coins/%s/market_chart?vs_currency=%s&days=max" % (
            asset_id, quote)
        json_resp = self.get_json(url)
        pair = self.pair(asset, quote)
        if 'prices' in json_resp:
            self.update_prices(pair,
                               {datetime.utcfromtimestamp(p[0]/1000).strftime('%Y-%m-%d'): {
                                   'price': Decimal(repr(p[1])) if p[1] else None,
                                   'url': url} for p in json_resp['prices']},
                               timestamp)

class CoinPaprika(DataSourceBase):
    def __init__(self):
        super(CoinPaprika, self).__init__()
        json_resp = self.get_json("https://api.coinpaprika.com/v1/coins")
        self.ids = {c['id']: {'symbol': c['symbol'].strip().upper(), 'name': c['name'].strip()}
                    for c in json_resp}
        self.assets = {c['symbol'].strip().upper(): {'id': c['id'], 'name': c['name'].strip()}
                       for c in json_resp}
        self.get_config_assets()

    def get_latest(self, asset, quote, asset_id=None):
        if asset_id is None:
            asset_id = self.assets[asset]['id']

        json_resp = self.get_json("https://api.coinpaprika.com/v1/tickers/%s?quotes=%s" % (
            (asset_id, quote)))
        return Decimal(repr(json_resp['quotes'][quote]['price'])) \
                if 'quotes' in json_resp and quote in json_resp['quotes'] else None

    def get_historical(self, asset, quote, timestamp, asset_id=None):
        # Historic prices only available in USD or BTC
        if quote not in ('USD', 'BTC'):
            return

        if asset_id is None:
            asset_id = self.assets[asset]['id']

        url = "https://api.coinpaprika.com/v1/tickers/%s/historical" \
              "?start=%s&limit=%s&quote=%s&interval=1d" % (
                  asset_id, timestamp.strftime('%Y-%m-%d'), COINPAPRIKA_MAX_DAYS, quote)

        json_resp = self.get_json(url)
        pair = self.pair(asset, quote)
        self.update_prices(pair,
                           {dateutil.parser.parse(p['timestamp']).strftime('%Y-%m-%d'): {
                               'price': Decimal(repr(p['price'])) if p['price'] else None,
                               'url': url} for p in json_resp},
                           timestamp)
