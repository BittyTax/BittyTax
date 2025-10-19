import requests

from bittytax.conv.parsers.binance import BASE_ASSETS, QUOTE_ASSETS, _split_trading_pair


def test_split_trading_pair() -> None:
    response = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=10)

    if response:
        for symbol in response.json()["symbols"]:
            quote = symbol["quoteAsset"]
            base = symbol["baseAsset"]

            assert quote in QUOTE_ASSETS

            if base[0].isdigit():
                assert base in BASE_ASSETS

            bt_base, bt_quote = _split_trading_pair(symbol["symbol"])

            assert bt_base == base
            assert bt_quote == quote
