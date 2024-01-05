# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024
# Generate the constants for the Gemini parser.

import requests

from bittytax.conv.parsers.gemini import _split_trading_pair


def get_assets() -> None:
    response = requests.get("https://api.gemini.com/v1/symbols", timeout=10)

    if response:
        quote_assets = []
        base_assets = []
        passed = True

        for symbol in response.json():
            response = requests.get(
                f"https://api.gemini.com/v1/symbols/details/{symbol}", timeout=10
            )
            if response:
                quote = response.json()["quote_currency"]
                base = response.json()["base_currency"]

                if quote not in quote_assets:
                    quote_assets.append(quote)

                if base not in base_assets:
                    base_assets.append(base)
            else:
                print(f"{response.status_code} {response.reason}")

            # Validate split method
            bt_base, bt_quote = _split_trading_pair(symbol.upper())

            if bt_base == base and bt_quote == quote:
                print(f"{symbol} = {bt_base}/{bt_quote} [OK]")
            elif bt_base is None and bt_quote is None and symbol.endswith("perp"):
                print(f"{symbol} = {bt_base}/{bt_quote} [OK] ({base} & {quote}) Skip futures")
            else:
                passed = False
                print(f"{symbol} = {bt_base}/{bt_quote} [Failure] ({base} & {quote})")

        if passed:
            print("===Split trading pairs PASSED===")
        else:
            print("===Split trading pairs FAILED===")

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
