# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020
# Generate the constants for the Kraken parser.

import requests

response = requests.get("https://api.kraken.com/0/public/AssetPairs")

if response:
    quote_assets = []
    for pair in response.json()["result"]:
        if response.json()["result"][pair].get("wsname"):
            if pair.endswith(response.json()["result"][pair]["quote"]):
                quote = response.json()["result"][pair]["quote"]
            else:
                quote = response.json()["result"][pair]["wsname"].split('/')[1]

            if quote not in quote_assets:
                quote_assets.append(quote)

    rows = []
    for i in range(0, len(quote_assets), 10):
        rows.append(", ".join("\'{}\'".format(v)
                for v in sorted(quote_assets)[i:i+10]))

    print("QUOTE_ASSETS = [%s]\n" % (',\n                '.join(rows)))

response = requests.get("https://api.kraken.com/0/public/Assets")

if response:
    alt_assets = {}
    for asset in response.json()["result"]:
        alt = response.json()["result"][asset]["altname"]
        if asset != alt:
            alt_assets[asset] = alt

    rows = []
    for i in range(0, len(alt_assets), 5):
        rows.append(", ".join("\'{}\': \'{}\'".format(k, v)
                for k, v in sorted(alt_assets.items())[i:i+5]))

    print("ALT_ASSETS = {%s}" % (',\n              '.join(rows)))
