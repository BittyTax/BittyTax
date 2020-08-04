# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import re

from ..config import config
from .datasource import DataSourceBase

class AssetData(object):
    def __init__(self):
        self.data_sources = {}

        for data_source in DataSourceBase.__subclasses__():
            if config.args.datasource and data_source.__name__.upper() == config.args.datasource \
                    or not config.args.datasource:
                self.data_sources[data_source.__name__.upper()] = data_source()

    def get_asset(self, symbol):
        assets = []
        if config.args.datasource:
            if symbol in self.data_sources[config.args.datasource].assets:
                assets.append({'symbol': symbol,
                               'name': self.data_sources[config.args.datasource].assets[symbol],
                               'data_source': self.data_sources[config.args.datasource].name()})
        else:
            for data_source in sorted(self.data_sources):
                if symbol in self.data_sources[data_source].assets:
                    assets.append({'symbol': symbol,
                                   'name': self.data_sources[data_source].assets[symbol],
                                   'data_source': self.data_sources[data_source].name()})
        return assets

    def all_assets(self):
        assets = []

        if config.args.datasource:
            for symbol in self.data_sources[config.args.datasource].assets:
                assets.append({'symbol': symbol,
                               'name': self.data_sources[config.args.datasource].assets[symbol],
                               'data_source': self.data_sources[config.args.datasource].name()})
        else:
            for data_source in self.data_sources:
                for symbol in self.data_sources[data_source].assets:
                    assets.append({'symbol': symbol,
                                   'name': self.data_sources[data_source].assets[symbol],
                                   'data_source': self.data_sources[data_source].name()})

            if config.args.duplicates:
                asset_names = {}
                for asset in assets:
                    asset_names[self.filter_name(asset['symbol']+asset['name'])] = asset
                assets = asset_names.values()

        return sorted(assets, key=lambda a: a['symbol'].lower())

    @staticmethod
    def filter_name(name):
        return re.sub(r'[^\w]', '', name).upper()
