import requests

from bittytax.conv.parsers.mexc import QUOTE_ASSETS, _split_trading_pair


def test_split_trading_pair() -> None:
    response = requests.get("https://api.mexc.com/api/v3/exchangeInfo", timeout=10)

    if response:
        for symbol in response.json()["symbols"]:
            quote = symbol["quoteAsset"]
            base = symbol["baseAsset"]

            assert quote in QUOTE_ASSETS

            bt_base, bt_quote = _split_trading_pair(symbol["symbol"])

            assert bt_base == base
            assert bt_quote == quote
