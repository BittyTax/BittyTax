# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import os
from decimal import Decimal
from typing import List, Optional, Tuple

from colorama import Fore
from tqdm import tqdm

from ..bt_types import (
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
from ..constants import CACHE_DIR
from ..utils import disable_tqdm
from .datasource import DataSourceBase
from .exceptions import UnexpectedDataSourceError


class PriceData:
    def __init__(
        self,
        data_sources_required: List[DataSourceName],
        price_tool: bool = False,
        no_cache: bool = False,
        leave_bar: bool = False,
    ) -> None:
        self.price_tool = price_tool
        self.no_cache = no_cache
        self.data_sources = {}
        self.progress_bar = None

        if not os.path.exists(CACHE_DIR):
            os.mkdir(CACHE_DIR)

        ds_classes = [
            cls
            for cls in DataSourceBase.__subclasses__()
            if cls.__name__.upper() in {ds.upper() for ds in data_sources_required}
        ]
        if ds_classes:
            with tqdm(
                total=len(ds_classes),
                desc=f"{Fore.CYAN}initialising data sources{Fore.GREEN}",
                unit="ds",
                leave=leave_bar,
                disable=disable_tqdm(),
            ) as pbar:
                for cls in ds_classes:
                    self.data_sources[cls.__name__.upper()] = cls(no_cache, progress_bar=pbar)
                    pbar.update(1)

        for ds in self.data_sources.values():
            ds.progress_bar = None

    @staticmethod
    def data_source_priority(asset: AssetSymbol) -> List[DataSourceName]:
        if asset in config.data_source_select:
            return [ds.split(":")[0] for ds in config.data_source_select[asset]]
        if asset in config.fiat_list:
            return config.data_source_fiat
        return config.data_source_crypto

    def get_latest_ds(
        self, data_source: DataSourceName, asset: AssetSymbol, quote: QuoteSymbol
    ) -> Tuple[Optional[Decimal], AssetName]:
        if data_source.upper() in self.data_sources:
            if asset in self.data_sources[data_source.upper()].assets:
                self.data_sources[data_source.upper()].progress_bar = self.progress_bar
                return (
                    self.data_sources[data_source.upper()].get_latest(asset, quote),
                    self.data_sources[data_source.upper()].assets[asset]["name"],
                )

            return None, AssetName("")
        raise UnexpectedDataSourceError(data_source, DataSourceBase.datasources_str())

    def get_historical_ds(
        self,
        data_source: DataSourceName,
        asset: AssetSymbol,
        quote: QuoteSymbol,
        timestamp: Timestamp,
    ) -> Tuple[Optional[Decimal], AssetName, SourceUrl]:
        if data_source.upper() in self.data_sources:
            ds_obj = self.data_sources[data_source.upper()]
            if asset in ds_obj.assets:
                ds_obj.progress_bar = self.progress_bar
                date = Date(timestamp.date())
                pair = TradingPair(asset + "/" + quote)
                asset_id = ds_obj.assets[asset]["asset_id"]

                if not self.no_cache:
                    if (
                        pair in ds_obj.prices
                        and asset_id in ds_obj.prices[pair]
                        and date in ds_obj.prices[pair][asset_id]
                    ):
                        return (
                            ds_obj.prices[pair][asset_id][date]["price"],
                            ds_obj.assets[asset]["name"],
                            ds_obj.prices[pair][asset_id][date]["url"],
                        )

                ds_obj.get_historical(asset, quote, timestamp)
                if (
                    pair in ds_obj.prices
                    and asset_id in ds_obj.prices[pair]
                    and date in ds_obj.prices[pair][asset_id]
                ):
                    return (
                        ds_obj.prices[pair][asset_id][date]["price"],
                        ds_obj.assets[asset]["name"],
                        ds_obj.prices[pair][asset_id][date]["url"],
                    )
                return (
                    None,
                    ds_obj.assets[asset]["name"],
                    SourceUrl(""),
                )
            return None, AssetName(""), SourceUrl("")
        raise UnexpectedDataSourceError(data_source, DataSourceBase.datasources_str())

    def get_latest(
        self, asset: AssetSymbol, quote: QuoteSymbol
    ) -> Tuple[Optional[Decimal], AssetName, DataSourceName]:
        name = AssetName("")
        for data_source in self.data_source_priority(asset):
            price, name = self.get_latest_ds(data_source, asset, quote)
            if price is not None:
                if config.debug:
                    print(
                        f"{Fore.YELLOW}price: <latest>, 1 "
                        f"{asset}={price.normalize():0,f} {quote} via "
                        f"{self.data_sources[data_source.upper()].name()} ({name})"
                    )
                if self.price_tool:
                    print(
                        f"{Fore.YELLOW}1 {asset}={price.normalize():0,f} {quote} "
                        f"{Fore.CYAN}via {self.data_sources[data_source.upper()].name()} ({name})"
                    )
                return price, name, self.data_sources[data_source.upper()].name()
        return None, name, DataSourceName("")

    def get_historical(
        self, asset: AssetSymbol, quote: QuoteSymbol, timestamp: Timestamp
    ) -> Tuple[Optional[Decimal], AssetName, DataSourceName, SourceUrl]:
        name = AssetName("")
        for data_source in self.data_source_priority(asset):
            price, name, url = self.get_historical_ds(data_source, asset, quote, timestamp)
            if price is not None:
                if config.debug:
                    print(
                        f"{Fore.YELLOW}price: {timestamp:%Y-%m-%d}, 1 "
                        f"{asset}={price.normalize():0,f} {quote} via "
                        f"{self.data_sources[data_source.upper()].name()} ({name})"
                    )
                if self.price_tool:
                    print(
                        f"{Fore.YELLOW}1 {asset}={price.normalize():0,f} {quote} "
                        f"{Fore.CYAN}via {self.data_sources[data_source.upper()].name()} ({name})"
                    )
                return price, name, self.data_sources[data_source.upper()].name(), url
        return None, name, DataSourceName(""), SourceUrl("")
