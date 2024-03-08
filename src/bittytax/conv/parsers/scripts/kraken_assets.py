# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020
# Generate the constants for the Kraken parser and verify the split method

import re
from typing import Dict, List, Set, Tuple

import requests
from colorama import Back

from bittytax.conv.parsers.kraken import (
    ALT_ASSETS,
    QUOTE_ASSETS,
    STAKED_SUFFIX,
    _split_trading_pair,
)


def get_alt_assets() -> Tuple[Dict[str, str], Set[str]]:
    response = requests.get("https://api.kraken.com/0/public/Assets", timeout=10)

    alt_assets = {}
    staked_suffix = set()
    if response:
        for asset in response.json()["result"]:
            alt = response.json()["result"][asset]["altname"]
            if asset != alt:
                alt_assets[asset] = alt

            match = re.match(r"^[A-Z]+((?:\d{2})?\.[S,M,P])$", asset)
            if match:
                staked_suffix.add(match.group(1))
    else:
        print(f"{response.status_code} {response.reason}")

    return alt_assets, staked_suffix


def get_quote_assets() -> Tuple[List[str], Dict[str, str]]:
    response = requests.get("https://api.kraken.com/0/public/AssetPairs", timeout=10)

    quote_assets = []
    specials = {}
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
                    specials[pair] = wsname.split("/")[1]
                    passed = False
                    print(f"{pair} = {bt_base}/{bt_quote} [Failure] {wsname} ({base} & {quote})")

        if passed:
            print("===Split trading pairs PASSED===")
        else:
            print("===Split trading pairs FAILED===")
    else:
        print(f"{response.status_code} {response.reason}")

    return quote_assets, specials


def output_constants(
    alt_assets: Dict[str, str],
    staked_suffix: Set[str],
    quote_assets: List[str],
    specials: Dict[str, str],
) -> None:
    print("\nQUOTE_ASSETS = [")
    for i in sorted(quote_assets):
        if i in QUOTE_ASSETS:
            print(f'    "{i}",')
        else:
            print(f'    {Back.RED}"{i}"{Back.RESET},')
    print("]")

    print("\nALT_ASSETS = {")
    for k, v in sorted(alt_assets.items()):
        if k in ALT_ASSETS:
            print(f'    "{k}": "{v}",')
        else:
            print(f'    {Back.RED}"{k}": "{v}"{Back.RESET},')
    print("}")

    print("\nSTAKED_SUFFIX = [")
    for i in sorted(staked_suffix):
        if i in STAKED_SUFFIX:
            print(f'    "{i}",')
        else:
            print(f'    {Back.RED}"{i}"{Back.RESET},')
    print("]")

    print("\nTRADINGPAIR_TO_QUOTE_ASSET = {")
    for i in sorted(specials):
        print(f'    {Back.RED}"{i}": "{specials[i]}"{Back.RESET},')
    print("}")


if __name__ == "__main__":
    output_constants(*get_alt_assets(), *get_quote_assets())
