# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import os
from decimal import Decimal
from typing import List, Optional, cast

from typing_extensions import NotRequired, TypedDict

from ..config import config
from ..constants import CACHE_DIR
from ..types import (
    AssetId,
    AssetName,
    AssetSymbol,
    DataSourceName,
    Date,
    QuoteSymbol,
    Timestamp,
    TradingPair,
)
from .datasource import BittyTaxAPI, DataSourceBase, Frankfurter
from .exceptions import UnexpectedDataSourceError


class AsRecord(TypedDict):
    symbol: AssetSymbol
    name: Optional[AssetName]
    data_source: Optional[DataSourceName]
    asset_id: NotRequired[AssetId]
    priority: NotRequired[bool]


class AsPriceRecord(AsRecord):
    price: Optional[Decimal]
    quote: QuoteSymbol


class AssetData:
    FIAT_DATASOURCES = (BittyTaxAPI.__name__, Frankfurter.__name__)

    def __init__(self) -> None:
        self.data_sources = {}

        if not os.path.exists(CACHE_DIR):
            os.mkdir(CACHE_DIR)

        for data_source_class in DataSourceBase.__subclasses__():
            self.data_sources[data_source_class.__name__.upper()] = data_source_class()

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
                        match = self.do_search(symbol, asset_id["name"], search_terms)
                    else:
                        match = True

                    if match:
                        asset_data.append(
                            AsRecord(
                                symbol=symbol,
                                name=asset_id["name"],
                                data_source=self.data_sources[ds].name(),
                                asset_id=asset_id["asset_id"],
                                priority=self._is_priority(symbol, asset_id["asset_id"], ds),
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
    def do_search(symbol: str, name: str, search_terms: str) -> bool:
        for search_term in search_terms:
            if search_term.upper() not in symbol.upper() + " " + name.upper():
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
            for asset_id in self.data_sources[ds].get_list().get(req_symbol, []):
                asset_data = cast(AsPriceRecord, asset_id)
                asset_data["symbol"] = req_symbol
                asset_data["data_source"] = self.data_sources[ds].name()
                asset_data["priority"] = self._is_priority(
                    asset_data["symbol"], asset_data["asset_id"], ds
                )

                if req_symbol == "BTC" or asset_data["data_source"] in self.FIAT_DATASOURCES:
                    asset_data["quote"] = config.ccy
                else:
                    asset_data["quote"] = QuoteSymbol("BTC")

                asset_data["price"] = self.data_sources[ds].get_latest(
                    req_symbol, asset_data["quote"], asset_data["asset_id"]
                )
                all_assets.append(asset_data)
        return all_assets

    def get_historic_price_ds(
        self,
        req_symbol: AssetSymbol,
        req_date: Timestamp,
        req_data_source: str,
        no_cache: bool = False,
    ) -> List[AsPriceRecord]:
        if req_data_source == "ALL":
            data_sources = list(self.data_sources.keys())
        else:
            data_sources = [req_data_source]

        all_assets = []
        for ds in data_sources:
            for asset_id in self.data_sources[ds].get_list().get(req_symbol, []):
                asset_data = cast(AsPriceRecord, asset_id)
                asset_data["symbol"] = req_symbol
                asset_data["data_source"] = self.data_sources[ds].name()
                asset_data["priority"] = self._is_priority(
                    asset_data["symbol"], asset_data["asset_id"], ds
                )

                if req_symbol == "BTC" or asset_data["data_source"] in self.FIAT_DATASOURCES:
                    asset_data["quote"] = config.ccy
                else:
                    asset_data["quote"] = QuoteSymbol("BTC")

                date = Date(req_date.date())
                pair = TradingPair(req_symbol + "/" + asset_data["quote"])

                if not no_cache:
                    # Check cache first
                    if (
                        pair in self.data_sources[ds].prices
                        and date in self.data_sources[ds].prices[pair]
                    ):
                        asset_data["price"] = self.data_sources[ds].prices[pair][date]["price"]
                        all_assets.append(asset_data)
                        continue

                self.data_sources[ds].get_historical(
                    req_symbol, asset_data["quote"], req_date, asset_data["asset_id"]
                )
                if (
                    pair in self.data_sources[ds].prices
                    and date in self.data_sources[ds].prices[pair]
                ):
                    asset_data["price"] = self.data_sources[ds].prices[pair][date]["price"]
                else:
                    asset_data["price"] = None

                all_assets.append(asset_data)
        return all_assets
