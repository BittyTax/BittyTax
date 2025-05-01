# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020
# Generate the constants for the Binance parser.

import requests
from colorama import Back

from ..binance import BASE_ASSETS, QUOTE_ASSETS, _split_trading_pair


def get_assets() -> None:
    response = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=10)

    if response:
        quote_assets = []
        base_assets = []
        specials = {}
        passed = True

        for symbol in response.json()["symbols"]:
            quote = symbol["quoteAsset"]
            base = symbol["baseAsset"]
            symbol = symbol["symbol"]

            if quote not in quote_assets:
                quote_assets.append(quote)

            if base[0].isdigit() and base not in base_assets:
                base_assets.append(base)

            # Validate split method
            bt_base, bt_quote = _split_trading_pair(symbol)

            if bt_base == base and bt_quote == quote:
                print(f"{symbol} = {bt_base}/{bt_quote} [OK]")
            else:
                specials[symbol] = quote
                passed = False
                print(f"{symbol} = {bt_base}/{bt_quote} [Failure] ({base} & {quote})")

        if passed:
            print("===Split trading pairs PASSED===")
        else:
            print("===Split trading pairs FAILED===")

        print("\nQUOTE_ASSETS = [")
        for i in sorted(quote_assets):
            if i in QUOTE_ASSETS:
                print(f'    "{i}",')
            else:
                print(f'    {Back.RED}"{i}"{Back.RESET},')
        print("]")

        print("\nBASE_ASSETS = [")
        for i in sorted(base_assets):
            if i in BASE_ASSETS:
                print(f'    "{i}",')
            else:
                print(f'    {Back.RED}"{i}"{Back.RESET},')
        print("]")

        print("\nTRADINGPAIR_TO_QUOTE_ASSET = {")
        for i in sorted(specials):
            print(f'    {Back.RED}"{i}": "{specials[i]}"{Back.RESET},')
        print("}")
    else:
        print(f"{response.status_code} {response.reason}")


if __name__ == "__main__":
    get_assets()
