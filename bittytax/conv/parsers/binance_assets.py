# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020
# Generate the constants for the Binance parser.

import requests

response = requests.get("https://api.binance.com/api/v3/exchangeInfo")

if response:
    quote_assets = []
    for symbol in response.json()["symbols"]:
        quote = symbol["quoteAsset"]

        if quote not in quote_assets:
            quote_assets.append(quote)

    rows = []
    for i in range(0, len(quote_assets), 10):
        rows.append(", ".join("\'{}\'".format(v)
                for v in sorted(quote_assets)[i:i+10]))

    print("QUOTE_ASSETS = [%s]\n" % (',\n                '.join(rows)))
