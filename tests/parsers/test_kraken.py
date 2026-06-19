import re
from decimal import Decimal
from typing import List

import requests

from bittytax.bt_types import TrType
from bittytax.conv.dataparser import DataParser
from bittytax.conv.datarow import DataRow
from bittytax.conv.parsers.kraken import (
    ALT_ASSETS,
    QUOTE_ASSETS,
    STAKED_SUFFIX,
    _split_trading_pair,
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


# ---------------------------------------------------------------------------
# Offline Ledgers tests (no network) — exercise the all_handler directly.
# ---------------------------------------------------------------------------

LEDGERS_HEADER = [
    "txid",
    "refid",
    "time",
    "type",
    "subtype",
    "aclass",
    "subclass",
    "asset",
    "wallet",
    "amount",
    "fee",
    "balance",
]


def _ledger_row(
    txid: str,
    refid: str,
    type_: str,
    subtype: str,
    asset: str,
    amount: str,
    fee: str = "0",
    wallet: str = "spot / main",
) -> List[str]:
    return [
        txid,
        refid,
        "2024-01-01 12:00:00",
        type_,
        subtype,
        "currency",
        "crypto",
        asset,
        wallet,
        amount,
        fee,
        "0",
    ]


def _parse(rows: List[List[str]]) -> List[DataRow]:
    parser = DataParser.match_header(LEDGERS_HEADER, 0)
    assert parser.name == "Kraken Ledgers"
    data_rows = [DataRow(i + 1, row, parser.in_header, "Kraken L") for i, row in enumerate(rows)]
    parse_kraken_ledgers(data_rows, parser)
    return data_rows


def test_trade_multi_wallet_legs_are_summed() -> None:
    # A single order liquidating the same asset from both the spot and earn wallets
    # produces two same-side legs sharing a refid; they must be summed, not overwritten.
    data_rows = _parse(
        [
            _ledger_row(
                "L1", "R1", "trade", "tradespot", "ETH", "-29.8578433312", wallet="spot / main"
            ),
            _ledger_row(
                "L2",
                "R1",
                "trade",
                "tradespot",
                "ETH",
                "-1.5516119088",
                "0.0125637800",
                "earn / liquid",
            ),
            _ledger_row("L3", "R1", "trade", "tradespot", "XXBT", "1.0679214782"),
        ]
    )

    t_record = data_rows[0].t_record
    assert t_record is not None
    assert t_record.t_type == TrType.TRADE
    assert t_record.sell_quantity == Decimal("31.4094552400")  # 29.8578433312 + 1.5516119088
    assert t_record.sell_asset == "ETH"
    assert t_record.buy_quantity == Decimal("1.0679214782")
    assert t_record.buy_asset == "BTC"  # XXBT normalised
    assert t_record.fee_quantity == Decimal("0.0125637800")
    assert t_record.fee_asset == "ETH"
    assert t_record.wallet == "Kraken"


def test_trade_normal_two_legs_unchanged() -> None:
    # Regression: an ordinary two-leg trade with a fiat fee is unaffected.
    data_rows = _parse(
        [
            _ledger_row("L1", "R1", "trade", "tradespot", "ZEUR", "-100.0", "0.16"),
            _ledger_row("L2", "R1", "trade", "tradespot", "XXBT", "0.002"),
        ]
    )

    t_record = data_rows[0].t_record
    assert t_record is not None
    assert t_record.t_type == TrType.TRADE
    assert t_record.sell_quantity == Decimal("100.0")
    assert t_record.sell_asset == "EUR"
    assert t_record.buy_quantity == Decimal("0.002")
    assert t_record.buy_asset == "BTC"
    assert t_record.fee_quantity == Decimal("0.16")
    assert t_record.fee_asset == "EUR"


def test_delisting_conversion_legs_booked_per_leg() -> None:
    # Delisted-token forced conversions arrive as unpaired single legs: the sent leg is a
    # disposal (Spend), the received leg an acquisition (Airdrop).
    data_rows = _parse(
        [
            _ledger_row("L1", "R1", "transfer", "delistingconversion", "USDT", "-110.39461455"),
            _ledger_row("L2", "R2", "transfer", "delistingconversion", "USDC", "110.36149621"),
        ]
    )

    sent = data_rows[0].t_record
    assert sent is not None
    assert sent.t_type == TrType.SPEND
    assert sent.sell_quantity == Decimal("110.39461455")
    assert sent.sell_asset == "USDT"

    received = data_rows[1].t_record
    assert received is not None
    assert received.t_type == TrType.AIRDROP
    assert received.buy_quantity == Decimal("110.36149621")
    assert received.buy_asset == "USDC"


def test_trade_dust_orphan_is_dropped() -> None:
    # A one-sided sub-threshold trade row (rounding residue) is dropped, not emitted.
    data_rows = _parse([_ledger_row("L1", "R1", "trade", "tradespot", "ADA", "0.00006813")])
    assert data_rows[0].t_record is None
    assert data_rows[0].failure is None


def test_trade_kfee_fee_valued_in_usd() -> None:
    # A fee paid in Kraken fee credits ("FEE") is a zero-amount leg; it must be valued at
    # 0.01 USD per unit rather than against the unpriceable "FEE" asset.
    data_rows = _parse(
        [
            _ledger_row("L1", "R1", "trade", "tradespot", "ZEUR", "-384.9328"),
            _ledger_row("L2", "R1", "trade", "tradespot", "XXBT", "0.0092754900"),
            _ledger_row("L3", "R1", "trade", "tradespot", "FEE", "0.00", "46.50"),
        ]
    )

    trade = data_rows[0].t_record
    assert trade is not None
    assert trade.t_type == TrType.TRADE
    assert trade.sell_asset == "EUR"
    assert trade.buy_asset == "BTC"

    fee_record = data_rows[2].t_record
    assert fee_record is not None
    assert fee_record.t_type == TrType.SPEND
    assert fee_record.fee_quantity == Decimal("0.4650")  # 46.50 * 0.01
    assert fee_record.fee_asset == "USD"
    assert fee_record.note == "Trading fee"


def test_kfee_deposit_is_skipped() -> None:
    # Standalone deposits of fee credits are not a tradeable asset and are skipped.
    data_rows = _parse([_ledger_row("L1", "R1", "deposit", "", "FEE", "8000.00")])
    assert data_rows[0].t_record is None
    assert data_rows[0].failure is None


def test_earn_reward_is_staking_reward() -> None:
    data_rows = _parse(
        [
            _ledger_row("L1", "R1", "earn", "reward", "DOT", "0.5", wallet="earn / bonded"),
            _ledger_row("L2", "R2", "earn", "reward", "DOT", "-0.1", wallet="earn / bonded"),
        ]
    )

    reward = data_rows[0].t_record
    assert reward is not None
    assert reward.t_type == TrType.STAKING_REWARD
    assert reward.buy_quantity == Decimal("0.5")
    assert reward.buy_asset == "DOT"

    negative = data_rows[1].t_record
    assert negative is not None
    assert negative.t_type == TrType.SPEND
    assert negative.sell_quantity == Decimal("0.1")


def test_earn_allocation_is_skipped() -> None:
    data_rows = _parse(
        [_ledger_row("L1", "R1", "earn", "autoallocation", "BTC", "1.25", wallet="earn / liquid")]
    )
    assert data_rows[0].t_record is None
    assert data_rows[0].failure is None


def test_earn_airdrop_is_airdrop_not_income() -> None:
    # A Kraken Earn "airdrop" is a token distribution, not a staking reward: the received
    # leg is booked as Airdrop (acquisition, no income) and any sent leg as Spend. It must
    # not become a staking reward, which would overstate taxable income.
    data_rows = _parse(
        [
            _ledger_row("L1", "R1", "earn", "airdrop", "ETH", "0.25", wallet="earn / flexible"),
            _ledger_row("L2", "R2", "earn", "airdrop", "ETH", "-0.10", wallet="earn / flexible"),
        ]
    )

    received = data_rows[0].t_record
    assert received is not None
    assert received.t_type == TrType.AIRDROP
    assert received.buy_quantity == Decimal("0.25")
    assert received.buy_asset == "ETH"
    assert data_rows[0].failure is None

    sent = data_rows[1].t_record
    assert sent is not None
    assert sent.t_type == TrType.SPEND
    assert sent.sell_quantity == Decimal("0.10")
    # Proceeds are left to market pricing, not forced to zero.
    assert sent.sell_value is None


def test_earn_delisting_conversion_is_not_income() -> None:
    # A forced delisting conversion routed through Earn books per leg (received = Airdrop,
    # sent = Spend), never as a staking reward; the disposal is market-priced.
    data_rows = _parse(
        [
            _ledger_row(
                "L1",
                "R1",
                "earn",
                "delistingconversion",
                "MATIC",
                "-17.04",
                "0.05",
                "earn / liquid",
            ),
            _ledger_row(
                "L2", "R2", "earn", "delistingconversion", "POL", "17.04", wallet="earn / liquid"
            ),
        ]
    )

    sent = data_rows[0].t_record
    assert sent is not None
    assert sent.t_type == TrType.SPEND
    assert sent.sell_quantity == Decimal("17.04")
    assert sent.sell_asset == "MATIC"
    assert sent.sell_value is None
    # A fee on the row is preserved, not dropped.
    assert sent.fee_quantity == Decimal("0.05")
    assert sent.fee_asset == "MATIC"

    received = data_rows[1].t_record
    assert received is not None
    assert received.t_type == TrType.AIRDROP
    assert received.buy_quantity == Decimal("17.04")
    assert received.buy_asset == "POL"


def test_unknown_subtype_degrades_gracefully() -> None:
    # Unknown earn subtype defaults to income (does not raise); unknown transfer subtype
    # is skipped with a warning (also no failure).
    data_rows = _parse(
        [
            _ledger_row("L1", "R1", "earn", "superstake", "DOT", "0.5"),
            _ledger_row("L2", "R2", "transfer", "somethingnew", "BTC", "1.0"),
        ]
    )

    earn = data_rows[0].t_record
    assert earn is not None
    assert earn.t_type == TrType.STAKING_REWARD
    assert data_rows[0].failure is None

    assert data_rows[1].t_record is None
    assert data_rows[1].failure is None


def test_trade_mixed_assets_same_side_fails_loudly() -> None:
    # Defensive: two same-side legs with different assets must NOT be silently summed into
    # one quantity; the refid is flagged as a failure instead of producing a corrupt trade.
    data_rows = _parse(
        [
            _ledger_row("L1", "R1", "trade", "tradespot", "ETH", "-2.0000000000"),
            _ledger_row("L2", "R1", "trade", "tradespot", "SOL", "-3.0000000000"),
            _ledger_row("L3", "R1", "trade", "tradespot", "BTC", "0.1000000000"),
        ]
    )
    assert data_rows[0].t_record is None
    assert data_rows[0].failure is not None
