# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import datetime
import os
import platform
import sys
from typing import Any, TextIO

import yaml
from colorama import Fore

from .bt_types import CostBasisMethod, CostTrackingMethod, TaxRules, UniversalOrdering
from .constants import BITTYTAX_PATH, ERROR

if sys.version_info < (3, 9):
    import importlib_resources as pkg_resources
else:
    import importlib.resources as pkg_resources


class Config:
    BITTYTAX_CONFIG = "bittytax.conf"

    FIAT_LIST = ["GBP", "EUR", "USD", "AUD", "NZD", "CAD", "PLN"]
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
        "local_currency": "USD",
        "local_timezone": "America/New_York",
        "date_is_day_first": False,
        "default_tax_rules": "US_INDIVIDUAL_FIFO",
        "cost_tracking_method": CostTrackingMethod.UNIVERSAL,
        "universal_ordering": UniversalOrdering.TID,
        "fiat_list": FIAT_LIST,
        "crypto_list": CRYPTO_LIST,
        "trade_asset_type": TRADE_ASSET_TYPE_PRIORITY,
        "trade_allowable_cost_type": TRADE_ASSET_TYPE_BUY,
        "transaction_fee_allowable_cost": False,
        "audit_hide_empty": False,
        "show_empty_wallets": False,
        "transfers_include": False,
        "transfer_fee_disposal": True,
        "transfer_fee_allowable_cost": False,
        "cost_basis_zero_if_missing": False,
        "fiat_income": True,
        "lost_buyback": False,
        "large_data": False,
        "classic_report": False,
        "data_source_select": {},
        "data_source_fiat": DATA_SOURCE_FIAT,
        "data_source_crypto": DATA_SOURCE_CRYPTO,
        "usernames": [],
        "coinbase_zero_fees_are_gifts": False,
        "binance_multi_bnb_split_even": False,
        "binance_statements_only": False,
    }

    OPTIONAL_CONFIG = (
        "coingecko_pro_api_key",
        "coingecko_demo_api_key",
        "cryptocompare_api_key",
        "coinpaprika_api_key",
    )

    def __init__(self) -> None:
        self.terminal = os.getenv("BITTYTAX_TERMINAL")
        self.debug = False
        self.start_of_year_month = 1
        self.start_of_year_day = 1
        # self.date_format = "%m/%d/%Y"

        if platform.system() == "Windows":
            self.date_format = "%b %#d, %Y"
        else:
            self.date_format = "%b %-d, %Y"

        if not os.path.exists(BITTYTAX_PATH):
            os.mkdir(BITTYTAX_PATH)

        if not os.path.exists(os.path.join(BITTYTAX_PATH, self.BITTYTAX_CONFIG)):
            default_conf = (
                pkg_resources.files(__package__)
                .joinpath(f"config/{self.BITTYTAX_CONFIG}")
                .read_bytes()
            )
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

        if self.config is None:
            self.config = {}

        try:
            self.config["cost_tracking_method"] = CostTrackingMethod(
                self.config.get("cost_tracking_method")
            )
        except ValueError:
            self.config["cost_tracking_method"] = self.DEFAULT_CONFIG["cost_tracking_method"]

        try:
            self.config["universal_ordering"] = UniversalOrdering(
                self.config.get("universal_ordering")
            )
        except ValueError:
            self.config["universal_ordering"] = self.DEFAULT_CONFIG["universal_ordering"]

        for name, default in self.DEFAULT_CONFIG.items():
            if name not in self.config:
                self.config[name] = default

        self.ccy = self.config["local_currency"]
        self.asset_priority = self.config["fiat_list"] + self.config["crypto_list"]

    def __getattr__(self, name: str) -> Any:
        return self.config[name]

    def output_config(self, file: TextIO) -> None:
        if config.terminal:
            if sys.__stderr__ is not None:
                file = sys.__stderr__
            file.write(f"{Fore.GREEN}config: env BITTYTAX_TERMINAL={self.terminal}\n")

        file.write(f'{Fore.GREEN}config: "{os.path.join(BITTYTAX_PATH, self.BITTYTAX_CONFIG)}"\n')

        for name in self.DEFAULT_CONFIG:
            file.write(f"{Fore.GREEN}config: {name}: {self.config[name]}\n")

        for name in self.OPTIONAL_CONFIG:
            if name in self.config:
                file.write(f"{Fore.GREEN}config: {name}: {self._mask_data(self.config[name])}\n")

    def sym(self) -> str:
        if self.ccy == "GBP":
            return "\xa3"  # £
        if self.ccy == "EUR":
            return "\u20ac"  # €
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

    def get_cost_method(self, tax_rules: TaxRules, tax_year: int) -> str:
        if tax_rules is TaxRules.US_INDIVIDUAL_FIFO:
            cost_basis_method = CostBasisMethod.FIFO
        elif tax_rules is TaxRules.US_INDIVIDUAL_LIFO:
            cost_basis_method = CostBasisMethod.LIFO
        elif tax_rules is TaxRules.US_INDIVIDUAL_HIFO:
            cost_basis_method = CostBasisMethod.HIFO
        elif tax_rules is TaxRules.US_INDIVIDUAL_LOFO:
            cost_basis_method = CostBasisMethod.LOFO
        else:
            raise RuntimeError("Unexpected tax_rules")

        if self.is_per_wallet(tax_year):
            return f"{cost_basis_method.value} Per-Wallet"
        return f"{cost_basis_method.value} Universal"

    def is_per_wallet(self, tax_year: int) -> bool:
        if config.cost_tracking_method is CostTrackingMethod.UNIVERSAL:
            return False
        if (
            config.cost_tracking_method is CostTrackingMethod.PER_WALLET_1JAN2025
            and tax_year < 2025
        ):
            return False
        return True

    def format_tax_year(self, tax_year: int) -> str:
        start = self.get_tax_year_start(tax_year)
        end = self.get_tax_year_end(tax_year)

        if start.year == end.year:
            return f"{start:%Y}"
        return f"{start:%Y}/{end:%y}"

    @staticmethod
    def _mask_data(data: str, show: int = 4) -> str:
        return data[-show:].rjust(len(data), "#")


config = Config()
