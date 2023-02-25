# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022
# Generate the constants for the Hotbit parser.

import requests


def get_assets():
    response = requests.get("https://api.hotbit.io/api/v1/market.list", timeout=10)

    if response:
        quote_assets = []
        base_assets = []

        for market in response.json()["result"]:
            quote = market["money"]
            base = market["stock"]

            if quote not in quote_assets:
                quote_assets.append(quote)

            if base not in base_assets:
                base_assets.append(base)

        print("\nQUOTE_ASSETS = [")
        for i in sorted(quote_assets):
            print('    "%s",' % i)
        print("]")

        rows = []
        for i in range(0, len(base_assets), 10):
            rows.append(", ".join("'{}'".format(v) for v in sorted(base_assets)[i : i + 10]))

        print("\nBASE_ASSETS = [%s]\n" % (",\n               ".join(rows)))


if __name__ == "__main__":
    get_assets()
