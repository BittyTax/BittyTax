# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import argparse
import sys
import codecs
import platform

from colorama import init, Fore, Back

from ..version import __version__
from ..config import config
from .datasource import DataSourceBase
from .assetdata import AssetData

if sys.stdout.encoding != 'UTF-8':
    if sys.version_info[0] < 3:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
    else:
        sys.stdout.reconfigure(encoding='utf-8')

def main():
    init()
    parser = argparse.ArgumentParser()
    parser.add_argument('asset',
                        type=str,
                        nargs='?',
                        help="symbol of cryptoasset or fiat currency (i.e. BTC/LTC/ETH or EUR/USD)")
    parser.add_argument('-v',
                        '--version',
                        action='version',
                        version='%s v%s' % (parser.prog, __version__))
    parser.add_argument('-d',
                        '--debug',
                        action='store_true',
                        help="enabled debug logging")
    parser.add_argument('-ds',
                        choices=sorted([ds.__name__.upper()
                                        for ds in DataSourceBase.__subclasses__()]),
                        dest='datasource',
                        type=str.upper,
                        help="specify the data source to use")
    parser.add_argument('--duplicates',
                        action='store_true',
                        help="remove any duplicate assets (same symbol and name) "
                             "when displaying all assets")

    config.args = parser.parse_args()

    if config.args.duplicates and (config.args.datasource or config.args.asset):
        parser.error("--duplicates cannot be used when a data source [-ds]"
                     " or an asset is specified")

    if config.args.debug:
        print("%s%s v%s" % (Fore.YELLOW, parser.prog, __version__))
        print("%spython: v%s" % (Fore.GREEN, platform.python_version()))
        print("%ssystem: %s, release: %s" % (Fore.GREEN, platform.system(), platform.release()))

    asset_data = AssetData()

    if config.args.asset:
        assets = asset_data.get_asset(config.args.asset)
        if not assets:
            if config.args.datasource:
                parser.exit("%sWARNING%s Asset %s is not supported by %s" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW,
                    config.args.asset,
                    asset_data.data_sources[config.args.datasource].name()))
            else:
                parser.exit("%sWARNING%s Asset %s is not supported" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW,
                    config.args.asset))
    else:
        assets = asset_data.all_assets()

    for asset in assets:
        print("%s%s (%s) %svia %s" % (
            Fore.WHITE,
            asset['symbol'],
            asset['name'],
            Fore.CYAN,
            asset['data_source']))
