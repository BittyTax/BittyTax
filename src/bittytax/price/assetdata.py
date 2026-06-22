# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import os
from decimal import Decimal
from typing import List, Optional, cast

from colorama import Fore
from tqdm import tqdm
from typing_extensions import NotRequired, TypedDict

from ..bt_types import (
    AssetId,
    AssetName,
    AssetSymbol,
    DataSourceName,
    Date,
    QuoteSymbol,
    Timestamp,
    TradingPair,
)
from ..config import config
from ..constants import CACHE_DIR
from ..utils import disable_tqdm
from .datasource import DataSourceBase
from .exceptions import UnexpectedDataSourceError


class AsRecord(TypedDict):  # pylint: disable=too-few-public-methods
    symbol: AssetSymbol
    name: Optional[AssetName]
    data_source: Optional[DataSourceName]
    asset_id: NotRequired[AssetId]
    priority: NotRequired[bool]
    deprecated: NotRequired[bool]


class AsPriceRecord(AsRecord):  # pylint: disable=too-few-public-methods
    price: Optional[Decimal]
    quote: QuoteSymbol


class AssetData:
    def __init__(
        self, no_cache: bool = False, data_sources_required: Optional[List[str]] = None
    ) -> None:
        self.no_cache = no_cache
        self.data_sources = {}

        if not os.path.exists(CACHE_DIR):
            os.mkdir(CACHE_DIR)

        all_classes = DataSourceBase.__subclasses__()
        if data_sources_required is not None:
            ds_classes = [
                cls
                for cls in all_classes
                if cls.__name__.upper() in {ds.upper() for ds in data_sources_required}
            ]
        else:
            ds_classes = list(all_classes)

        if ds_classes:
            with tqdm(
                total=len(ds_classes),
                desc=f"{Fore.CYAN}initialising data sources{Fore.GREEN}",
                unit="ds",
                leave=False,
                disable=disable_tqdm(),
            ) as pbar:
                for cls in ds_classes:
                    self.data_sources[cls.__name__.upper()] = cls(no_cache, progress_bar=pbar)
                    pbar.update(1)

        for ds in self.data_sources.values():
            ds.progress_bar = None

    def get_assets(
        self, req_symbol: AssetSymbol, req_data_source: str, search_terms: str
    ) -> List[AsRecord]:
        if not req_data_source or req_data_source == "ALL":
            data_sources = list(self.data_sources.keys())
        else:
            data_sources = [req_data_source]

        asset_data = []
        for ds in data_sources:
            if not req_symbol:
                assets = self.data_sources[ds].get_list()
            else:
                assets = {}
                assets[req_symbol] = self.data_sources[ds].get_list().get(req_symbol, [])
            for symbol in assets:
                for asset_id in assets[symbol]:
                    if search_terms:
                        match = self.do_search(
                            symbol, asset_id["name"], search_terms, asset_id["asset_id"]
                        )
                    else:
                        match = True

                    if match:
                        asset_data.append(
                            AsRecord(
                                symbol=symbol,
                                name=asset_id["name"],
                                data_source=self.data_sources[ds].name(),
                                asset_id=asset_id["asset_id"],
                                priority=(
                                    self._is_priority(symbol, asset_id["asset_id"], ds)
                                    if (not req_data_source or req_data_source == "ALL")
                                    and not search_terms
                                    else False
                                ),
                                deprecated=self.data_sources[ds].DEPRECATED,
                            )
                        )

        return sorted(asset_data, key=lambda a: a["symbol"].lower())

    def _is_priority(self, symbol: AssetSymbol, asset_id: AssetId, data_source: str) -> bool:
        if symbol in config.data_source_select:
            ds_priority = [ds.split(":")[0] for ds in config.data_source_select[symbol]]
        elif symbol in config.fiat_list:
            ds_priority = config.data_source_fiat
        else:
            ds_priority = config.data_source_crypto

        for ds in ds_priority:
            if ds.upper() in self.data_sources:
                if symbol in self.data_sources[ds.upper()].assets:
                    if (
                        ds.upper() == data_source.upper()
                        and self.data_sources[ds.upper()].assets[symbol].get("asset_id") == asset_id
                    ):
                        return True
                    return False
            else:
                raise UnexpectedDataSourceError(ds, DataSourceBase.datasources_str())
        return False

    @staticmethod
    def do_search(symbol: str, name: str, search_terms: str, asset_id: str = "") -> bool:
        for search_term in search_terms:
            if search_term.upper() not in f"{symbol} {name} {asset_id}".upper():
                return False

        return True

    def get_latest_price_ds(
        self, req_symbol: AssetSymbol, req_data_source: str
    ) -> List[AsPriceRecord]:
        if req_data_source == "ALL":
            data_sources = list(self.data_sources.keys())
        else:
            data_sources = [req_data_source]

        all_assets = []
        for ds in data_sources:
            if config.ccy not in type(self.data_sources[ds]).LATEST_QUOTES:
                continue

            for asset_id in self.data_sources[ds].get_list().get(req_symbol, []):
                asset_data = cast(AsPriceRecord, asset_id)
                asset_data["symbol"] = req_symbol
                asset_data["data_source"] = self.data_sources[ds].name()
                asset_data["priority"] = (
                    self._is_priority(asset_data["symbol"], asset_data["asset_id"], ds)
                    if req_data_source == "ALL"
                    else False
                )
                asset_data["quote"] = config.ccy
                asset_data["price"] = self.data_sources[ds].get_latest(
                    req_symbol, asset_data["quote"], asset_data["asset_id"]
                )
                all_assets.append(asset_data)
        return all_assets

    def get_historic_btc_price(self, date: Timestamp) -> "AsPriceRecord":
        btc_priority = (
            [ds.split(":")[0] for ds in config.data_source_select[AssetSymbol("BTC")]]
            if AssetSymbol("BTC") in config.data_source_select
            else config.data_source_crypto
        )
        for data_source in btc_priority:
            ds_key = data_source.upper()
            if ds_key not in self.data_sources:
                continue
            ds_obj = self.data_sources[ds_key]
            if AssetSymbol("BTC") not in ds_obj.assets:
                continue
            if config.ccy not in type(ds_obj).HISTORICAL_QUOTES:
                continue
            pair = TradingPair("BTC/" + config.ccy)
            asset_id = ds_obj.assets[AssetSymbol("BTC")]["asset_id"]
            date_key = Date(date.date())
            if not self.no_cache:
                if (
                    pair in ds_obj.prices
                    and asset_id in ds_obj.prices[pair]
                    and date_key in ds_obj.prices[pair][asset_id]
                ):
                    cached = ds_obj.prices[pair][asset_id][date_key]["price"]
                    if cached is not None:
                        return AsPriceRecord(
                            symbol=AssetSymbol("BTC"),
                            name=ds_obj.assets[AssetSymbol("BTC")]["name"],
                            data_source=ds_obj.name(),
                            asset_id=asset_id,
                            price=cached,
                            quote=config.ccy,
                        )
            ds_obj.get_historical(AssetSymbol("BTC"), config.ccy, date, asset_id)
            if (
                pair in ds_obj.prices
                and asset_id in ds_obj.prices[pair]
                and date_key in ds_obj.prices[pair][asset_id]
            ):
                fetched = ds_obj.prices[pair][asset_id][date_key]["price"]
                if fetched is not None:
                    return AsPriceRecord(
                        symbol=AssetSymbol("BTC"),
                        name=ds_obj.assets[AssetSymbol("BTC")]["name"],
                        data_source=ds_obj.name(),
                        asset_id=asset_id,
                        price=fetched,
                        quote=config.ccy,
                    )
        raise RuntimeError("BTC price is not available")

    def get_historic_price_ds(
        self,
        req_symbol: AssetSymbol,
        req_date: Timestamp,
        req_data_source: str,
    ) -> List[AsPriceRecord]:
        if req_data_source == "ALL":
            data_sources = list(self.data_sources.keys())
        else:
            data_sources = [req_data_source]

        all_assets = []
        for ds in data_sources:
            has_direct = config.ccy in type(self.data_sources[ds]).HISTORICAL_QUOTES
            has_btc = req_symbol != "BTC" and "BTC" in type(self.data_sources[ds]).HISTORICAL_QUOTES

            if config.price_via_btc:
                if has_btc:
                    quote = QuoteSymbol("BTC")
                elif has_direct:
                    quote = config.ccy
                else:
                    continue
            else:
                if has_direct:
                    quote = config.ccy
                elif has_btc:
                    quote = QuoteSymbol("BTC")
                else:
                    continue

            for asset_id in self.data_sources[ds].get_list().get(req_symbol, []):
                asset_data = cast(AsPriceRecord, asset_id)
                asset_data["symbol"] = req_symbol
                asset_data["data_source"] = self.data_sources[ds].name()
                asset_data["priority"] = (
                    self._is_priority(asset_data["symbol"], asset_data["asset_id"], ds)
                    if req_data_source == "ALL"
                    else False
                )
                asset_data["quote"] = quote

                date = Date(req_date.date())
                pair = TradingPair(req_symbol + "/" + asset_data["quote"])

                if not self.no_cache:
                    # Check cache first
                    aid = asset_data["asset_id"]
                    if (
                        pair in self.data_sources[ds].prices
                        and aid in self.data_sources[ds].prices[pair]
                        and date in self.data_sources[ds].prices[pair][aid]
                    ):
                        asset_data["price"] = self.data_sources[ds].prices[pair][aid][date]["price"]
                        all_assets.append(asset_data)
                        continue

                self.data_sources[ds].get_historical(
                    req_symbol, asset_data["quote"], req_date, asset_data["asset_id"]
                )
                aid = asset_data["asset_id"]
                if (
                    pair in self.data_sources[ds].prices
                    and aid in self.data_sources[ds].prices[pair]
                    and date in self.data_sources[ds].prices[pair][aid]
                ):
                    asset_data["price"] = self.data_sources[ds].prices[pair][aid][date]["price"]
                else:
                    asset_data["price"] = None

                all_assets.append(asset_data)
        return all_assets
