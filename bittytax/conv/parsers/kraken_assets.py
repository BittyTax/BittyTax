# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020
# Generate the constants for the Kraken parser and verify the split method

import requests

from bittytax.conv.parsers.kraken import split_trading_pair

def get_alt_assets():
    response = requests.get("https://api.kraken.com/0/public/Assets")

    alt_assets = {}
    if response:
        for asset in response.json()["result"]:
            alt = response.json()["result"][asset]["altname"]
            if asset != alt:
                alt_assets[asset] = alt

    return alt_assets

def get_quote_assets():
    response = requests.get("https://api.kraken.com/0/public/AssetPairs")

    quote_assets = []
    if response:
        passed = True
        for pair in response.json()["result"]:
            if response.json()["result"][pair].get("wsname"):
                if pair.endswith(response.json()["result"][pair]["quote"]):
                    quote = response.json()["result"][pair]["quote"]
                else:
                    quote = response.json()["result"][pair]["wsname"].split('/')[1]

                if quote not in quote_assets:
                    quote_assets.append(quote)

                # validate split method
                bt_base, bt_quote = split_trading_pair(pair)

                wsname = response.json()["result"][pair]["wsname"]
                base = response.json()["result"][pair]["base"]
                quote = response.json()["result"][pair]["quote"]

                if bt_base and bt_quote and bt_base + '/' + bt_quote == wsname:
                    print("%s = %s/%s [OK]" % (pair, bt_base, bt_quote))
                elif bt_base == base and bt_quote == quote:
                    print("%s = %s/%s [OK]" % (pair, bt_base, bt_quote))
                else:
                    passed = False
                    print("%s = %s/%s [Failure] %s (%s & %s)" %
                          (pair, bt_base, bt_quote, wsname, base, quote))

        if passed:
            print("===Split trading pairs PASSED===")
        else:
            print("===Split trading pairs FAILED===")

    return quote_assets

def output_constants(alt_assets, quote_assets):
    rows = []
    for i in range(0, len(quote_assets), 10):
        rows.append(", ".join("\'{}\'".format(v)
                              for v in sorted(quote_assets)[i:i+10]))

    print("\nQUOTE_ASSETS = [%s]\n" % (',\n                '.join(rows)))

    rows = []
    for i in range(0, len(alt_assets), 5):
        rows.append(", ".join("\'{}\': \'{}\'".format(k, v)
                              for k, v in sorted(alt_assets.items())[i:i+5]))

    print("ALT_ASSETS = {%s}" % (',\n              '.join(rows)))

output_constants(get_alt_assets(), get_quote_assets())
