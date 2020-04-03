# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
import logging
import argparse
from decimal import Decimal

import dateutil.parser

from ..version import __version__
from ..config import config
from .valueasset import ValueAsset

if sys.version_info[0] >= 3:
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO,
                    format='[%(asctime)s.%(msecs)03d] %(levelname)s -- : %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S')
log = logging.getLogger()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("asset",
                        type=str,
                        nargs=1,
                        help="symbol of cryptoasset or fiat currency (i.e. BTC/LTC/ETH or EUR/USD)")
    parser.add_argument("date",
                        type=str,
                        nargs='?',
                        help="date (YYYY-MM-DD)")
    parser.add_argument("-v",
                        "--version",
                        action='version',
                        version='%(prog)s {version}'.format(version=__version__))
    parser.add_argument("-d",
                        "--debug",
                        action='store_true',
                        help="enabled debug logging")
    parser.add_argument("-q",
                        "--quantity",
                        type=Decimal,
                        help="quantity to price")
    parser.add_argument("-nc",
                        "--nocache",
                        action='store_true', help="bypass cache for historical data")

    config.args = parser.parse_args()

    if config.args.debug:
        log.setLevel(logging.DEBUG)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        config.output_config(parser.prog)

    value_asset = ValueAsset()
    asset = config.args.asset[0]
    timestamp = None

    if asset == config.CCY:
        return

    if config.args.date:
        timestamp = dateutil.parser.parse(config.args.date)
        timestamp = timestamp.replace(tzinfo=config.TZ_LOCAL)
        price_ccy, name, data_source = value_asset.get_historical_price(asset, timestamp)
    else:
        price_ccy, name, data_source = value_asset.get_latest_price(asset)

    if price_ccy is not None:
        log.info("1 %s=%s%s %s via %s (%s)",
                 asset,
                 config.sym(), '{:0,.2f}'.format(price_ccy), config.CCY,
                 data_source, name)
        if config.args.quantity:
            quantity = Decimal(config.args.quantity)
            log.info("%s %s=%s%s %s",
                     '{:0,f}'.format(quantity.normalize()),
                     asset,
                     config.sym(), '{:0,.2f}'.format(quantity * price_ccy), config.CCY)
    else:
        if name is not None:
            if timestamp:
                log.warning("Price for %s at %s is not available",
                            asset, timestamp.strftime('%Y-%m-%d'))
            else:
                log.warning("Current price for %s is not available", asset)
        else:
            log.warning("Prices for %s are not supported", asset)
