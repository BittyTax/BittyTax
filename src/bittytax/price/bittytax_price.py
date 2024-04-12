# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import argparse
import platform
import re
import sys
from decimal import Decimal, InvalidOperation
from typing import List

import colorama
import dateutil.parser
from colorama import Fore

from ..bt_types import AssetSymbol, Timestamp
from ..config import config
from ..constants import ERROR, TZ_UTC, WARNING
from ..version import __version__
from .assetdata import AsPriceRecord, AsRecord, AssetData
from .datasource import DataSourceBase
from .exceptions import DataSourceError
from .valueasset import ValueAsset

CMD_LATEST = "latest"
CMD_HISTORY = "historic"
CMD_LIST = "list"

if sys.stdout.encoding != "UTF-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]


def main() -> None:
    colorama.init()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{parser.prog} v{__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

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
                for asset_data in assets:
                    if asset_data["price"] is None:
                        continue

                    output_ds_price(asset_data)
                    if asset_data["quote"] == "BTC":
                        if btc is None:
                            if args.command == CMD_HISTORY:
                                btc = get_historic_btc_price(args.date[0])
                            else:
                                btc = get_latest_btc_price()

                        if btc["price"] is not None:
                            price_ccy = btc["price"] * asset_data["price"]
                            output_ds_price(btc)
                            price = True
                    else:
                        price_ccy = asset_data["price"]
                        price = True

                    output_price(symbol, price_ccy, args.quantity)

                if assets:
                    asset = True
            else:
                value_asset = ValueAsset(price_tool=True)
                if args.command == CMD_HISTORY:
                    price_ccy2, name, _ = value_asset.get_historical_price(
                        symbol, args.date[0], args.no_cache
                    )
                else:
                    price_ccy2, name, _ = value_asset.get_latest_price(symbol)

                if price_ccy2 is not None:
                    output_price(symbol, price_ccy2, args.quantity)
                    price = True

                if name:
                    asset = True

        except DataSourceError as e:
            parser.exit(message=f"{ERROR} {e}\n")

        if not asset:
            parser.exit(message=f"{WARNING} Prices for {symbol} are not supported\n")

        if not price:
            if args.command == CMD_HISTORY:
                parser.exit(
                    message=f"{WARNING} Price for {symbol} on {args.date[0]:%Y-%m-%d} "
                    "is not available\n"
                )
            else:
                parser.exit(message=f"{WARNING} Current price for {symbol} is not available\n")
    elif args.command == CMD_LIST:
        symbol = args.asset
        try:
            asset_list = AssetData().get_assets(symbol, args.datasource, args.search_terms)
        except DataSourceError as e:
            parser.exit(message=f"{ERROR} {e}\n")

        if symbol and not asset_list:
            parser.exit(message=f"{WARNING} Asset {symbol} not found\n")

        if args.search_terms and not asset_list:
            parser.exit(message="No results found\n")

        output_assets(asset_list)


def get_latest_btc_price() -> AsPriceRecord:
    price_ccy, name, data_source = ValueAsset().get_latest_price(AssetSymbol("BTC"))
    if price_ccy is not None:
        return AsPriceRecord(
            symbol=AssetSymbol("BTC"),
            name=name,
            data_source=data_source,
            price=price_ccy,
            quote=config.ccy,
        )
    raise RuntimeError("BTC price is not available")


def get_historic_btc_price(date: Timestamp) -> AsPriceRecord:
    price_ccy, name, data_source = ValueAsset().get_historical_price(AssetSymbol("BTC"), date)
    if price_ccy is not None:
        return AsPriceRecord(
            symbol=AssetSymbol("BTC"),
            name=name,
            data_source=data_source,
            price=price_ccy,
            quote=config.ccy,
        )
    raise RuntimeError("BTC price is not available")


def output_price(symbol: AssetSymbol, price_ccy: Decimal, quantity: Decimal) -> None:
    print(f"{Fore.WHITE}1 {symbol}={config.sym()}{price_ccy:0,.2f} {config.ccy}")
    if quantity:
        print(
            f"{Fore.WHITE}{quantity.normalize():0,f} {symbol}="
            f"{config.sym()}{quantity * price_ccy:0,.2f} {config.ccy}"
        )


def output_ds_price(asset_data: AsPriceRecord) -> None:
    if asset_data["price"] is None:
        raise RuntimeError("Missing price")

    print(
        f'{Fore.YELLOW}1 {asset_data["symbol"]}='
        f'{asset_data["price"].normalize():0,f} {asset_data["quote"]}'
        f'{Fore.CYAN} via {asset_data["data_source"]} ({asset_data["name"]})'
        f'{Fore.YELLOW + " <-" if asset_data.get("priority") else ""}'
    )


def output_assets(asset_list: List[AsRecord]) -> None:
    for asset_record in asset_list:
        if asset_record["asset_id"]:
            id_str = f' [ID:{asset_record["asset_id"]}]'
        else:
            id_str = ""

        print(
            f'{Fore.WHITE}{asset_record["symbol"]} ({asset_record["name"]})'
            f'{Fore.CYAN} via {asset_record["data_source"]}{id_str}'
            f'{Fore.YELLOW + " <-" if asset_record["priority"] else ""}'
        )


def validate_date(value: str) -> Timestamp:
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

    return Timestamp(date.replace(tzinfo=TZ_UTC))


def validate_quantity(value: str) -> Decimal:
    try:
        quantity = Decimal(value.replace(",", ""))
    except InvalidOperation as e:
        raise argparse.ArgumentTypeError("quantity is not valid") from e

    return quantity


def datasource_choices(upper: bool = False) -> List[str]:
    if upper:
        return sorted([ds.__name__.upper() for ds in DataSourceBase.__subclasses__()])
    return sorted([ds.__name__ for ds in DataSourceBase.__subclasses__()])


if __name__ == "__main__":
    main()
