# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020
# Generate the constants for the Kraken parser and verify the split method

import requests

from bittytax.conv.parsers.kraken import _split_trading_pair


def get_alt_assets():
    response = requests.get("https://api.kraken.com/0/public/Assets", timeout=10)

    alt_assets = {}
    if response:
        for asset in response.json()["result"]:
            alt = response.json()["result"][asset]["altname"]
            if asset != alt:
                alt_assets[asset] = alt

    return alt_assets


def get_quote_assets():
    response = requests.get("https://api.kraken.com/0/public/AssetPairs", timeout=10)

    quote_assets = []
    if response:
        passed = True
        for pair in response.json()["result"]:
            if response.json()["result"][pair].get("wsname"):
                if pair.endswith(response.json()["result"][pair]["quote"]):
                    quote = response.json()["result"][pair]["quote"]
                else:
                    quote = response.json()["result"][pair]["wsname"].split("/")[1]

                if quote not in quote_assets:
                    quote_assets.append(quote)

                # Validate split method
                bt_base, bt_quote = _split_trading_pair(pair)

                wsname = response.json()["result"][pair]["wsname"]
                base = response.json()["result"][pair]["base"]
                quote = response.json()["result"][pair]["quote"]

                if bt_base and bt_quote and bt_base + "/" + bt_quote == wsname:
                    print(f"{pair} = {bt_base}/{bt_quote} [OK]")
                elif bt_base == base and bt_quote == quote:
                    print(f"{pair} = {bt_base}/{bt_quote} [OK]")
                else:
                    passed = False
                    print(f"{pair} = {bt_base}/{bt_quote} [Failure] {wsname} ({base} & {quote})")

        if passed:
            print("===Split trading pairs PASSED===")
        else:
            print("===Split trading pairs FAILED===")

    return quote_assets


def output_constants(alt_assets, quote_assets):
    print("\nQUOTE_ASSETS = [")
    for i in sorted(quote_assets):
        print(f'    "{i}"')
    print("]")

    print("\nALT_ASSETS = {")
    for k, v in sorted(alt_assets.items()):
        print(f'    "{k}": "{v}",')
    print("}")


if __name__ == "__main__":
    output_constants(get_alt_assets(), get_quote_assets())
