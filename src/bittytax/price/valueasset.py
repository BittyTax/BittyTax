# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, Optional, Tuple, Union

from colorama import Fore, Style

from ..bt_types import AssetName, AssetSymbol, DataSourceName, Date, Timestamp, Year
from ..config import config
from ..constants import WARNING
from ..utils import bt_tqdm_write
from .pricedata import PriceData, PriceDataRecord

if TYPE_CHECKING:
    from ..transactions import Buy, Sell


@dataclass
class ValueOrigin:
    origin: Union["Buy", "Sell"]
    price_record: Optional[PriceDataRecord] = None
    derived_price: bool = False


class ValueAsset:
    def __init__(
        self, price_tool: bool = False, no_cache: bool = False, leave_bar: bool = False
    ) -> None:
        self.price_tool = price_tool
        self.price_report: Dict[Year, Dict[AssetSymbol, Dict[Date, PriceDataRecord]]] = {}
        data_sources_required = set(config.data_source_fiat + config.data_source_crypto) | {
            x.split(":")[0] for v in config.data_source_select.values() for x in v
        }
        self.price_data = PriceData(list(data_sources_required), price_tool, no_cache, leave_bar)

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
        price_record = self.get_latest_price(asset)
        if price_record.price_ccy is not None:
            return price_record.price_ccy * quantity, price_record.name, price_record.data_source

        return None, AssetName(""), DataSourceName("")

    def get_historical_price(self, asset: AssetSymbol, timestamp: Timestamp) -> PriceDataRecord:
        if not self.price_tool and timestamp.date() >= datetime.now().date():
            bt_tqdm_write(
                f"{WARNING} Price for {asset} on {timestamp:%Y-%m-%d}, "
                f"no historic price available, using latest price"
            )
            price_record = self.get_latest_price(asset)
            return price_record

        price_record = self.price_data.get_historical(asset, config.ccy, timestamp)
        self.price_report_cache(asset, timestamp, price_record)
        if price_record.btc_record:
            self.price_report_cache(AssetSymbol("BTC"), timestamp, price_record.btc_record)
        return price_record

    def get_latest_price(self, asset: AssetSymbol) -> PriceDataRecord:
        return self.price_data.get_latest(asset, config.ccy)

    def price_report_cache(
        self, asset: AssetSymbol, timestamp: Timestamp, price_record: PriceDataRecord
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
            self.price_report[tax_year][asset][Date(date)] = price_record
