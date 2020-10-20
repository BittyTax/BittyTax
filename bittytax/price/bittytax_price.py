# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import argparse
import sys
import codecs
import platform
import re
from decimal import Decimal, InvalidOperation

import colorama
from colorama import Fore, Back
import dateutil.parser

from ..version import __version__
from ..config import config
from .datasource import DataSourceBase
from .valueasset import ValueAsset
from .exceptions import UnexpectedDataSourceError

if sys.stdout.encoding != 'UTF-8':
    if sys.version_info[:2] >= (3, 7):
        sys.stdout.reconfigure(encoding='utf-8')
    elif sys.version_info[:2] >= (3, 1):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    else:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

def main():
    colorama.init()
    parser = argparse.ArgumentParser()
    parser.add_argument('asset',
                        type=str,
                        nargs=1,
                        help="symbol of cryptoasset or fiat currency (i.e. BTC/LTC/ETH or EUR/USD)")
    parser.add_argument('date',
                        type=validate_date,
                        nargs='?',
                        help="date (YYYY-MM-DD or DD/MM/YYYY)")
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
                        type=validate_quantity,
                        help="quantity to price")
    parser.add_argument('-ds',
                        choices=sorted([ds.__name__.upper()
                                 for ds in DataSourceBase.__subclasses__()]) + ['ALL'],
                        metavar='{' +
                                ', '.join(sorted([ds.__name__ for ds in
                                                  DataSourceBase.__subclasses__()])) +
                                '} or ALL',
                        dest='datasource',
                        type=str.upper,
                        help="specify the data source to use, or all")
    parser.add_argument('-nc',
                        '--nocache',
                        action='store_true', help="bypass cache for historical data")

    config.args = parser.parse_args()

    if config.args.debug:
        print("%s%s v%s" % (Fore.YELLOW, parser.prog, __version__))
        print("%spython: v%s" % (Fore.GREEN, platform.python_version()))
        print("%ssystem: %s, release: %s" % (Fore.GREEN, platform.system(), platform.release()))
        config.output_config()

    symbol = config.args.asset[0]
    if symbol == config.CCY:
        return

    try:
        asset = False
        price = False

        if config.args.datasource == 'ALL':
            for ds in DataSourceBase.__subclasses__():
                value_asset = ValueAsset(price_tool=True, data_source=ds.__name__.upper())
                if config.args.date:
                    price_ccy, name, _ = value_asset.get_historical_price(symbol, config.args.date)
                else:
                    price_ccy, name, _ = value_asset.get_latest_price(symbol)

                if price_ccy is not None:
                    output_price(price_ccy)
                    price = True

                if name is not None:
                    asset = True
        else:
            value_asset = ValueAsset(price_tool=True, data_source=config.args.datasource)
            if config.args.date:
                price_ccy, name, _ = value_asset.get_historical_price(symbol, config.args.date)
            else:
                price_ccy, name, _ = value_asset.get_latest_price(symbol)

            if price_ccy is not None:
                output_price(price_ccy)
                price = True

            if name is not None:
                asset = True

        if not asset:
            parser.exit("%sWARNING%s Prices for %s are not supported" % (
                Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, symbol))

        if not price:
            if config.args.date:
                parser.exit("%sWARNING%s Price for %s on %s is not available" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW,
                    symbol, config.args.date.strftime('%Y-%m-%d')))
            else:
                parser.exit("%sWARNING%s Current price for %s is not available" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, symbol))

    except UnexpectedDataSourceError as e:
        parser.exit("%sERROR%s %s" % (
            Back.RED+Fore.BLACK, Back.RESET+Fore.RED, e))

def output_price(price_ccy):
    symbol = config.args.asset[0]

    print("%s1 %s=%s %s" % (
        Fore.WHITE,
        symbol,
        config.sym() + '{:0,.2f}'.format(price_ccy),
        config.CCY))
    if config.args.quantity:
        quantity = Decimal(config.args.quantity)
        print("%s%s %s=%s %s" % (
            Fore.WHITE,
            '{:0,f}'.format(quantity.normalize()),
            symbol,
            config.sym() + '{:0,.2f}'.format(quantity * price_ccy),
            config.CCY))

def validate_date(value):
    match = re.match(r"^([0-9]{4}-[0-9]{2}-[0-9]{2})|([0-9]{2}\/[0-9]{2}\/[0-9]{4})$", value)

    if not match:
        raise argparse.ArgumentTypeError("date format is not valid, use YYYY-MM-DD or DD/MM/YYYY")

    if match.group(1):
        dayfirst = False
    else:
        dayfirst = True

    try:
        date = dateutil.parser.parse(value, dayfirst=dayfirst)
    except ValueError:
        raise argparse.ArgumentTypeError("date is not valid")

    return date.replace(tzinfo=config.TZ_LOCAL)

def validate_quantity(value):
    try:
        quantity = Decimal(value.replace(',', ''))
    except InvalidOperation:
        raise argparse.ArgumentTypeError("quantity is not valid")

    return quantity
