# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import datetime
import os
import sys
from typing import Any, TextIO

import dateutil.tz
import pkg_resources
import yaml
from colorama import Fore

from .constants import BITTYTAX_PATH, ERROR


class Config:
    BITTYTAX_CONFIG = "bittytax.conf"

    TZ_LOCAL = dateutil.tz.gettz("Europe/London")

    FIAT_LIST = ["GBP", "EUR", "USD"]
    CRYPTO_LIST = ["BTC", "ETH", "XRP", "LTC", "BCH", "USDT"]

    TRADE_ASSET_TYPE_BUY = 0
    TRADE_ASSET_TYPE_SELL = 1
    TRADE_ASSET_TYPE_PRIORITY = 2

    TRADE_ALLOWABLE_COST_BUY = 0
    TRADE_ALLOWABLE_COST_SELL = 1
    TRADE_ALLOWABLE_COST_SPLIT = 2

    DATA_SOURCE_FIAT = ["BittyTaxAPI"]
    DATA_SOURCE_CRYPTO = ["CryptoCompare", "CoinGecko"]

    DEFAULT_CONFIG = {
        "local_currency": "GBP",
        "fiat_list": FIAT_LIST,
        "crypto_list": CRYPTO_LIST,
        "trade_asset_type": TRADE_ASSET_TYPE_PRIORITY,
        "trade_allowable_cost_type": TRADE_ALLOWABLE_COST_SPLIT,
        "audit_hide_empty": False,
        "show_empty_wallets": False,
        "transfers_include": False,
        "transfer_fee_disposal": True,
        "transfer_fee_allowable_cost": False,
        "fiat_income": False,
        "lost_buyback": True,
        "data_source_select": {},
        "data_source_fiat": DATA_SOURCE_FIAT,
        "data_source_crypto": DATA_SOURCE_CRYPTO,
        "usernames": [],
        "coinbase_zero_fees_are_gifts": False,
        "binance_multi_bnb_split_even": False,
    }

    def __init__(self) -> None:
        self.debug = False
        self.start_of_year_month = 4
        self.start_of_year_day = 6

        if not os.path.exists(BITTYTAX_PATH):
            os.mkdir(BITTYTAX_PATH)

        if not os.path.exists(os.path.join(BITTYTAX_PATH, self.BITTYTAX_CONFIG)):
            default_conf = pkg_resources.resource_string(__name__, "config/" + self.BITTYTAX_CONFIG)
            with open(os.path.join(BITTYTAX_PATH, self.BITTYTAX_CONFIG), "wb") as config_file:
                config_file.write(default_conf)

        try:
            with open(os.path.join(BITTYTAX_PATH, self.BITTYTAX_CONFIG), "rb") as config_file:
                self.config = yaml.safe_load(config_file)
        except IOError:
            sys.stderr.write(
                f"{ERROR}Config file cannot be loaded: "
                f"{os.path.join(BITTYTAX_PATH, self.BITTYTAX_CONFIG)}\n"
            )
            sys.exit(1)
        except yaml.scanner.ScannerError as e:
            sys.stderr.write(f"{ERROR}Config file contains an error:\n{e}\n")
            sys.exit(1)

        for name, default in self.DEFAULT_CONFIG.items():
            if name not in self.config:
                self.config[name] = default

        self.ccy = self.config["local_currency"]
        self.asset_priority = self.config["fiat_list"] + self.config["crypto_list"]

    def __getattr__(self, name: str) -> Any:
        return self.config[name]

    def output_config(self, sys_out: TextIO) -> None:
        sys_out.write(
            f'{Fore.GREEN}config: "{os.path.join(BITTYTAX_PATH, self.BITTYTAX_CONFIG)}"\n'
        )

        for name in self.DEFAULT_CONFIG:
            sys_out.write(f"{Fore.GREEN}config: {name}: {self.config[name]}\n")

    def sym(self) -> str:
        if self.ccy == "GBP":
            return "\xA3"  # £
        if self.ccy == "EUR":
            return "\u20AC"  # €
        if self.ccy in ("USD", "AUD", "NZD"):
            return "$"
        if self.ccy in ("DKK", "NOK", "SEK"):
            return "kr."

        raise RuntimeError("Currency not supported")

    def get_tax_year_start(self, tax_year: int) -> datetime.date:
        if self.start_of_year_month != 1:
            return datetime.date(
                tax_year - 1,
                self.start_of_year_month,
                self.start_of_year_day,
            )
        return datetime.date(
            tax_year,
            self.start_of_year_month,
            self.start_of_year_day,
        )

    def get_tax_year_end(self, tax_year: int) -> datetime.date:
        if self.start_of_year_month == 1:
            return datetime.date(
                tax_year + 1,
                self.start_of_year_month,
                self.start_of_year_day,
            ) - datetime.timedelta(days=1)
        return datetime.date(
            tax_year,
            self.start_of_year_month,
            self.start_of_year_day,
        ) - datetime.timedelta(days=1)

    def format_tax_year(self, tax_year: int) -> str:
        start = self.get_tax_year_start(tax_year)
        end = self.get_tax_year_end(tax_year)

        if start.year == end.year:
            return f"{start:%Y}"
        return f"{start:%Y}/{end:%y}"


config = Config()
