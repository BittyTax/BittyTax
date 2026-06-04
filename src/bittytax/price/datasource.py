# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import atexit
import json
import os
import platform
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from colorama import Fore
from tqdm import tqdm
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
from ..utils import disable_tqdm
from ..version import __version__
from .exceptions import DataSourceApiError, UnexpectedDataSourceAssetIdError


class DsSymbolToAssetData(TypedDict):  # pylint: disable=too-few-public-methods
    asset_id: AssetId
    name: AssetName


class DsIdToAssetData(TypedDict):  # pylint: disable=too-few-public-methods
    symbol: AssetSymbol
    name: AssetName


class DsPriceData(TypedDict):  # pylint: disable=too-few-public-methods
    price: Optional[Decimal]
    url: SourceUrl


class _CoinGeckoIdData(TypedDict):
    symbol: AssetSymbol
    name: AssetName
    market_cap: Decimal


class _CoinPaprikaIdData(TypedDict):
    symbol: AssetSymbol
    name: AssetName
    rank: int


class DataSourceBase:
    USER_AGENT = (
        f"BittyTax/{__version__} Python/{platform.python_version()} "
        f"{platform.system()}/{platform.release()}"
    )

    TIME_OUT = 30
    RATE_LIMIT = 5  # requests per second
    RETRIES = 3
    BACKOFF_FACTOR = 1  # seconds
    RETRY_AFTER_DEFAULT = 5  # seconds
    IDS_TTL = timedelta(days=1)

    HISTORICAL_QUOTES: Set[str] = set()
    LATEST_QUOTES: Set[str] = set()

    def __init__(self, no_cache: bool = False, progress_bar: Optional[tqdm] = None) -> None:
        self.no_cache = no_cache
        self.headers = {"User-Agent": self.USER_AGENT}
        self.assets: Dict[AssetSymbol, DsSymbolToAssetData] = {}
        self.ids: Dict[AssetId, DsIdToAssetData] = {}
        self.progress_bar: Optional[tqdm] = progress_bar
        self.prices, self._prices_dirty = self._load_prices()

        self.api_lock = threading.Lock()
        self._thread_local = threading.local()
        self.last_request_time = float(0)

        for pair in sorted(self.prices):
            if config.debug:
                print(f"{Fore.YELLOW}price: {self.name()} ({pair}) data cache loaded")

        atexit.register(self._save_prices)

    def name(self) -> DataSourceName:
        return DataSourceName(self.__class__.__name__)

    def _get_session(self) -> requests.Session:
        if not hasattr(self._thread_local, "session"):
            self._thread_local.session = requests.Session()
        return self._thread_local.session

    def _set_tqdm_postfix(self, message: str) -> None:
        if self.progress_bar is None:
            return

        self.progress_bar.set_postfix_str(message)

    def _countdown_sleep(self, label: str, wait_time: float) -> None:
        if self.progress_bar is not None:
            remaining = wait_time
            while remaining > 0:
                self._set_tqdm_postfix(f"{label} {remaining:.0f}s")
                sleep_for = min(1.0, remaining)
                time.sleep(sleep_for)
                remaining -= sleep_for
            self._set_tqdm_postfix("")
        else:
            with tqdm(
                total=int(wait_time),
                desc=f"{Fore.CYAN}{label}{Fore.GREEN}",
                unit="s",
                leave=False,
                disable=disable_tqdm(),
            ) as pbar:
                remaining = float(wait_time)
                while remaining > 0:
                    sleep_for = min(1.0, remaining)
                    time.sleep(sleep_for)
                    pbar.update(1)
                    remaining -= sleep_for

    def _rate_limit(self) -> None:
        elapsed_time = time.time() - self.last_request_time
        wait_time = (1 / self.RATE_LIMIT) - elapsed_time + 0.05

        if wait_time > 0:
            if config.debug:
                print(f"{Fore.YELLOW}price: {self.name()} rate-limit, wait: {wait_time:.2f}s")
                time.sleep(wait_time)

        self.last_request_time = time.time()

    def _retry(self, attempt: int, retry_after: Optional[int] = None) -> bool:
        if attempt < self.RETRIES:
            if retry_after:
                wait_time = retry_after
            else:
                wait_time = self.BACKOFF_FACTOR * (2**attempt)

            if config.debug:
                print(f"{Fore.YELLOW}price: {self.name()} back-off, wait: {wait_time:.0f}s")

            self._countdown_sleep(f"{self.name()} back-off", wait_time)
            return True
        return False

    def _check_rate_limit_in_response(self, _json_resp: Any) -> Tuple[bool, Optional[int]]:
        """
        Check if response contains data source-specific rate limit indicator.
        Override in sub-classes to implement custom rate limit detection.

        Args:
            json_resp: The parsed JSON response

        Returns:
            Tuple of (rate_limited, retry_after_seconds) where retry_after_seconds is None
            if no specific duration is provided by the API.
        """
        return False, None

    def get_json(self, url: str) -> Any:
        with self.api_lock:
            session = self._get_session()

            for attempt in range(1 + self.RETRIES):
                self._rate_limit()

                try:
                    if config.debug:
                        retry_msg = f"(retry {attempt}/{self.RETRIES}) " if attempt > 0 else ""
                        print(
                            (
                                f"{Fore.YELLOW}price: {datetime.now():%H:%M:%S.%f} GET "
                                f"{retry_msg}{url} {list(self.headers.keys())}"
                            )
                        )

                    response = session.get(url, headers=self.headers, timeout=self.TIME_OUT)

                    if response.status_code in [
                        HTTPStatus.UNAUTHORIZED,
                        HTTPStatus.PAYMENT_REQUIRED,
                        HTTPStatus.FORBIDDEN,
                        HTTPStatus.TOO_MANY_REQUESTS,
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        HTTPStatus.BAD_GATEWAY,
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        HTTPStatus.GATEWAY_TIMEOUT,
                    ]:
                        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                            # Handle rate limit
                            retry_after: Optional[int] = self.RETRY_AFTER_DEFAULT
                            if "retry-after" in response.headers:
                                retry_after = int(response.headers["retry-after"])

                            if not self._retry(attempt, retry_after):
                                raise DataSourceApiError(
                                    self.name(),
                                    url,
                                    f"HTTP {response.status_code} {response.reason}",
                                )
                            continue

                        if not self._retry(attempt):
                            reason = f"HTTP {response.status_code} {response.reason}"
                            try:
                                error_detail = response.json()
                                reason += f": {error_detail}"
                            except requests.exceptions.JSONDecodeError:
                                pass
                            raise DataSourceApiError(self.name(), url, reason)
                        continue

                    if response:
                        json_resp = response.json()

                        rate_limited, retry_after = self._check_rate_limit_in_response(json_resp)
                        if rate_limited:
                            if config.debug:
                                print(
                                    f"{Fore.YELLOW}price: {self.name()} "
                                    f"rate limit detected in response"
                                )
                            if not self._retry(attempt, retry_after):
                                raise DataSourceApiError(self.name(), url, "rate limit exceeded")
                            continue

                        return json_resp
                    return {}

                except requests.exceptions.JSONDecodeError as e:
                    if config.debug:
                        print(f"{self.name()} JSON decode error: {url}")
                    if not self._retry(attempt):
                        raise DataSourceApiError(self.name(), url, str(e)) from e

                except (
                    requests.exceptions.ConnectionError,
                    requests.RequestException,
                    requests.exceptions.Timeout,
                ) as e:
                    if config.debug:
                        print(f"{self.name()} request failed: {url} - {e}")
                    if not self._retry(attempt):
                        raise DataSourceApiError(self.name(), url, str(e)) from e

        # If all retries exhausted
        raise DataSourceApiError(self.name(), url, "all retries exhausted")

    def update_prices(
        self,
        pair: TradingPair,
        asset_id: AssetId,
        prices: Dict[Date, DsPriceData],
        timestamp: Timestamp,
    ) -> None:
        if pair not in self.prices:
            self.prices[pair] = {}
        if asset_id not in self.prices[pair]:
            self.prices[pair][asset_id] = {}

        # We are not interested in today's latest price, only the days closing price, also need to
        #  filter any erroneous future dates returned
        prices = {k: v for k, v in prices.items() if k < datetime.now().date()}

        # We might not receive data for the date requested, if so set to None to prevent repeat
        #  lookups, assuming date is in the past
        date = Date(timestamp.date())
        if date not in prices and date < datetime.now().date():
            prices[date] = {"price": None, "url": SourceUrl("")}

        self.prices[pair][asset_id].update(prices)
        self._prices_dirty = True

    def _load_prices(
        self,
    ) -> Tuple[Dict[TradingPair, Dict[AssetId, Dict[Date, DsPriceData]]], bool]:
        filename = os.path.join(CACHE_DIR, self.name() + ".json")
        if not os.path.exists(filename):
            return {}, False

        try:
            with open(filename, "r", encoding="utf-8") as price_cache:
                json_prices = json.load(price_cache)
            prices: Dict[TradingPair, Dict[AssetId, Dict[Date, DsPriceData]]] = {}
            dirty = False
            for pair, pair_data in json_prices.items():
                if pair_data and self._is_date_key(next(iter(pair_data))):
                    # Legacy format
                    dirty = True
                    prices[TradingPair(pair)] = {
                        AssetId(""): {
                            self.str_to_date(date): {
                                "price": self.str_to_decimal(price_data["price"]),
                                "url": price_data["url"],
                            }
                            for date, price_data in pair_data.items()
                        }
                    }
                else:
                    # New format
                    prices[TradingPair(pair)] = {}
                    for asset_id, asset_entry in pair_data.items():
                        aid = AssetId(asset_id)
                        prices[TradingPair(pair)][aid] = {
                            self.str_to_date(date): {
                                "price": self.str_to_decimal(price_data["price"]),
                                "url": price_data["url"],
                            }
                            for date, price_data in asset_entry.get("prices", {}).items()
                        }
            return prices, dirty
        except (IOError, ValueError):
            tqdm.write(f"{WARNING} Data cached for {self.name()} could not be loaded")
            return {}, True

    def _save_prices(self) -> None:
        if not self._prices_dirty:
            return
        with open(
            os.path.join(CACHE_DIR, self.name() + ".json"), "w", encoding="utf-8"
        ) as price_cache:
            json_prices: Dict[str, Any] = {}
            for pair, asset_id_dict in self.prices.items():
                symbol = AssetSymbol(pair.split("/")[0])
                json_prices[pair] = {}
                for asset_id, date_dict in asset_id_dict.items():
                    if not asset_id and symbol in self.assets:
                        # Promote old flat-format data to current asset_id
                        asset_id = self.assets[symbol]["asset_id"]
                    if asset_id:
                        name = self.ids[asset_id]["name"] if asset_id in self.ids else ""
                    else:
                        name = self.assets[symbol]["name"] if symbol in self.assets else ""
                    json_prices[pair][asset_id] = {
                        "name": name,
                        "prices": {
                            f"{date:%Y-%m-%d}": {
                                "price": self.decimal_to_str(price["price"]),
                                "url": price["url"],
                            }
                            for date, price in date_dict.items()
                        },
                    }
            json.dump(json_prices, price_cache, indent=4, sort_keys=True)

    def _load_ids(self) -> Optional[Dict[AssetId, DsIdToAssetData]]:
        if self.no_cache:
            return None
        filename = os.path.join(CACHE_DIR, self.name() + "_ids.json")
        if not os.path.exists(filename):
            return None
        try:
            with open(filename, "r", encoding="utf-8") as ids_cache:
                json_ids = json.load(ids_cache)
                timestamp = datetime.fromisoformat(json_ids["timestamp"])
                if datetime.now() - timestamp > self.IDS_TTL:
                    if config.debug:
                        print(f"{Fore.YELLOW}price: {self.name()} ids cache expired")
                    return None
                if config.debug:
                    print(f"{Fore.YELLOW}price: {self.name()} ids cache loaded")
                return {
                    AssetId(k): DsIdToAssetData(
                        symbol=AssetSymbol(v["symbol"]), name=AssetName(v["name"])
                    )
                    for k, v in json_ids["ids"].items()
                }
        except (IOError, ValueError, KeyError):
            return None

    def _save_ids(self) -> None:
        filename = os.path.join(CACHE_DIR, self.name() + "_ids.json")
        try:
            with open(filename, "w", encoding="utf-8") as ids_cache:
                json.dump(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "ids": {
                            k: {"symbol": v["symbol"], "name": v["name"]}
                            for k, v in self.ids.items()
                        },
                    },
                    ids_cache,
                    indent=4,
                )
        except IOError:
            pass

    def _load_assets(self) -> Optional[Dict[AssetSymbol, DsSymbolToAssetData]]:
        if self.no_cache:
            return None
        filename = os.path.join(CACHE_DIR, self.name() + "_assets.json")
        if not os.path.exists(filename):
            return None
        try:
            with open(filename, "r", encoding="utf-8") as assets_cache:
                json_assets = json.load(assets_cache)
                timestamp = datetime.fromisoformat(json_assets["timestamp"])
                if datetime.now() - timestamp > self.IDS_TTL:
                    if config.debug:
                        print(f"{Fore.YELLOW}price: {self.name()} assets cache expired")
                    return None
                if config.debug:
                    print(f"{Fore.YELLOW}price: {self.name()} assets cache loaded")
                return {
                    AssetSymbol(k): {"asset_id": AssetId(""), "name": AssetName(v)}
                    for k, v in json_assets["assets"].items()
                }
        except (IOError, ValueError, KeyError):
            return None

    def _save_assets(self) -> None:
        filename = os.path.join(CACHE_DIR, self.name() + "_assets.json")
        try:
            with open(filename, "w", encoding="utf-8") as assets_cache:
                json.dump(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "assets": {k: v["name"] for k, v in self.assets.items()},
                    },
                    assets_cache,
                    indent=4,
                )
        except IOError:
            pass

    def get_config_assets(self) -> None:
        for symbol in config.data_source_select:
            for ds_select in config.data_source_select[symbol]:
                if ds_select.upper().startswith(self.name().upper() + ":"):  # pylint: disable=E1101
                    self._add_asset(symbol, ds_select)

    def _add_asset(self, symbol: AssetSymbol, ds_select: str) -> None:
        asset_id = AssetId(ds_select.split(":")[1])
        if asset_id in self.ids:
            self.assets[symbol] = {"asset_id": asset_id, "name": self.ids[asset_id]["name"]}

            if config.debug:
                print(
                    f"{Fore.YELLOW}price: "
                    f"{symbol} added as {self.name()} [ID:{asset_id}] "
                    f'({self.ids[asset_id]["name"]})'
                )
        else:
            raise UnexpectedDataSourceAssetIdError(ds_select, symbol)

    def get_list(self) -> Dict[AssetSymbol, List[DsSymbolToAssetData]]:
        asset_list = {k: [v] for k, v in self.assets.items()}

        if self.ids:
            for k, v in self.ids.items():
                asset_data = DsSymbolToAssetData({"asset_id": k, "name": v["name"]})
                if asset_data not in asset_list[v["symbol"]]:
                    asset_list[v["symbol"]].append(asset_data)

        return asset_list

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
        return Date(datetime.fromisoformat(date).date())

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
    def epoch_time(timestamp: datetime) -> int:
        return int(timestamp.timestamp())

    @staticmethod
    def _is_date_key(key: str) -> bool:
        # Quick check for ISO date format YYYY-MM-DD
        return len(key) == 10 and key[4] == "-" and key[7] == "-"


class BittyTaxAPI(DataSourceBase):
    HISTORICAL_QUOTES = {
        "AUD",
        "BRL",
        "CAD",
        "CHF",
        "CNY",
        "CZK",
        "DKK",
        "EUR",
        "GBP",
        "HKD",
        "HUF",
        "IDR",
        "ILS",
        "INR",
        "ISK",
        "JPY",
        "KRW",
        "MXN",
        "MYR",
        "NOK",
        "NZD",
        "PHP",
        "PLN",
        "RON",
        "SEK",
        "SGD",
        "THB",
        "TRY",
        "USD",
        "ZAR",
    }
    LATEST_QUOTES = HISTORICAL_QUOTES

    def __init__(self, no_cache: bool = False, progress_bar: Optional[tqdm] = None) -> None:
        super().__init__(no_cache, progress_bar)
        cached_assets = self._load_assets()
        if cached_assets is not None:
            self.assets = cached_assets
        else:
            json_resp = self.get_json("https://api.bitty.tax/v1/symbols")
            self.assets = {
                k: {"asset_id": AssetId(""), "name": v} for k, v in json_resp["symbols"].items()
            }
            self._save_assets()

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
            AssetId(""),
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
    HISTORICAL_QUOTES = {
        "AUD",
        "BRL",
        "CAD",
        "CHF",
        "CNY",
        "CZK",
        "DKK",
        "EUR",
        "GBP",
        "HKD",
        "HUF",
        "IDR",
        "ILS",
        "INR",
        "ISK",
        "JPY",
        "KRW",
        "MXN",
        "MYR",
        "NOK",
        "NZD",
        "PHP",
        "PLN",
        "RON",
        "SEK",
        "SGD",
        "THB",
        "TRY",
        "USD",
        "ZAR",
    }
    LATEST_QUOTES = HISTORICAL_QUOTES

    def __init__(self, no_cache: bool = False, progress_bar: Optional[tqdm] = None) -> None:
        super().__init__(no_cache, progress_bar)
        cached_assets = self._load_assets()
        if cached_assets is not None:
            self.assets = cached_assets
        else:
            json_resp = self.get_json("https://api.frankfurter.dev/v1/currencies")
            self.assets = {
                AssetSymbol(k): {"asset_id": AssetId(""), "name": AssetName(v)}
                for k, v in json_resp.items()
            }
            self._save_assets()

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
            AssetId(""),
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
    HISTORICAL_QUOTES = {"USD", "GBP", "EUR"}

    def __init__(self, no_cache: bool = False, progress_bar: Optional[tqdm] = None) -> None:
        super().__init__(no_cache, progress_bar)
        self.assets = {AssetSymbol("BTC"): {"asset_id": AssetId(""), "name": AssetName("Bitcoin")}}

    def get_latest(
        self, _asset: AssetSymbol, _quote: QuoteSymbol, _asset_id: AssetId = AssetId("")
    ) -> Optional[Decimal]:
        # Deprecated
        return None

    def get_historical(
        self,
        _asset: AssetSymbol,
        _quote: QuoteSymbol,
        _timestamp: Timestamp,
        _asset_id: AssetId = AssetId(""),
    ) -> None:
        # Deprecated
        return None


class CryptoCompare(DataSourceBase):
    ERROR_TYPE_MARKET_NOT_EXIST = 2
    ERROR_TYPE_RATE_LIMIT = 99
    MAX_DAYS = 2000

    HISTORICAL_QUOTES = {
        "ARS",
        "AUD",
        "BOB",
        "BRL",
        "BTC",
        "CAD",
        "CHF",
        "CLP",
        "CNY",
        "COP",
        "CZK",
        "DKK",
        "EUR",
        "GBP",
        "HKD",
        "HUF",
        "IDR",
        "ILS",
        "INR",
        "ISK",
        "JPY",
        "KRW",
        "MXN",
        "MYR",
        "NGN",
        "NOK",
        "NZD",
        "PEN",
        "PHP",
        "PKR",
        "PLN",
        "RUB",
        "SEK",
        "SGD",
        "THB",
        "TRY",
        "TWD",
        "UAH",
        "USD",
        "VND",
        "ZAR",
    }
    LATEST_QUOTES = HISTORICAL_QUOTES

    def __init__(self, no_cache: bool = False, progress_bar: Optional[tqdm] = None) -> None:
        super().__init__(no_cache, progress_bar)

        if "cryptocompare_api_key" in config.config:
            CryptoCompare.RATE_LIMIT = 20
            self.headers["authorization"] = f"Apikey {config.cryptocompare_api_key}"
        else:
            CryptoCompare.RATE_LIMIT = 2

        self.api_root = "https://min-api.cryptocompare.com"

        cached_ids = self._load_ids()
        if cached_ids is not None:
            self.ids = cached_ids
        else:
            url = f"{self.api_root}/data/all/coinlist"
            json_resp = self.get_json(url)
            if json_resp["Response"] != "Success":
                raise DataSourceApiError(
                    self.name(),
                    url,
                    f"unexpected response: {json_resp}",
                )

            # CryptoCompare symbols are unique, so can be used as the ID
            self.ids = {
                c[1]["Symbol"]
                .strip()
                .lower(): {
                    "symbol": c[1]["Symbol"].strip().upper(),
                    "name": c[1]["CoinName"].strip(),
                }
                for c in json_resp["Data"].items()
            }
            self._save_ids()

        for k, v in self.ids.items():
            self.assets[v["symbol"]] = {"asset_id": k, "name": v["name"]}
        self.get_config_assets()

    def _check_rate_limit_in_response(self, json_resp: Any) -> Tuple[bool, Optional[int]]:
        """
        CryptoCompare returns rate limit in response body with 200 OK status.
        Check for unsuccessful response with rate limit error.
        Note: no "retry-after" is provided in headers or response, use default back-off time for
        retries.
        """
        if isinstance(json_resp, dict):
            if (
                "Response" in json_resp
                and "Type" in json_resp
                and json_resp["Response"] != "Success"
                and json_resp["Type"] == self.ERROR_TYPE_RATE_LIMIT
            ):
                if config.debug:
                    message = json_resp.get("Message")
                    print(f"{Fore.YELLOW}price: CryptoCompare rate limit: {message}")
                return True, None
        return False, None

    def get_latest(
        self, asset: AssetSymbol, quote: QuoteSymbol, asset_id: AssetId = AssetId("")
    ) -> Optional[Decimal]:
        if not asset_id:
            asset_id = self.assets[asset]["asset_id"]

        json_resp = self.get_json(
            f"{self.api_root}/data/price?extraParams={self.USER_AGENT}"
            f"&fsym={asset_id}&tsyms={quote}"
        )
        return Decimal(repr(json_resp[quote])) if quote in json_resp else None

    def get_historical(
        self,
        asset: AssetSymbol,
        quote: QuoteSymbol,
        timestamp: Timestamp,
        asset_id: AssetId = AssetId(""),
    ) -> None:
        if not asset_id:
            asset_id = self.assets[asset]["asset_id"]

        url = (
            f"{self.api_root}/data/histoday?aggregate=1"
            f"&extraParams={self.USER_AGENT}&fsym={asset_id}&tsym={quote}"
            f"&limit={self.MAX_DAYS}"
            f"&toTs={self.epoch_time(Timestamp(timestamp + timedelta(days=self.MAX_DAYS)))}"
        )
        json_resp = self.get_json(url)
        if (
            json_resp["Response"] != "Success"
            and json_resp["Type"] != self.ERROR_TYPE_MARKET_NOT_EXIST
        ):
            raise DataSourceApiError(
                self.name(),
                url,
                f"unexpected response: {json_resp}",
            )

        pair = self.pair(asset, quote)
        # Warning - CryptoCompare returns 0 as data for missing dates, convert these to None.
        if "Data" in json_resp:
            self.update_prices(
                pair,
                asset_id,
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
    PRO_KEY = "x-cg-pro-api-key"
    DEMO_KEY = "x-cg-demo-api-key"

    HISTORICAL_QUOTES = {
        "AED",
        "ARS",
        "AUD",
        "BDT",
        "BHD",
        "BMD",
        "BRL",
        "BTC",
        "CAD",
        "CHF",
        "CLP",
        "CNY",
        "CZK",
        "DKK",
        "EUR",
        "GBP",
        "GEL",
        "HKD",
        "HUF",
        "IDR",
        "ILS",
        "INR",
        "JPY",
        "KRW",
        "KWD",
        "LKR",
        "MMK",
        "MXN",
        "MYR",
        "NGN",
        "NOK",
        "NZD",
        "PHP",
        "PKR",
        "PLN",
        "RUB",
        "SAR",
        "SEK",
        "SGD",
        "THB",
        "TRY",
        "TWD",
        "UAH",
        "USD",
        "VEF",
        "VND",
        "XDR",
        "ZAR",
    }
    LATEST_QUOTES = HISTORICAL_QUOTES

    def __init__(self, no_cache: bool = False, progress_bar: Optional[tqdm] = None) -> None:
        super().__init__(no_cache, progress_bar)

        if "coingecko_pro_api_key" in config.config:
            CoinGecko.RATE_LIMIT = 20
            self.headers[self.PRO_KEY] = f"{config.coingecko_pro_api_key}"
            self.api_root = "https://pro-api.coingecko.com/api/v3"
        elif "coingecko_demo_api_key" in config.config:
            CoinGecko.RATE_LIMIT = 2
            self.headers[self.DEMO_KEY] = config.coingecko_demo_api_key
            self.api_root = "https://api.coingecko.com/api/v3"
        else:
            CoinGecko.RATE_LIMIT = 2
            self.api_root = "https://api.coingecko.com/api/v3"

        cached_ids = self._load_ids()
        if cached_ids is not None:
            self.ids = cached_ids
        else:
            json_resp = self.get_json(f"{self.api_root}/coins/list?status=active")

            ids: Dict[AssetId, _CoinGeckoIdData] = {}
            for c in json_resp:
                symbol = AssetSymbol(c["symbol"].strip().upper())
                asset_id = AssetId(c["id"])
                name = AssetName(c["name"].strip())
                ids[asset_id] = {"symbol": symbol, "name": name, "market_cap": Decimal(0)}

            if self.PRO_KEY in self.headers:
                json_resp = self.get_json(f"{self.api_root}/coins/list?status=inactive")
                for c in json_resp:
                    symbol = AssetSymbol(c["symbol"].strip().upper())
                    asset_id = AssetId(c["id"])
                    name = AssetName(c["name"].strip())
                    ids[asset_id] = {"symbol": symbol, "name": name, "market_cap": Decimal(0)}

            # Get market cap of top 250 tokens only
            json_resp = self.get_json(
                f"{self.api_root}/coins/markets?vs_currency=USD&per_page=250&order=market_cap_dsc"
            )
            for c in json_resp:
                if c["id"] in ids:
                    ids[AssetId(c["id"])]["market_cap"] = (
                        Decimal(c["market_cap"]) if c.get("market_cap") else Decimal(0)
                    )

            self.ids = {
                k: DsIdToAssetData(symbol=v["symbol"], name=v["name"])
                for k, v in sorted(
                    ids.items(),
                    key=lambda k_v: k_v[1]["market_cap"],
                    reverse=True,
                )
            }
            self._save_ids()

        for k, v in self.ids.items():
            if v["symbol"] not in self.assets:
                self.assets[v["symbol"]] = {"asset_id": k, "name": v["name"]}

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

        # Public API is limited to 365 days of historical price data
        if self.PRO_KEY not in self.headers:
            days_ago = (datetime.now().date() - timestamp.date()).days
            if days_ago > 365:
                if config.debug:
                    print(
                        f"{Fore.YELLOW}price: {self.name()} "
                        f"skipping historical lookup for {timestamp:%Y-%m-%d} "
                        f"({days_ago} days ago) - requires Pro API for data older than 365 days"
                    )
                return
            days = "365"
        else:
            days = "max"

        url = f"{self.api_root}/coins/{asset_id}/market_chart?vs_currency={quote}&days={days}"
        json_resp = self.get_json(url)
        pair = self.pair(asset, quote)
        if "prices" in json_resp:
            self.update_prices(
                pair,
                asset_id,
                {
                    Date(datetime.fromtimestamp(p[0] / 1000, TZ_UTC).date()): {
                        "price": Decimal(repr(p[1])) if p[1] else None,
                        "url": SourceUrl(url),
                    }
                    for p in json_resp["prices"]
                },
                timestamp,
            )


class CoinPaprika(DataSourceBase):
    MAX_DAYS = 5000

    HISTORICAL_QUOTES = {"USD", "BTC"}
    LATEST_QUOTES = {
        "ARS",
        "AUD",
        "BOB",
        "BRL",
        "BTC",
        "CAD",
        "CHF",
        "CLP",
        "CNY",
        "COP",
        "CZK",
        "DKK",
        "ETH",
        "EUR",
        "GBP",
        "HKD",
        "HUF",
        "IDR",
        "ILS",
        "INR",
        "ISK",
        "JPY",
        "KRW",
        "MXN",
        "MYR",
        "NGN",
        "NOK",
        "NZD",
        "PEN",
        "PHP",
        "PKR",
        "PLN",
        "RUB",
        "SEK",
        "SGD",
        "THB",
        "TRY",
        "TWD",
        "UAH",
        "USD",
        "VND",
        "ZAR",
    }

    def __init__(self, no_cache: bool = False, progress_bar: Optional[tqdm] = None) -> None:
        super().__init__(no_cache, progress_bar)

        if "coinpaprika_api_key" in config.config:
            CoinPaprika.RATE_LIMIT = 20
            self.headers["Authorization"] = f"{config.coinpaprika_api_key}"
            self.api_root = "https://api-pro.coinpaprika.com/v1"
        else:
            CoinPaprika.RATE_LIMIT = 2
            self.api_root = "https://api.coinpaprika.com/v1"

        cached_ids = self._load_ids()
        if cached_ids is not None:
            self.ids = cached_ids
        else:
            json_resp = self.get_json(f"{self.api_root}/coins")

            ids: Dict[AssetId, _CoinPaprikaIdData] = {}
            for c in json_resp:
                symbol = AssetSymbol(c["symbol"].strip().upper())
                asset_id = AssetId(c["id"])
                name = AssetName(c["name"].strip())
                ids[asset_id] = {
                    "symbol": symbol,
                    "name": name,
                    "rank": c.get("rank", 0),
                }

            self.ids = {
                k: DsIdToAssetData(symbol=v["symbol"], name=v["name"])
                for k, v in sorted(
                    ids.items(),
                    key=lambda k_v: k_v[1]["rank"] if k_v[1]["rank"] > 0 else float("inf"),
                )
            }
            self._save_ids()

        for k, v in self.ids.items():
            if v["symbol"] not in self.assets:
                self.assets[v["symbol"]] = {"asset_id": k, "name": v["name"]}

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
        if not asset_id:
            asset_id = self.assets[asset]["asset_id"]

        # Public API is limited to 365 days of historical price data
        if "Authorization" not in self.headers:
            days_ago = (datetime.now().date() - timestamp.date()).days
            if days_ago >= 365:
                if config.debug:
                    print(
                        f"{Fore.YELLOW}price: {self.name()} "
                        f"skipping historical lookup for {timestamp:%Y-%m-%d} "
                        f"({days_ago} days ago) - requires Pro API for data older than 365 days"
                    )
                return

        url = (
            f"{self.api_root}/tickers/{asset_id}/historical"
            f"?start={timestamp:%Y-%m-%d}&limit={self.MAX_DAYS}&quote={quote}&interval=1d"
        )

        json_resp = self.get_json(url)
        pair = self.pair(asset, quote)
        self.update_prices(
            pair,
            asset_id,
            {
                Date(datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00")).date()): {
                    "price": Decimal(repr(p["price"])) if p["price"] else None,
                    "url": SourceUrl(url),
                }
                for p in json_resp
            },
            timestamp,
        )
