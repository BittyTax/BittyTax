# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import logging
import os
import platform
import pkg_resources

import yaml
import dateutil.tz

from .version import __version__

log = logging.getLogger()

class Config(object):
    TZ_INFOS = {'BST': dateutil.tz.gettz('Europe/London'),
                'GMT': dateutil.tz.gettz('Europe/London')}
    TZ_LOCAL = dateutil.tz.gettz('Europe/London')
    TZ_UTC = dateutil.tz.UTC
    CCY = 'GBP'

    BITTYTAX_PATH = os.path.expanduser('~/.bittytax')
    BITTYTAX_CONFIG = 'bittytax.conf'
    CACHE_DIR = os.path.join(BITTYTAX_PATH, 'cache')

    FIAT_LIST = ['GBP', 'EUR', 'USD']
    CRYPTO_LIST = ['BTC', 'ETH', 'XRP', 'LTC', 'BCH', 'USDT']

    FORMAT_CSV = 'CSV'
    FORMAT_EXCEL = 'EXCEL'
    FORMAT_RECAP = 'RECAP'

    TRADE_ASSET_TYPE_BUY = 0
    TRADE_ASSET_TYPE_SELL = 1
    TRADE_ASSET_TYPE_PRIORITY = 2

    DATA_SOURCE_FIAT = ["ExchangeRatesAPI", "RatesAPI"]
    DATA_SOURCE_CRYPTO = ["CryptoCompare", "CoinGecko"]

    DEFAULT_CONFIG = {
        'fiat_list': FIAT_LIST,
        'crypto_list': CRYPTO_LIST,
        'trade_asset_type': TRADE_ASSET_TYPE_PRIORITY,
        'show_empty_wallets': False,
        'transfers_include': True,
        'data_source_select': {},
        'data_source_fiat': DATA_SOURCE_FIAT,
        'data_source_crypto': DATA_SOURCE_CRYPTO,
    }

    def __init__(self):
        self.args = None

        if not os.path.exists(Config.BITTYTAX_PATH):
            os.mkdir(Config.BITTYTAX_PATH)

        if not os.path.exists(os.path.join(Config.BITTYTAX_PATH, Config.BITTYTAX_CONFIG)):
            default_conf = pkg_resources.resource_string(__name__,
                                                         'config/' + Config.BITTYTAX_CONFIG)
            with open(os.path.join(Config.BITTYTAX_PATH,
                                   Config.BITTYTAX_CONFIG), 'wb') as config_file:
                config_file.write(default_conf)

        try:
            with open(os.path.join(Config.BITTYTAX_PATH,
                                   Config.BITTYTAX_CONFIG), "rb") as config_file:
                self.config = yaml.safe_load(config_file)
        except:
            self.log.warning("Config file cannot be loaded: %s",
                             os.path.join(Config.BITTYTAX_PATH, Config.BITTYTAX_CONFIG))
            self.config = {}

        for name, default in self.DEFAULT_CONFIG.items():
            if name not in self.config:
                self.config[name] = default

        self.asset_priority = self.config['fiat_list'] + self.config['crypto_list']

    def __getattr__(self, name):
        try:
            return self.config[name]
        except KeyError:
            return getattr(self.args, name)

    def output_config(self, progname):
        log.debug("BITTYTAX: %s v%s", progname, __version__)
        log.debug("PYTHON: v%s SYSTEM: %s RELEASE: %s",
                  platform.python_version(), platform.system(), platform.release())

        for name in sorted(self.DEFAULT_CONFIG):
            log.debug("CONFIG: %s = %s", name, self.config[name])

    def sym(self):
        if self.CCY == 'GBP':
            return u'\xA3' # £
        else:
            raise ValueError("Currency not supported")

config = Config()
