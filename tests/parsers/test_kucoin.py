import requests

from bittytax.conv.parsers.kucoin import _get_asset_from_symbol


def test_get_asset_from_symbol() -> None:
    response = requests.get("https://api-futures.kucoin.com/api/v1/contracts/active", timeout=10)

    if response:
        for data in response.json()["data"]:
            symbol = data["symbol"]
            settle_currency = data["settleCurrency"]

            asset = _get_asset_from_symbol(symbol)

            if asset == "BTC":
                asset = "XBT"

            assert asset == settle_currency
