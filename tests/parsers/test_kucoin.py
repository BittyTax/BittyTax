from decimal import Decimal

import requests

from bittytax.bt_types import TrType
from bittytax.conv.dataparser import DataParser
from bittytax.conv.datarow import DataRow
from bittytax.conv.parsers.kucoin import _get_asset_from_symbol, parse_kucoin_trades_v5


def test_get_asset_from_symbol() -> None:
    response = requests.get("https://api-futures.kucoin.com/api/v1/contracts/active", timeout=10)

    if response:
        for data in response.json()["data"]:
            symbol = data["symbol"]
            settle_currency = data["settleCurrency"]

            asset = _get_asset_from_symbol(symbol)

            if asset == "BTC":
                asset = "XBT"

            assert asset == settle_currency


def test_spot_filled_orders_with_account_mode() -> None:
    # KuCoin added a trailing "Account Mode" column to Spot Orders exports, which
    # is matched by a dedicated fixed-header parser alongside the legacy format.
    header = [
        "UID",
        "Account Type",
        "Order ID",
        "Order Time(UTC+01:00)",
        "Symbol",
        "Side",
        "Order Type",
        "Order Price",
        "Order Amount",
        "Avg. Filled Price",
        "Filled Amount",
        "Filled Volume",
        "Filled Volume (USDT)",
        "Filled Time(UTC+01:00)",
        "Fee",
        "Fee Currency",
        "Tax",
        "Status",
        "Account Mode",
    ]
    parser = DataParser.match_header(header, 0)

    assert parser.name == "KuCoin Trades"
    assert parser.row_handler is parse_kucoin_trades_v5

    row = [
        "28896117",
        "mainAccount",
        "65ba511276bd0500070149bd",
        "2024-01-31 14:54:26",
        "DAG-USDT",
        "SELL",
        "LIMIT",
        "0.051",
        "1045079.6954",
        "0.05102902815692303434",
        "174196.5908",
        "8889.0827367732",
        "8889.0827367732",
        "2024-01-31 14:55:54",
        "8.8890827367732",
        "USDT",
        "",
        "part_deal",
        "CLASSIC",
    ]
    data_row = DataRow(1, row, parser.in_header, "KuCoin T")
    parse_kucoin_trades_v5(data_row, parser)

    assert data_row.t_record is not None
    assert data_row.t_record.t_type == TrType.TRADE
    assert data_row.t_record.buy_quantity == Decimal("8889.0827367732")
    assert data_row.t_record.buy_asset == "USDT"
    assert data_row.t_record.sell_quantity == Decimal("174196.5908")
    assert data_row.t_record.sell_asset == "DAG"
    assert data_row.t_record.fee_quantity == Decimal("8.8890827367732")
    assert data_row.t_record.fee_asset == "USDT"
    assert data_row.t_record.wallet == "KuCoin"


def test_spot_filled_orders_order_splitting_with_account_mode() -> None:
    # Order-splitting export variant, also with the trailing "Account Mode" column.
    header = [
        "UID",
        "Account Type",
        "Order ID",
        "Symbol",
        "Side",
        "Order Type",
        "Avg. Filled Price",
        "Filled Amount",
        "Filled Volume",
        "Filled Volume (USDT)",
        "Filled Time(UTC+01:00)",
        "Fee",
        "Tax",
        "Maker/Taker",
        "Fee Currency",
        "Account Mode",
    ]
    parser = DataParser.match_header(header, 0)

    assert parser.name == "KuCoin Trades"
    assert parser.row_handler is parse_kucoin_trades_v5

    row = [
        "28896117",
        "mainAccount",
        "65ba511276bd0500070149bd",
        "DAG-USDT",
        "SELL",
        "LIMIT",
        "0.051",
        "383.9201",
        "19.5799251",
        "19.5799251",
        "2024-01-31 14:54:26",
        "0.0195799251",
        "",
        "MAKER",
        "USDT",
        "CLASSIC",
    ]
    data_row = DataRow(1, row, parser.in_header, "KuCoin T")
    parse_kucoin_trades_v5(data_row, parser)

    assert data_row.t_record is not None
    assert data_row.t_record.t_type == TrType.TRADE
    assert data_row.t_record.buy_quantity == Decimal("19.5799251")
    assert data_row.t_record.buy_asset == "USDT"
    assert data_row.t_record.sell_quantity == Decimal("383.9201")
    assert data_row.t_record.sell_asset == "DAG"
    assert data_row.t_record.fee_quantity == Decimal("0.0195799251")
    assert data_row.t_record.fee_asset == "USDT"
    assert data_row.t_record.wallet == "KuCoin"
