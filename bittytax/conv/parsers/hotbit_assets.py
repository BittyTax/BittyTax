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

        rows = []
        for i in range(0, len(quote_assets), 10):
            rows.append(", ".join("\'{}\'".format(v)
                                  for v in sorted(quote_assets)[i:i+10]))

        print("QUOTE_ASSETS = [%s]\n" % (',\n                '.join(rows)))

        rows = []
        for i in range(0, len(base_assets), 10):
            rows.append(", ".join("\'{}\'".format(v)
                                  for v in sorted(base_assets)[i:i+10]))

        print("BASE_ASSETS = [%s]\n" % (',\n                '.join(rows)))

get_assets()
