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

    print("QUOTE_ASSETS = %s" % sorted(quote_assets))
