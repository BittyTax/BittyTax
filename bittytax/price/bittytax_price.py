# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import argparse
import sys
import codecs
import platform
from decimal import Decimal

from colorama import init, Fore, Back
import dateutil.parser

from ..version import __version__
from ..config import config
from .valueasset import ValueAsset
from .exceptions import UnexpectedDataSourceError

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
                        nargs=1,
                        help="symbol of cryptoasset or fiat currency (i.e. BTC/LTC/ETH or EUR/USD)")
    parser.add_argument('date',
                        type=str,
                        nargs='?',
                        help="date (YYYY-MM-DD)")
    parser.add_argument('-v',
                        '--version',
                        action='version',
                        version='%s v%s' % (parser.prog, __version__))
    parser.add_argument('-d',
                        '--debug',
                        action='store_true',
                        help="enabled debug logging")
    parser.add_argument('-q',
                        '--quantity',
                        type=Decimal,
                        help="quantity to price")
    parser.add_argument('-nc',
                        '--nocache',
                        action='store_true', help="bypass cache for historical data")

    config.args = parser.parse_args()

    if config.args.debug:
        print("%s%s v%s" % (Fore.YELLOW, parser.prog, __version__))
        print("%spython: v%s" % (Fore.GREEN, platform.python_version()))
        print("%ssystem: %s, release: %s" % (Fore.GREEN, platform.system(), platform.release()))
        config.output_config()

    value_asset = ValueAsset()
    asset = config.args.asset[0]
    timestamp = None

    if asset == config.CCY:
        return

    try:
        if config.args.date:
            try:
                timestamp = dateutil.parser.parse(config.args.date)
            except ValueError as e:
                if sys.version_info[0] < 3:
                    err_msg = ' '.join(e)
                else:
                    err_msg = ' '.join(e.args)

                parser.exit("%sERROR%s Invalid date: %s" % (
                    Back.RED+Fore.BLACK, Back.RESET+Fore.RED, err_msg))

            timestamp = timestamp.replace(tzinfo=config.TZ_LOCAL)
            price_ccy, name, data_source = value_asset.get_historical_price(asset, timestamp)
        else:
            price_ccy, name, data_source = value_asset.get_latest_price(asset)
    except UnexpectedDataSourceError as e:
        parser.exit("%sERROR%s %s" % (
            Back.RED+Fore.BLACK, Back.RESET+Fore.RED, e))

    if price_ccy is not None:
        print("%s1 %s=%s %s %svia %s (%s)" % (
            Fore.WHITE,
            asset,
            config.sym() + '{:0,.2f}'.format(price_ccy),
            config.CCY,
            Fore.CYAN,
            data_source,
            name))
        if config.args.quantity:
            quantity = Decimal(config.args.quantity)
            print("%s%s %s=%s %s" % (
                Fore.WHITE,
                '{:0,f}'.format(quantity.normalize()),
                asset,
                config.sym() + '{:0,.2f}'.format(quantity * price_ccy),
                config.CCY))
    else:
        if name is not None:
            if timestamp:
                parser.exit("%sWARNING%s Price for %s on %s is not available" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW,
                    asset, timestamp.strftime('%Y-%m-%d')))
            else:
                parser.exit("%sWARNING%s Current price for %s is not available" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, asset))
        else:
            parser.exit("%sWARNING%s Prices for %s are not supported" % (
                Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, asset))
