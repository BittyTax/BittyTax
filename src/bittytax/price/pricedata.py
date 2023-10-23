# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import os
from decimal import Decimal
from typing import List, Optional, Tuple

from colorama import Fore

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
from .datasource import DataSourceBase
from .exceptions import UnexpectedDataSourceError


class PriceData:
    def __init__(
        self, data_sources_required: List[DataSourceName], price_tool: bool = False
    ) -> None:
        self.price_tool = price_tool
        self.data_sources = {}

        if not os.path.exists(CACHE_DIR):
            os.mkdir(CACHE_DIR)

        for data_source_class in DataSourceBase.__subclasses__():
            if data_source_class.__name__.upper() in [ds.upper() for ds in data_sources_required]:
                self.data_sources[data_source_class.__name__.upper()] = data_source_class()

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
        no_cache: bool = False,
    ) -> Tuple[Optional[Decimal], AssetName, SourceUrl]:
        if data_source.upper() in self.data_sources:
            if asset in self.data_sources[data_source.upper()].assets:
                date = Date(timestamp.date())
                pair = TradingPair(asset + "/" + quote)

                if not no_cache:
                    # Check cache first
                    if (
                        pair in self.data_sources[data_source.upper()].prices
                        and date in self.data_sources[data_source.upper()].prices[pair]
                    ):
                        return (
                            self.data_sources[data_source.upper()].prices[pair][date]["price"],
                            self.data_sources[data_source.upper()].assets[asset]["name"],
                            self.data_sources[data_source.upper()].prices[pair][date]["url"],
                        )

                self.data_sources[data_source.upper()].get_historical(asset, quote, timestamp)
                if (
                    pair in self.data_sources[data_source.upper()].prices
                    and date in self.data_sources[data_source.upper()].prices[pair]
                ):
                    return (
                        self.data_sources[data_source.upper()].prices[pair][date]["price"],
                        self.data_sources[data_source.upper()].assets[asset]["name"],
                        self.data_sources[data_source.upper()].prices[pair][date]["url"],
                    )
                return (
                    None,
                    self.data_sources[data_source.upper()].assets[asset]["name"],
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
        self, asset: AssetSymbol, quote: QuoteSymbol, timestamp: Timestamp, no_cache: bool = False
    ) -> Tuple[Optional[Decimal], AssetName, DataSourceName, SourceUrl]:
        name = AssetName("")
        for data_source in self.data_source_priority(asset):
            price, name, url = self.get_historical_ds(
                data_source, asset, quote, timestamp, no_cache
            )
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
