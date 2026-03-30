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
from typing import Any, Dict, List, Optional, Tuple

import dateutil.parser
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
from ..constants import CACHE_DIR, WARNING
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
    RATE_LIMIT = 5  # requests per second
    RETRIES = 3
    BACKOFF_FACTOR = 1  # seconds
    RETRY_AFTER_DEFAULT = 5  # seconds

    def __init__(self) -> None:
        self.headers = {"User-Agent": self.USER_AGENT}
        self.assets: Dict[AssetSymbol, DsSymbolToAssetData] = {}
        self.ids: Dict[AssetId, DsIdToAssetData] = {}
        self.prices = self._load_prices()

        self.api_lock = threading.Lock()
        self._thread_local = threading.local()
        self.last_request_time = float(0)
        self.progress_bar: Optional[tqdm] = None

        for pair in sorted(self.prices):
            if config.debug:
                print(f"{Fore.YELLOW}price: {self.name()} ({pair}) data cache loaded")

        atexit.register(self._cache_prices)

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
        remaining = wait_time
        while remaining > 0:
            self._set_tqdm_postfix(f"{label} {remaining:.0f}s")
            sleep_for = min(1.0, remaining)
            time.sleep(sleep_for)
            remaining -= sleep_for
        self._set_tqdm_postfix("")

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
        Override in subclasses to implement custom rate limit detection.

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
                                response.raise_for_status()
                            continue

                        if not self._retry(attempt):
                            try:
                                error_json = response.json()
                                raise RuntimeError(
                                    f"{self.name()} request failed {response.status_code} "
                                    f"{response.reason} for url: {response.url}: {error_json}"
                                )
                            except requests.exceptions.JSONDecodeError as e:
                                raise RuntimeError(
                                    f"{self.name()} request failed {response.status_code} "
                                    f"{response.reason} for url: {response.url}"
                                ) from e
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
                                raise RuntimeError(f"{self.name()} rate limit exceeded")
                            continue

                        return json_resp
                    return {}

                except requests.exceptions.JSONDecodeError:
                    if config.debug:
                        print(f"{self.name()} JSON decode error: {url}")
                    if not self._retry(attempt):
                        raise

                except (
                    requests.exceptions.ConnectionError,
                    requests.RequestException,
                    requests.exceptions.Timeout,
                ) as e:
                    if config.debug:
                        print(f"{self.name()} request failed: {url} - {e}")
                    if not self._retry(attempt):
                        raise

        # If all retries exhausted
        raise RuntimeError(f"{self.name()} all retries exhausted for: {url}")

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
    def epoch_time(timestamp: datetime) -> int:
        return int(timestamp.timestamp())


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

    def __init__(self) -> None:
        super().__init__()

        if "cryptocompare_api_key" in config.config:
            CryptoCompare.RATE_LIMIT = 20
            self.headers["authorization"] = f"Apikey {config.cryptocompare_api_key}"
        else:
            CryptoCompare.RATE_LIMIT = 2

        self.api_root = "https://min-api.cryptocompare.com"

        json_resp = self.get_json(f"{self.api_root}/data/all/coinlist")
        if json_resp["Response"] != "Success":
            raise RuntimeError(f"CryptoCompare API failure: {json_resp}")

        # CryptoCompare symbols are unique, so can be used as the ID
        self.ids = {
            c[1]["Symbol"]
            .strip()
            .lower(): {"symbol": c[1]["Symbol"].strip().upper(), "name": c[1]["CoinName"].strip()}
            for c in json_resp["Data"].items()
        }
        self.assets = {
            c[1]["Symbol"]
            .strip()
            .upper(): {"asset_id": c[1]["Symbol"].strip().lower(), "name": c[1]["CoinName"].strip()}
            for c in json_resp["Data"].items()
        }
        self.get_config_assets()

    def _check_rate_limit_in_response(self, json_resp: Any) -> Tuple[bool, Optional[int]]:
        """
        CryptoCompare returns rate limit in response body with 200 OK status.
        Check for unsuccessful response with rate limit error.
        Note: no "retry-after" is provided in headers or response, use default backoff time for
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
            raise RuntimeError(f"CryptoCompare API failure: {json_resp}")

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
    PRO_KEY = "x-cg-pro-api-key"
    DEMO_KEY = "x-cg-demo-api-key"

    def __init__(self) -> None:
        super().__init__()

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

        json_resp = self.get_json(f"{self.api_root}/coins/list?status=active")
        self.ids = {
            c["id"]: {"symbol": c["symbol"].strip().upper(), "name": c["name"].strip()}
            for c in json_resp
        }
        self.assets = {
            c["symbol"].strip().upper(): {"asset_id": c["id"], "name": c["name"].strip()}
            for c in json_resp
        }
        if self.PRO_KEY in self.headers:
            json_resp = self.get_json(f"{self.api_root}/coins/list?status=inactive")
            for c in json_resp:
                self.ids[c["id"]] = {
                    "symbol": c["symbol"].strip().upper(),
                    "name": c["name"].strip(),
                }
            for c in json_resp:
                self.assets[c["symbol"].strip().upper()] = {
                    "asset_id": c["id"],
                    "name": c["name"].strip(),
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
            CoinPaprika.RATE_LIMIT = 20
            self.headers["Authorization"] = f"{config.coinpaprika_api_key}"
            self.api_root = "https://api-pro.coinpaprika.com/v1"
        else:
            CoinPaprika.RATE_LIMIT = 2
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
            {
                Date(timestamp.date()): {
                    "price": Decimal(repr(p["price"])) if p["price"] else None,
                    "url": SourceUrl(url),
                }
                for p in json_resp
            },
            timestamp,
        )
