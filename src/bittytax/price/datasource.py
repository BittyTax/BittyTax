# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import atexit
import json
import os
import platform
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import dateutil.parser
import requests
from colorama import Fore
from typing_extensions import TypedDict

from ..bt_types import (
    AssetId,
    AssetName,
    AssetSymbol,
    DataSourceName,
    Date,
    QuoteSymbol,
    SourceUrl,
    Timestamp,
    TradingPair,
)
from ..config import config
from ..constants import CACHE_DIR, TZ_UTC, WARNING
from ..version import __version__
from .exceptions import UnexpectedDataSourceAssetIdError


class DsSymbolToAssetData(TypedDict):  # pylint: disable=too-few-public-methods
    asset_id: AssetId
    name: AssetName


class DsIdToAssetData(TypedDict):  # pylint: disable=too-few-public-methods
    symbol: AssetSymbol
    name: AssetName


class DsPriceData(TypedDict):  # pylint: disable=too-few-public-methods
    price: Optional[Decimal]
    url: SourceUrl


class DataSourceBase:
    USER_AGENT = (
        f"BittyTax/{__version__} Python/{platform.python_version()} "
        f"{platform.system()}/{platform.release()}"
    )

    TIME_OUT = 30

    def __init__(self) -> None:
        self.headers = {"User-Agent": self.USER_AGENT}
        self.assets: Dict[AssetSymbol, DsSymbolToAssetData] = {}
        self.ids: Dict[AssetId, DsIdToAssetData] = {}
        self.prices = self._load_prices()

        for pair in sorted(self.prices):
            if config.debug:
                print(f"{Fore.YELLOW}price: {self.name()} ({pair}) data cache loaded")

        atexit.register(self._cache_prices)

    def name(self) -> DataSourceName:
        return DataSourceName(self.__class__.__name__)

    def get_json(self, url: str) -> Any:
        if config.debug:
            print(f"{Fore.YELLOW}price: GET {url} {list(self.headers.keys())}")

        response = requests.get(url, headers=self.headers, timeout=self.TIME_OUT)

        if response.status_code in [401, 402, 403, 429, 502, 503, 504]:
            response.raise_for_status()

        if response:
            return response.json()
        return {}

    def update_prices(
        self, pair: TradingPair, prices: Dict[Date, DsPriceData], timestamp: Timestamp
    ) -> None:
        if pair not in self.prices:
            self.prices[pair] = {}

        # We are not interested in today's latest price, only the days closing price, also need to
        #  filter any erroneous future dates returned
        prices = {k: v for k, v in prices.items() if k < datetime.now().date()}

        # We might not receive data for the date requested, if so set to None to prevent repeat
        #  lookups, assuming date is in the past
        date = Date(timestamp.date())
        if date not in prices and date < datetime.now().date():
            prices[date] = {"price": None, "url": SourceUrl("")}

        self.prices[pair].update(prices)

    def _load_prices(self) -> Dict[TradingPair, Dict[Date, DsPriceData]]:
        filename = os.path.join(CACHE_DIR, self.name() + ".json")
        if not os.path.exists(filename):
            return {}

        try:
            with open(filename, "r", encoding="utf-8") as price_cache:
                json_prices = json.load(price_cache)
                return {
                    pair: {
                        self.str_to_date(date): {
                            "price": self.str_to_decimal(price["price"]),
                            "url": price["url"],
                        }
                        for date, price in json_prices[pair].items()
                    }
                    for pair in json_prices
                }
        except (IOError, ValueError):
            print(f"{WARNING} Data cached for {self.name()} could not be loaded")
            return {}

    def _cache_prices(self) -> None:
        with open(
            os.path.join(CACHE_DIR, self.name() + ".json"), "w", encoding="utf-8"
        ) as price_cache:
            json_prices = {
                pair: {
                    f"{date:%Y-%m-%d}": {
                        "price": self.decimal_to_str(price["price"]),
                        "url": price["url"],
                    }
                    for date, price in self.prices[pair].items()
                }
                for pair in self.prices
            }
            json.dump(json_prices, price_cache, indent=4, sort_keys=True)

    def get_config_assets(self) -> None:
        for symbol in config.data_source_select:
            for ds_select in config.data_source_select[symbol]:
                if ds_select.upper().startswith(self.name().upper() + ":"):  # pylint: disable=E1101
                    if symbol in self.assets:
                        self._update_asset(symbol, ds_select)
                    else:
                        self._add_asset(symbol, ds_select)

    def _update_asset(self, symbol: AssetSymbol, ds_select: str) -> None:
        asset_id = AssetId(ds_select.split(":")[1])
        # Update an existing symbol, validate id belongs to that symbol
        if asset_id in self.ids and self.ids[asset_id]["symbol"] == symbol:
            self.assets[symbol] = {"asset_id": asset_id, "name": self.ids[asset_id]["name"]}

            if config.debug:
                print(
                    f"{Fore.YELLOW}price: "
                    f"{symbol} updated as {self.name()} [ID:{asset_id}] "
                    f'({self.ids[asset_id]["name"]})'
                )
        else:
            raise UnexpectedDataSourceAssetIdError(ds_select, symbol)

    def _add_asset(self, symbol: AssetSymbol, ds_select: str) -> None:
        asset_id = AssetId(ds_select.split(":")[1])
        if asset_id in self.ids:
            self.assets[symbol] = {"asset_id": asset_id, "name": self.ids[asset_id]["name"]}
            self.ids[asset_id] = {"symbol": symbol, "name": self.ids[asset_id]["name"]}

            if config.debug:
                print(
                    f"{Fore.YELLOW}price: "
                    f"{symbol} added as {self.name()} [ID:{asset_id}] "
                    f'({self.ids[asset_id]["name"]})'
                )
        else:
            raise UnexpectedDataSourceAssetIdError(ds_select, symbol)

    def get_list(self) -> Dict[AssetSymbol, List[DsSymbolToAssetData]]:
        if self.ids:
            asset_list: Dict[AssetSymbol, List[DsSymbolToAssetData]] = {}
            for t, ids in self.ids.items():
                symbol = ids["symbol"]
                if symbol not in asset_list:
                    asset_list[symbol] = []

                asset_list[symbol].append({"asset_id": t, "name": ids["name"]})

            # Include any custom symbols as well
            for symbol, assets in asset_list.items():
                if self.assets[symbol] not in assets:
                    assets.append(self.assets[symbol])

            return asset_list
        return {k: [{"asset_id": AssetId(""), "name": v["name"]}] for k, v in self.assets.items()}

    def get_latest(
        self, _asset: AssetSymbol, _quote: QuoteSymbol, _asset_id: AssetId = AssetId("")
    ) -> Optional[Decimal]: ...

    def get_historical(
        self,
        _asset: AssetSymbol,
        _quote: QuoteSymbol,
        _timestamp: Timestamp,
        _asset_id: AssetId = AssetId(""),
    ) -> None: ...

    @classmethod
    def datasources_str(cls) -> str:
        return f"{{{','.join([ds.__name__ for ds in cls.__subclasses__()])}}}"

    @staticmethod
    def pair(asset: AssetSymbol, quote: QuoteSymbol) -> TradingPair:
        return TradingPair(asset + "/" + quote)

    @staticmethod
    def str_to_date(date: str) -> Date:
        return Date(dateutil.parser.parse(date).date())

    @staticmethod
    def str_to_decimal(price: str) -> Optional[Decimal]:
        if price:
            return Decimal(price)

        return None

    @staticmethod
    def decimal_to_str(price: Optional[Decimal]) -> Optional[str]:
        if price:
            return f"{price:f}"

        return None

    @staticmethod
    def epoch_time(timestamp: Timestamp) -> int:
        epoch = timestamp - Timestamp(datetime(1971, 1, 1, tzinfo=TZ_UTC))
        return int(epoch.total_seconds())


class BittyTaxAPI(DataSourceBase):
    def __init__(self) -> None:
        super().__init__()
        json_resp = self.get_json("https://api.bitty.tax/v1/symbols")
        self.assets = {
            k: {"asset_id": AssetId(""), "name": v} for k, v in json_resp["symbols"].items()
        }

    def get_latest(
        self, asset: AssetSymbol, quote: QuoteSymbol, _asset_id: AssetId = AssetId("")
    ) -> Optional[Decimal]:
        json_resp = self.get_json(f"https://api.bitty.tax/v1/latest?base={asset}&symbols={quote}")
        return (
            Decimal(repr(json_resp["rates"][quote]))
            if "rates" in json_resp and quote in json_resp["rates"]
            else None
        )

    def get_historical(
        self,
        asset: AssetSymbol,
        quote: QuoteSymbol,
        timestamp: Timestamp,
        _asset_id: AssetId = AssetId(""),
    ) -> None:
        url = f"https://api.bitty.tax/v1/{timestamp:%Y-%m-%d}?base={asset}&symbols={quote}"
        json_resp = self.get_json(url)
        pair = self.pair(asset, quote)
        # Date returned in response might not be date requested due to weekends/holidays
        self.update_prices(
            pair,
            {
                Date(timestamp.date()): {
                    "price": (
                        Decimal(repr(json_resp["rates"][quote]))
                        if "rates" in json_resp and quote in json_resp["rates"]
                        else None
                    ),
                    "url": SourceUrl(url),
                }
            },
            timestamp,
        )


class Frankfurter(DataSourceBase):
    def __init__(self) -> None:
        super().__init__()
        currencies = [
            "EUR",
            "USD",
            "JPY",
            "BGN",
            "CYP",
            "CZK",
            "DKK",
            "EEK",
            "GBP",
            "HUF",
            "LTL",
            "LVL",
            "MTL",
            "PLN",
            "ROL",
            "RON",
            "SEK",
            "SIT",
            "SKK",
            "CHF",
            "ISK",
            "NOK",
            "HRK",
            "RUB",
            "TRL",
            "TRY",
            "AUD",
            "BRL",
            "CAD",
            "CNY",
            "HKD",
            "IDR",
            "ILS",
            "INR",
            "KRW",
            "MXN",
            "MYR",
            "NZD",
            "PHP",
            "SGD",
            "THB",
            "ZAR",
        ]
        self.assets = {
            AssetSymbol(c): {"asset_id": AssetId(""), "name": AssetName("Fiat " + c)}
            for c in currencies
        }

    def get_latest(
        self, asset: AssetSymbol, quote: QuoteSymbol, _asset_id: AssetId = AssetId("")
    ) -> Optional[Decimal]:
        json_resp = self.get_json(f"https://api.frankfurter.app/latest?from={asset}&to={quote}")
        return (
            Decimal(repr(json_resp["rates"][quote]))
            if "rates" in json_resp and quote in json_resp["rates"]
            else None
        )

    def get_historical(
        self,
        asset: AssetSymbol,
        quote: QuoteSymbol,
        timestamp: Timestamp,
        _asset_id: AssetId = AssetId(""),
    ) -> None:
        url = f"https://api.frankfurter.app/{timestamp:%Y-%m-%d}?from={asset}&to={quote}"
        json_resp = self.get_json(url)
        pair = self.pair(asset, quote)
        # Date returned in response might not be date requested due to weekends/holidays
        self.update_prices(
            pair,
            {
                Date(timestamp.date()): {
                    "price": (
                        Decimal(repr(json_resp["rates"][quote]))
                        if "rates" in json_resp and quote in json_resp["rates"]
                        else None
                    ),
                    "url": SourceUrl(url),
                }
            },
            timestamp,
        )


class CoinDesk(DataSourceBase):
    def __init__(self) -> None:
        super().__init__()
        self.assets = {AssetSymbol("BTC"): {"asset_id": AssetId(""), "name": AssetName("Bitcoin")}}

    def get_latest(
        self, _asset: AssetSymbol, quote: QuoteSymbol, _asset_id: AssetId = AssetId("")
    ) -> Optional[Decimal]:
        json_resp = self.get_json("https://api.coindesk.com/v1/bpi/currentprice.json")
        return (
            Decimal(repr(json_resp["bpi"][quote]["rate_float"]))
            if "bpi" in json_resp and quote in json_resp["bpi"]
            else None
        )

    def get_historical(
        self,
        asset: AssetSymbol,
        quote: QuoteSymbol,
        timestamp: Timestamp,
        _asset_id: AssetId = AssetId(""),
    ) -> None:
        url = (
            f"https://api.coindesk.com/v1/bpi/historical/close.json"
            f"?start={timestamp:%Y-%m-%d}&end={datetime.now():%Y-%m-%d}&currency={quote}"
        )
        json_resp = self.get_json(url)
        pair = self.pair(asset, quote)
        if "bpi" in json_resp:
            self.update_prices(
                pair,
                {
                    self.str_to_date(k): {
                        "price": Decimal(repr(v)) if v else None,
                        "url": SourceUrl(url),
                    }
                    for k, v in json_resp["bpi"].items()
                },
                timestamp,
            )


class CryptoCompare(DataSourceBase):
    MAX_DAYS = 2000

    def __init__(self) -> None:
        super().__init__()

        if "cryptocompare_api_key" in config.config:
            self.headers["authorization"] = f"Apikey {config.cryptocompare_api_key}"

        self.api_root = "https://min-api.cryptocompare.com"

        json_resp = self.get_json(f"{self.api_root}/data/all/coinlist")
        if json_resp["Response"] != "Success":
            raise RuntimeError(f"CryptoCompare API failure: {json_resp.get('Message', '')}")

        self.assets = {
            c[1]["Symbol"]
            .strip()
            .upper(): {"asset_id": AssetId(""), "name": c[1]["CoinName"].strip()}
            for c in json_resp["Data"].items()
        }
        # CryptoCompare symbols are unique, so no ID required

    def get_latest(
        self, asset: AssetSymbol, quote: QuoteSymbol, _asset_id: AssetId = AssetId("")
    ) -> Optional[Decimal]:
        json_resp = self.get_json(
            f"{self.api_root}/data/price?extraParams={self.USER_AGENT}&fsym={asset}&tsyms={quote}"
        )
        return Decimal(repr(json_resp[quote])) if quote in json_resp else None

    def get_historical(
        self,
        asset: AssetSymbol,
        quote: QuoteSymbol,
        timestamp: Timestamp,
        _asset_id: AssetId = AssetId(""),
    ) -> None:
        url = (
            f"{self.api_root}/data/histoday?aggregate=1"
            f"&extraParams={self.USER_AGENT}&fsym={asset}&tsym={quote}"
            f"&limit={self.MAX_DAYS}"
            f"&toTs={self.epoch_time(Timestamp(timestamp + timedelta(days=self.MAX_DAYS)))}"
        )

        json_resp = self.get_json(url)
        # Type=2 - CCCAGG market does not exist for this coin pair
        if json_resp["Response"] != "Success" and json_resp["Type"] != 2:
            raise RuntimeError(f"CryptoCompare API failure: {json_resp.get('Message', '')}")

        pair = self.pair(asset, quote)
        # Warning - CryptoCompare returns 0 as data for missing dates, convert these to None.
        if "Data" in json_resp:
            self.update_prices(
                pair,
                {
                    Date(datetime.fromtimestamp(d["time"]).date()): {
                        "price": Decimal(repr(d["close"])) if "close" in d and d["close"] else None,
                        "url": SourceUrl(url),
                    }
                    for d in json_resp["Data"]
                },
                timestamp,
            )


class CoinGecko(DataSourceBase):
    def __init__(self) -> None:
        super().__init__()

        if "coingecko_pro_api_key" in config.config:
            self.headers["x-cg-pro-api-key"] = f"{config.coingecko_pro_api_key}"
            self.api_root = "https://pro-api.coingecko.com/api/v3"
        elif "coingecko_demo_api_key" in config.config:
            self.headers["x-cg-demo-api-key"] = config.coingecko_demo_api_key
            self.api_root = "https://api.coingecko.com/api/v3"
        else:
            self.api_root = "https://api.coingecko.com/api/v3"

        json_resp = self.get_json(f"{self.api_root}/coins/list")
        self.ids = {
            c["id"]: {"symbol": c["symbol"].strip().upper(), "name": c["name"].strip()}
            for c in json_resp
        }
        self.assets = {
            c["symbol"].strip().upper(): {"asset_id": c["id"], "name": c["name"].strip()}
            for c in json_resp
        }
        self.get_config_assets()

    def get_latest(
        self, asset: AssetSymbol, quote: QuoteSymbol, asset_id: AssetId = AssetId("")
    ) -> Optional[Decimal]:
        if not asset_id:
            asset_id = self.assets[asset]["asset_id"]

        json_resp = self.get_json(
            f"{self.api_root}/coins/{asset_id}"
            f"?localization=false&community_data=false&developer_data=false"
        )
        return (
            Decimal(repr(json_resp["market_data"]["current_price"][quote.lower()]))
            if "market_data" in json_resp
            and "current_price" in json_resp["market_data"]
            and quote.lower() in json_resp["market_data"]["current_price"]
            else None
        )

    def get_historical(
        self,
        asset: AssetSymbol,
        quote: QuoteSymbol,
        timestamp: Timestamp,
        asset_id: AssetId = AssetId(""),
    ) -> None:
        if not asset_id:
            asset_id = self.assets[asset]["asset_id"]

        url = f"{self.api_root}/coins/{asset_id}/market_chart?vs_currency={quote}&days=max"
        json_resp = self.get_json(url)
        pair = self.pair(asset, quote)
        if "prices" in json_resp:
            self.update_prices(
                pair,
                {
                    Date(datetime.utcfromtimestamp(p[0] / 1000).date()): {
                        "price": Decimal(repr(p[1])) if p[1] else None,
                        "url": SourceUrl(url),
                    }
                    for p in json_resp["prices"]
                },
                timestamp,
            )


class CoinPaprika(DataSourceBase):
    MAX_DAYS = 5000

    def __init__(self) -> None:
        super().__init__()

        if "coinpaprika_api_key" in config.config:
            self.headers["Authorization"] = f"{config.coinpaprika_api_key}"
            self.api_root = "https://api-pro.coinpaprika.com/v1"
        else:
            self.api_root = "https://api.coinpaprika.com/v1"

        json_resp = self.get_json(f"{self.api_root}/coins")
        self.ids = {
            c["id"]: {"symbol": c["symbol"].strip().upper(), "name": c["name"].strip()}
            for c in json_resp
        }
        self.assets = {
            c["symbol"].strip().upper(): {"asset_id": c["id"], "name": c["name"].strip()}
            for c in json_resp
        }
        self.get_config_assets()

    def get_latest(
        self, asset: AssetSymbol, quote: QuoteSymbol, asset_id: AssetId = AssetId("")
    ) -> Optional[Decimal]:
        if not asset_id:
            asset_id = self.assets[asset]["asset_id"]

        json_resp = self.get_json(f"{self.api_root}/tickers/{asset_id}?quotes={quote}")
        return (
            Decimal(repr(json_resp["quotes"][quote]["price"]))
            if "quotes" in json_resp and quote in json_resp["quotes"]
            else None
        )

    def get_historical(
        self,
        asset: AssetSymbol,
        quote: QuoteSymbol,
        timestamp: Timestamp,
        asset_id: AssetId = AssetId(""),
    ) -> None:
        # Historic prices only available in USD or BTC
        if quote not in ("USD", "BTC"):
            return

        if not asset_id:
            asset_id = self.assets[asset]["asset_id"]

        url = (
            f"{self.api_root}/tickers/{asset_id}/historical"
            f"?start={timestamp:%Y-%m-%d}&limit={self.MAX_DAYS}&quote={quote}&interval=1d"
        )

        json_resp = self.get_json(url)
        pair = self.pair(asset, quote)
        self.update_prices(
            pair,
            {
                Date(timestamp.date()): {
                    "price": Decimal(repr(p["price"])) if p["price"] else None,
                    "url": SourceUrl(url),
                }
                for p in json_resp
            },
            timestamp,
        )
