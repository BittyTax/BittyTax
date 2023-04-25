# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import argparse
import codecs
import platform
import re
import sys
from decimal import Decimal, InvalidOperation

import colorama
import dateutil.parser
from colorama import Fore

from ..config import config
from ..constants import ERROR, WARNING
from ..version import __version__
from .assetdata import AssetData
from .datasource import DataSourceBase
from .exceptions import DataSourceError
from .valueasset import ValueAsset

CMD_LATEST = "latest"
CMD_HISTORY = "historic"
CMD_LIST = "list"

if sys.stdout.encoding != "UTF-8":
    if sys.version_info[:2] >= (3, 7):
        sys.stdout.reconfigure(encoding="utf-8")
    else:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())


def main():
    colorama.init()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{parser.prog} v{__version__}",
    )

    if sys.version_info[:2] >= (3, 7):
        subparsers = parser.add_subparsers(dest="command", required=True)
    else:
        subparsers = parser.add_subparsers(dest="command")

    parser_latest = subparsers.add_parser(
        CMD_LATEST,
        help="get the latest price of an asset",
        description=f"Get the latest [asset] price (in {config.ccy}). "
        "If no data source [-ds] is given, the same data source(s) as 'bittytax' are used.",
    )
    parser_latest.add_argument(
        "asset",
        type=str,
        nargs=1,
        help="symbol of cryptoasset or fiat currency (i.e. BTC/LTC/ETH or EUR/USD)",
    )
    parser_latest.add_argument(
        "quantity",
        type=validate_quantity,
        nargs="?",
        help="quantity to price (optional)",
    )
    parser_latest.add_argument(
        "-ds",
        choices=datasource_choices(upper=True) + ["ALL"],
        metavar="{" + ", ".join(datasource_choices()) + "} or ALL",
        dest="datasource",
        type=str.upper,
        help="specify the data source to use, or all",
    )
    parser_latest.add_argument("-d", "--debug", action="store_true", help="enable debug logging")

    parser_history = subparsers.add_parser(
        CMD_HISTORY,
        help="get the historical price of an asset",
        description=f"Get the historic [asset] price (in {config.ccy}) for the [date] specified. "
        "If no data source [-ds] is given, the same data source(s) as 'bittytax' are used.",
    )
    parser_history.add_argument(
        "asset",
        type=str.upper,
        nargs=1,
        help="symbol of cryptoasset or fiat currency (i.e. BTC/LTC/ETH or EUR/USD)",
    )
    parser_history.add_argument(
        "date", type=validate_date, nargs=1, help="date (YYYY-MM-DD or DD/MM/YYYY)"
    )
    parser_history.add_argument(
        "quantity",
        type=validate_quantity,
        nargs="?",
        help="quantity to price (optional)",
    )
    parser_history.add_argument(
        "-ds",
        choices=datasource_choices(upper=True) + ["ALL"],
        metavar="{" + ", ".join(datasource_choices()) + "} or ALL",
        dest="datasource",
        type=str.upper,
        help="specify the data source to use, or all",
    )
    parser_history.add_argument(
        "-nc",
        "--nocache",
        dest="no_cache",
        action="store_true",
        help="bypass data cache",
    )
    parser_history.add_argument("-d", "--debug", action="store_true", help="enable debug logging")

    parser_list = subparsers.add_parser(
        CMD_LIST,
        help="list all assets",
        description="List all assets, or filter by [asset].",
    )
    parser_list.add_argument(
        "asset",
        type=str,
        nargs="?",
        help="symbol of cryptoasset or fiat currency (i.e. BTC/LTC/ETH or EUR/USD)",
    )
    parser_list.add_argument(
        "-s",
        type=str,
        nargs="+",
        metavar="SEARCH_TERM",
        dest="search_terms",
        help="search assets using SEARCH_TERM(S)",
    )
    parser_list.add_argument(
        "-ds",
        choices=datasource_choices(upper=True) + ["ALL"],
        metavar="{" + ", ".join(datasource_choices()) + "} or ALL",
        dest="datasource",
        type=str.upper,
        help="specify the data source to use, or all",
    )
    parser_list.add_argument("-d", "--debug", action="store_true", help="enable debug logging")

    args = parser.parse_args()
    config.debug = args.debug

    if config.debug:
        print(f"{Fore.YELLOW}{parser.prog} v{__version__}")
        print(f"{Fore.GREEN}python: v{platform.python_version()}")
        print(f"{Fore.GREEN}system: {platform.system()}, release: {platform.release()}")
        config.output_config(sys.stdout)

    if args.command in (CMD_LATEST, CMD_HISTORY):
        symbol = args.asset[0]
        asset = price = False

        try:
            if args.datasource:
                if args.command == CMD_HISTORY:
                    assets = AssetData().get_historic_price_ds(
                        symbol, args.date[0], args.datasource, args.no_cache
                    )
                else:
                    assets = AssetData().get_latest_price_ds(symbol, args.datasource)
                btc = None
                for asset in assets:
                    if asset["price"] is None:
                        continue

                    output_ds_price(asset)
                    if asset["quote"] == "BTC":
                        if btc is None:
                            if args.command == CMD_HISTORY:
                                btc = get_historic_btc_price(args.date[0])
                            else:
                                btc = get_latest_btc_price()

                        if btc["price"] is not None:
                            price_ccy = btc["price"] * asset["price"]
                            output_ds_price(btc)
                            price = True
                    else:
                        price_ccy = asset["price"]
                        price = True

                    output_price(symbol, price_ccy, args.quantity)

                if not assets:
                    asset = False
            else:
                value_asset = ValueAsset(price_tool=True)
                if args.command == CMD_HISTORY:
                    price_ccy, name, _ = value_asset.get_historical_price(
                        symbol, args.date[0], args.no_cache
                    )
                else:
                    price_ccy, name, _ = value_asset.get_latest_price(symbol)

                if price_ccy is not None:
                    output_price(symbol, price_ccy, args.quantity)
                    price = True

                if name is not None:
                    asset = True

        except DataSourceError as e:
            parser.exit(f"{ERROR} {e}")

        if not asset:
            parser.exit(f"{WARNING} Prices for {symbol} are not supported")

        if not price:
            if args.command == CMD_HISTORY:
                parser.exit(
                    f"{WARNING} Price for {symbol} on {args.date[0]:%Y-%m-%d} is not available"
                )
            else:
                parser.exit(f"{WARNING} Current price for {symbol} is not available")
    elif args.command == CMD_LIST:
        symbol = args.asset
        try:
            assets = AssetData().get_assets(symbol, args.datasource, args.search_terms)
        except DataSourceError as e:
            parser.exit(f"{ERROR} {e}")

        if symbol and not assets:
            parser.exit(f"{WARNING} Asset {symbol} not found")

        if args.search_terms and not assets:
            parser.exit("No results found")

        output_assets(assets)


def get_latest_btc_price():
    btc = {}
    btc["symbol"] = "BTC"
    btc["quote"] = config.ccy
    btc["price"], btc["name"], btc["data_source"] = ValueAsset().get_latest_price(btc["symbol"])
    return btc


def get_historic_btc_price(date):
    btc = {}
    btc["symbol"] = "BTC"
    btc["quote"] = config.ccy
    btc["price"], btc["name"], btc["data_source"] = ValueAsset().get_historical_price(
        btc["symbol"], date
    )
    return btc


def output_price(symbol, price_ccy, quantity):
    print(f"{Fore.WHITE}1 {symbol}={config.sym()}{price_ccy:0,.2f} {config.ccy}")
    if quantity:
        quantity = Decimal(quantity)
        print(
            f"{Fore.WHITE}{quantity.normalize():0,f} {symbol}="
            f"{config.sym()}{quantity * price_ccy:0,.2f} {config.ccy}"
        )


def output_ds_price(asset):
    print(
        f'{Fore.YELLOW}1 {asset["symbol"]}={asset["price"].normalize():0,f} {asset["quote"]} '
        f'{Fore.CYAN} via {asset["data_source"]} ({asset["name"]})'
        f'{Fore.YELLOW + " <-" if asset.get("priority") else ""}'
    )


def output_assets(assets):
    for asset in assets:
        if asset["id"]:
            id_str = f' [ID:{asset["id"]}]'
        else:
            id_str = ""

        print(
            f'{Fore.WHITE}{asset["symbol"]} ({asset["name"]})'
            f'{Fore.CYAN} via {asset["data_source"]}{id_str}'
            f'{Fore.YELLOW + " <-" if asset["priority"] else ""}'
        )


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
    except ValueError as e:
        raise argparse.ArgumentTypeError("date is not valid") from e

    return date.replace(tzinfo=config.TZ_LOCAL)


def validate_quantity(value):
    try:
        quantity = Decimal(value.replace(",", ""))
    except InvalidOperation as e:
        raise argparse.ArgumentTypeError("quantity is not valid") from e

    return quantity


def datasource_choices(upper=False):
    if upper:
        return sorted([ds.__name__.upper() for ds in DataSourceBase.__subclasses__()])
    return sorted([ds.__name__ for ds in DataSourceBase.__subclasses__()])


if __name__ == "__main__":
    main()
