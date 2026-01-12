import requests

from bittytax.conv.parsers.gemini import QUOTE_ASSETS, _split_trading_pair


def test_split_trading_pair() -> None:
    response = requests.get("https://api.gemini.com/v1/symbols", timeout=10)

    if response:
        for symbol in response.json():
            response = requests.get(
                f"https://api.gemini.com/v1/symbols/details/{symbol}", timeout=10
            )
            if response:
                quote = response.json()["quote_currency"]
                base = response.json()["base_currency"]

                assert quote in QUOTE_ASSETS

                bt_base, bt_quote = _split_trading_pair(symbol.upper())

                if symbol.endswith("perp"):
                    assert bt_base is None
                    assert bt_quote is None
                else:
                    assert bt_base == base
                    assert bt_quote == quote
