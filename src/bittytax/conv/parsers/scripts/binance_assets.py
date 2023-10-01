# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020
# Generate the constants for the Binance parser.

import requests


def get_assets() -> None:
    response = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=10)

    if response:
        quote_assets = []
        base_assets = []

        for symbol in response.json()["symbols"]:
            quote = symbol["quoteAsset"]
            base = symbol["baseAsset"]

            if quote not in quote_assets:
                quote_assets.append(quote)

            if base[0].isdigit() and base not in base_assets:
                base_assets.append(base)

        print("\nQUOTE_ASSETS = [")
        for i in sorted(quote_assets):
            print(f'    "{i}",')
        print("]")

        rows = []
        for i in range(0, len(base_assets), 10):
            rows.append(", ".join(f"'{v}'" for v in sorted(base_assets)[i : i + 10]))

        rows_str = ",/\n               ".join(rows)
        print(f"\nBASE_ASSETS = [{rows_str}]\n")
    else:
        print(f"{response.status_code} {response.reason}")


if __name__ == "__main__":
    get_assets()
