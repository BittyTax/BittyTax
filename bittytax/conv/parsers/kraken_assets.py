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

    print("QUOTE_ASSETS = %s\n" % sorted(quote_assets))

response = requests.get("https://api.kraken.com/0/public/Assets")

if response:
    alt_assets = {}
    for asset in response.json()["result"]:
        alt = response.json()["result"][asset]["altname"]
        if asset != alt:
            alt_assets[asset] = alt


    print("ALT_ASSETS = {%s}" % ", ".join("\"{}\": \"{}\"".format(k, v)
                                          for k, v in sorted(alt_assets.items())))
