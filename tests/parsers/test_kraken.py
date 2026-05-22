import re
from decimal import Decimal

import requests

from bittytax.bt_types import TrType
from bittytax.conv.datarow import DataRow
from bittytax.conv.parsers.kraken import (
    ALT_ASSETS,
    QUOTE_ASSETS,
    STAKED_SUFFIX,
    _split_trading_pair,
    kraken_ledgers,
    parse_kraken_ledgers,
)


def test_assets_and_staked_suffix() -> None:
    response = requests.get("https://api.kraken.com/0/public/Assets", timeout=10)

    if response:
        for asset in response.json()["result"]:
            alt = response.json()["result"][asset]["altname"]

            if asset != alt:
                assert ALT_ASSETS[asset] == alt

            match = re.match(r"^[A-Z]+((?:\d{2})?\.\w+)$", asset)
            if match:
                staked_suffix = match.group(1)
                assert staked_suffix in STAKED_SUFFIX


def test_split_trading_pair() -> None:
    response = requests.get("https://api.kraken.com/0/public/AssetPairs", timeout=10)

    if response:
        for pair in response.json()["result"]:
            if response.json()["result"][pair].get("wsname"):
                if pair.endswith(response.json()["result"][pair]["quote"]):
                    quote = response.json()["result"][pair]["quote"]
                else:
                    quote = response.json()["result"][pair]["wsname"].split("/")[1]

                assert quote in QUOTE_ASSETS

                bt_base, bt_quote = _split_trading_pair(pair)

                wsname = response.json()["result"][pair]["wsname"]
                base = response.json()["result"][pair]["base"]
                quote = response.json()["result"][pair]["quote"]

                assert bt_base is not None
                assert bt_quote is not None

                assert bt_base + "/" + bt_quote == wsname or bt_base == base and bt_quote == quote


def test_parse_kraken_earn_airdrop() -> None:
    data_row = DataRow(
        1,
        [
            "txid-1",
            "refid-1",
            "2024-01-01 12:00:00",
            "earn",
            "airdrop",
            "currency",
            "",
            "FLR",
            "spot / main",
            "100",
            "0",
            "100",
        ],
        kraken_ledgers.in_header,
        "Kraken L",
    )

    parse_kraken_ledgers([data_row], kraken_ledgers)

    assert str(data_row.t_record) == "Airdrop 100 FLR 'Kraken' 2024-01-01T12:00:00 UTC "
    assert data_row.t_record is not None
    assert data_row.t_record.t_type == TrType.AIRDROP
    assert data_row.t_record.buy_quantity == Decimal("100")
    assert data_row.t_record.buy_asset == "FLR"
