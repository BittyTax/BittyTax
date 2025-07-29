# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, Optional, Tuple, Union

from colorama import Fore, Style

from ..bt_types import (
    AssetName,
    AssetSymbol,
    DataSourceName,
    Date,
    QuoteSymbol,
    SourceUrl,
    Timestamp,
    Year,
)
from ..config import config
from ..constants import WARNING
from ..utils import bt_tqdm_write
from .pricedata import PriceData

if TYPE_CHECKING:
    from ..transactions import Buy, Sell


@dataclass
class VaPriceRecord:
    name: AssetName
    data_source: DataSourceName
    url: SourceUrl
    price_ccy: Optional[Decimal]
    price_btc: Optional[Decimal]


@dataclass
class ValueOrigin:
    origin: Union["Buy", "Sell"]
    price_record: Optional[VaPriceRecord] = None
    derived_price: bool = False


class ValueAsset:
    def __init__(self, price_tool: bool = False) -> None:
        self.price_tool = price_tool
        self.price_report: Dict[Year, Dict[AssetSymbol, Dict[Date, VaPriceRecord]]] = {}
        data_sources_required = set(config.data_source_fiat + config.data_source_crypto) | {
            x.split(":")[0] for v in config.data_source_select.values() for x in v
        }
        self.price_data = PriceData(list(data_sources_required), price_tool)

    def get_value(self, t: Union["Buy", "Sell"]) -> Tuple[Decimal, ValueOrigin]:
        if t.asset == config.ccy:
            return t.quantity, ValueOrigin(t)

        if t.quantity == 0:
            return Decimal(0), ValueOrigin(t)

        price_record = self.get_historical_price(t.asset, t.timestamp)
        if price_record.price_ccy is not None:
            value = price_record.price_ccy * t.quantity
            if config.debug:
                print(
                    f"{Fore.YELLOW}price: {t.timestamp:%Y-%m-%d}, 1 "
                    f"{t.asset}={config.sym()}{price_record.price_ccy:0,.2f} {config.ccy}, "
                    f"{t.quantity.normalize():0,f} {t.asset}="
                    f"{Style.BRIGHT}{config.sym()}{value:0,.2f} {config.ccy}{Style.NORMAL}"
                )
            return value, ValueOrigin(t, price_record)

        bt_tqdm_write(
            f"{WARNING} Price for {t.asset} on {t.timestamp:%Y-%m-%d} is not available, "
            f"using price of {config.sym()}{0:0,.2f}"
        )
        return Decimal(0), ValueOrigin(t, price_record)

    def get_current_value(
        self, asset: AssetSymbol, quantity: Decimal
    ) -> Tuple[Optional[Decimal], AssetName, DataSourceName]:
        asset_price_ccy, name, data_source = self.get_latest_price(asset)
        if asset_price_ccy is not None:
            return asset_price_ccy * quantity, name, data_source

        return None, AssetName(""), DataSourceName("")

    def get_historical_price(
        self, asset: AssetSymbol, timestamp: Timestamp, no_cache: bool = False
    ) -> VaPriceRecord:
        asset_price_ccy = None

        if not self.price_tool and timestamp.date() >= datetime.now().date():
            bt_tqdm_write(
                f"{WARNING} Price for {asset} on {timestamp:%Y-%m-%d}, "
                f"no historic price available, using latest price"
            )
            asset_price_ccy, name, data_source = self.get_latest_price(asset)
            price_record = VaPriceRecord(name, data_source, SourceUrl(""), asset_price_ccy, None)
            return price_record

        if asset == "BTC" or asset in config.fiat_list:
            asset_price_ccy, name, data_source, url = self.price_data.get_historical(
                asset, config.ccy, timestamp, no_cache
            )
            price_record = VaPriceRecord(name, data_source, url, asset_price_ccy, None)
            self.price_report_cache(asset, timestamp, name, data_source, url, asset_price_ccy)
        else:
            asset_price_btc, name, data_source, url = self.price_data.get_historical(
                asset, QuoteSymbol("BTC"), timestamp, no_cache
            )
            if asset_price_btc is not None:
                (
                    btc_price_ccy,
                    name2,
                    data_source2,
                    url2,
                ) = self.price_data.get_historical(
                    AssetSymbol("BTC"), config.ccy, timestamp, no_cache
                )
                if btc_price_ccy is not None:
                    asset_price_ccy = btc_price_ccy * asset_price_btc

                self.price_report_cache(
                    AssetSymbol("BTC"), timestamp, name2, data_source2, url2, btc_price_ccy
                )

            self.price_report_cache(
                asset,
                timestamp,
                name,
                data_source,
                url,
                asset_price_ccy,
                asset_price_btc,
            )
            price_record = VaPriceRecord(name, data_source, url, asset_price_ccy, asset_price_btc)

        return price_record

    def get_latest_price(
        self, asset: AssetSymbol
    ) -> Tuple[Optional[Decimal], AssetName, DataSourceName]:
        asset_price_ccy = None

        if asset == "BTC" or asset in config.fiat_list:
            asset_price_ccy, name, data_source = self.price_data.get_latest(asset, config.ccy)
        else:
            asset_price_btc, name, data_source = self.price_data.get_latest(
                asset, QuoteSymbol("BTC")
            )

            if asset_price_btc is not None:
                btc_price_ccy, _, _ = self.price_data.get_latest(AssetSymbol("BTC"), config.ccy)
                if btc_price_ccy is not None:
                    asset_price_ccy = btc_price_ccy * asset_price_btc

        return asset_price_ccy, name, data_source

    def price_report_cache(
        self,
        asset: AssetSymbol,
        timestamp: Timestamp,
        name: AssetName,
        data_source: DataSourceName,
        url: SourceUrl,
        price_ccy: Optional[Decimal],
        price_btc: Optional[Decimal] = None,
    ) -> None:
        date = timestamp.date()

        if date > config.get_tax_year_end(date.year):
            tax_year = Year(date.year + 1)
        else:
            tax_year = Year(date.year)

        if tax_year not in self.price_report:
            self.price_report[tax_year] = {}

        if asset not in self.price_report[tax_year]:
            self.price_report[tax_year][asset] = {}

        if date not in self.price_report[tax_year][asset]:
            self.price_report[tax_year][asset][Date(date)] = VaPriceRecord(
                name=name,
                data_source=data_source,
                url=url,
                price_ccy=price_ccy,
                price_btc=price_btc,
            )
