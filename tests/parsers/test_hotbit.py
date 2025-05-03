import requests

from bittytax.conv.dataparser import DataParser
from bittytax.conv.parsers.hotbit import QUOTE_ASSETS, _split_trading_pair, parse_hotbit_orders_v3


def test_split_trading_pair() -> None:
    response = requests.get("https://api.hotbit.io/api/v1/market.list", timeout=10)

    if response:
        for market in response.json()["result"]:
            quote = market["money"]

            assert quote in QUOTE_ASSETS

            bt_base, bt_quote = _split_trading_pair(market["name"])

            assert bt_base == market["stock"]
            assert bt_quote == market["money"]


def test_parser() -> None:
    parser = DataParser.match_header(["Date", "Pair", "Side", "Price", "Volume", "Fee", "Total"], 0)

    assert parser.all_handler is parse_hotbit_orders_v3
