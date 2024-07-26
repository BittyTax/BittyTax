# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024
# Test the _get_asset_from_symbol function of the KuCoin parser.

import requests

from bittytax.conv.parsers.kucoin import _get_asset_from_symbol


def get_symbols() -> None:
    response = requests.get("https://api-futures.kucoin.com/api/v1/contracts/active", timeout=10)

    if response:
        passed = True

        for data in response.json()["data"]:
            symbol = data["symbol"]
            settle_currency = data["settleCurrency"]
            asset = _get_asset_from_symbol(symbol)

            if asset == "BTC":
                asset = "XBT"

            if asset == settle_currency:
                print(f"{symbol} = {settle_currency} [OK]")
            else:
                passed = False
                print(f"{symbol} = {settle_currency} [Failure] ({asset})")

        if passed:
            print("===Get asset from symbol PASSED===")
        else:
            print("===Get asset from symbol FAILED===")
    else:
        print(f"{response.status_code} {response.reason}")


if __name__ == "__main__":
    get_symbols()
