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
from .assetdata import AssetData
from .valueasset import ValueAsset
from .exceptions import DataSourceError

CMD_LATEST = 'latest'
CMD_HISTORY = 'historic'
CMD_LIST = 'list'

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
    parser.add_argument('-v',
                        '--version',
                        action='version',
                        version='%s v%s' % (parser.prog, __version__))

    if sys.version_info[:2] >= (3, 7):
        subparsers = parser.add_subparsers(dest='command',
                                           required=True)
    else:
        subparsers = parser.add_subparsers(dest='command')

    parser_latest = subparsers.add_parser(CMD_LATEST,
                                          help="get the latest price of an asset",
                                          description="Get the latest [asset] price (in %s). "
                                                      "If no data source [-ds] is given, "
                                                      "the same data source(s) as "
                                                      "'bittytax' are used." % config.ccy)
    parser_latest.add_argument('asset',
                               type=str,
                               nargs=1,
                               help="symbol of cryptoasset or fiat currency "
                                    "(i.e. BTC/LTC/ETH or EUR/USD)")
    parser_latest.add_argument('quantity',
                               type=validate_quantity,
                               nargs='?',
                               help="quantity to price (optional)")
    parser_latest.add_argument('-ds',
                               choices=datasource_choices(upper=True) + ['ALL'],
                               metavar='{' + ', '.join(datasource_choices()) + '} or ALL',
                               dest='datasource',
                               type=str.upper,
                               help="specify the data source to use, or all")
    parser_latest.add_argument('-d',
                               '--debug',
                               action='store_true',
                               help="enable debug logging")

    parser_history = subparsers.add_parser(CMD_HISTORY,
                                           help="get the historical price of an asset",
                                           description="Get the historic [asset] price (in %s) "
                                                       "for the [date] specified. "
                                                       "If no data source [-ds] is given, "
                                                       "the same data source(s) as "
                                                       "'bittytax' are used." % config.ccy)
    parser_history.add_argument('asset',
                                type=str.upper,
                                nargs=1,
                                help="symbol of cryptoasset or fiat currency "
                                     "(i.e. BTC/LTC/ETH or EUR/USD)")
    parser_history.add_argument('date',
                                type=validate_date,
                                nargs=1,
                                help="date (YYYY-MM-DD or DD/MM/YYYY)")
    parser_history.add_argument('quantity',
                                type=validate_quantity,
                                nargs='?',
                                help="quantity to price (optional)")
    parser_history.add_argument('-ds',
                                choices=datasource_choices(upper=True) + ['ALL'],
                                metavar='{' + ', '.join(datasource_choices()) + '} or ALL',
                                dest='datasource',
                                type=str.upper,
                                help="specify the data source to use, or all")
    parser_history.add_argument('-nc',
                                '--nocache',
                                dest='no_cache',
                                action='store_true', help="bypass data cache")
    parser_history.add_argument('-d',
                                '--debug',
                                action='store_true',
                                help="enable debug logging")

    parser_list = subparsers.add_parser(CMD_LIST,
                                        help="list all assets",
                                        description='List all assets, or filter by [asset].')
    parser_list.add_argument('asset',
                             type=str,
                             nargs='?',
                             help="symbol of cryptoasset or fiat currency "
                                  "(i.e. BTC/LTC/ETH or EUR/USD)")
    parser_list.add_argument('-s',
                             type=str,
                             nargs='+',
                             metavar='SEARCH_TERM',
                             dest='search_terms',
                             help="search assets using SEARCH_TERM(S)")
    parser_list.add_argument('-ds',
                             choices=datasource_choices(upper=True) + ['ALL'],
                             metavar='{' + ', '.join(datasource_choices()) + '} or ALL',
                             dest='datasource',
                             type=str.upper,
                             help="specify the data source to use, or all")
    parser_list.add_argument('-d',
                             '--debug',
                             action='store_true',
                             help="enable debug logging")

    args = parser.parse_args()
    config.debug = args.debug

    if config.debug:
        print("%s%s v%s" % (Fore.YELLOW, parser.prog, __version__))
        print("%spython: v%s" % (Fore.GREEN, platform.python_version()))
        print("%ssystem: %s, release: %s" % (Fore.GREEN, platform.system(), platform.release()))
        config.output_config()

    if args.command in (CMD_LATEST, CMD_HISTORY):
        symbol = args.asset[0]
        asset = price = False

        try:
            if args.datasource:
                if args.command == CMD_HISTORY:
                    assets = AssetData().get_historic_price_ds(symbol,
                                                               args.date[0],
                                                               args.datasource,
                                                               args.no_cache)
                else:
                    assets = AssetData().get_latest_price_ds(symbol,
                                                             args.datasource)
                btc = None
                for asset in assets:
                    if asset['price'] is None:
                        continue

                    output_ds_price(asset)
                    if asset['quote'] == 'BTC':
                        if btc is None:
                            if args.command == CMD_HISTORY:
                                btc = get_historic_btc_price(args.date[0])
                            else:
                                btc = get_latest_btc_price()

                        if btc['price'] is not None:
                            price_ccy = btc['price'] * asset['price']
                            output_ds_price(btc)
                            price = True
                    else:
                        price_ccy = asset['price']
                        price = True

                    output_price(symbol, price_ccy, args.quantity)

                if not assets:
                    asset = False
            else:
                value_asset = ValueAsset(price_tool=True)
                if args.command == CMD_HISTORY:
                    price_ccy, name, _ = value_asset.get_historical_price(symbol,
                                                                          args.date[0],
                                                                          args.no_cache)
                else:
                    price_ccy, name, _ = value_asset.get_latest_price(symbol)

                if price_ccy is not None:
                    output_price(symbol, price_ccy, args.quantity)
                    price = True

                if name is not None:
                    asset = True

        except DataSourceError as e:
            parser.exit("%sERROR%s %s" % (Back.RED+Fore.BLACK, Back.RESET+Fore.RED, e))

        if not asset:
            parser.exit("%sWARNING%s Prices for %s are not supported" % (
                Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, symbol))

        if not price:
            if args.command == CMD_HISTORY:
                parser.exit("%sWARNING%s Price for %s on %s is not available" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW,
                    symbol, args.date[0].strftime('%Y-%m-%d')))
            else:
                parser.exit("%sWARNING%s Current price for %s is not available" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, symbol))
    elif args.command == CMD_LIST:
        symbol = args.asset
        try:
            assets = AssetData().get_assets(symbol, args.datasource, args.search_terms)
        except DataSourceError as e:
            parser.exit("%sERROR%s %s" % (Back.RED+Fore.BLACK, Back.RESET+Fore.RED, e))

        if symbol and not assets:
            parser.exit("%sWARNING%s Asset %s not found" % (
                Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, symbol))

        if args.search_terms and not assets:
            parser.exit("No results found")

        output_assets(assets)

def get_latest_btc_price():
    btc = {}
    btc['symbol'] = 'BTC'
    btc['quote'] = config.ccy
    btc['price'], btc['name'], btc['data_source'] = ValueAsset().get_latest_price(btc['symbol'])
    return btc

def get_historic_btc_price(date):
    btc = {}
    btc['symbol'] = 'BTC'
    btc['quote'] = config.ccy
    btc['price'], btc['name'], btc['data_source'] = ValueAsset().get_historical_price(btc['symbol'],
                                                                                      date)
    return btc

def output_price(symbol, price_ccy, quantity):
    print("%s1 %s=%s %s" % (
        Fore.WHITE,
        symbol,
        config.sym() + '{:0,.2f}'.format(price_ccy),
        config.ccy))
    if quantity:
        quantity = Decimal(quantity)
        print("%s%s %s=%s %s" % (
            Fore.WHITE,
            '{:0,f}'.format(quantity.normalize()),
            symbol,
            config.sym() + '{:0,.2f}'.format(quantity * price_ccy),
            config.ccy))

def output_ds_price(asset):
    print("%s1 %s=%s %s %svia %s (%s)%s" % (
        Fore.YELLOW,
        asset['symbol'],
        '{:0,f}'.format(asset['price'].normalize()),
        asset['quote'],
        Fore.CYAN,
        asset['data_source'],
        asset['name'],
        Fore.YELLOW + ' <-' if asset.get('priority') else ''))

def output_assets(assets):
    for asset in assets:
        print("%s%s (%s) %svia %s%s%s" % (
            Fore.WHITE,
            #Fore.YELLOW if asset['priority'] else Fore.WHITE,
            asset['symbol'],
            asset['name'],
            Fore.CYAN,
            asset['data_source'],
            ' [ID:{}]'.format(asset['id']) if asset['id'] else '',
            Fore.YELLOW + ' <-' if asset['priority'] else ''))

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

def datasource_choices(upper=False):
    if upper:
        return sorted([ds.__name__.upper() for ds in DataSourceBase.__subclasses__()])
    return sorted([ds.__name__ for ds in DataSourceBase.__subclasses__()])
