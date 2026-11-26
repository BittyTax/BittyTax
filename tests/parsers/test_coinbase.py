from decimal import Decimal
from types import SimpleNamespace
from typing import Callable, List, Optional

import pytest

from bittytax.bt_types import TrType
from bittytax.config import config
from bittytax.conv.dataparser import DataParser
from bittytax.conv.datarow import DataRow, TxRawPos
from bittytax.conv.parsers import coinbase

HEADER = [
    "ID",
    "Timestamp",
    "Transaction Type",
    "Asset",
    "Quantity Transacted",
    "Price Currency",
    "Price at Transaction",
    "Subtotal",
    "Total (inclusive of fees and/or spread)",
    "Fees and/or Spread",
    "Notes",
]


def test_parser_accepts_sender_and_recipient_addresses() -> None:
    header = HEADER + ["Sender Address", "Recipient Address"]
    parser = DataParser.match_header(header, 0)

    assert parser.all_handler is coinbase.parse_coinbase_v4
    assert parser.header == header
    assert parser.header_fixed
    assert parser.newest_first

    with pytest.raises(KeyError):
        DataParser.match_header(header + ["Unexpected"], 0)


@pytest.mark.parametrize(
    ("header", "handler"),
    [
        (HEADER, coinbase.parse_coinbase_v4),
        (HEADER[1:], coinbase.parse_coinbase_v4),
        (
            HEADER[1:5] + ["Spot Price Currency", "Spot Price at Transaction"] + HEADER[7:],
            coinbase.parse_coinbase_v3,
        ),
        (
            HEADER[1:5]
            + ["Spot Price Currency", "Spot Price at Transaction", "Subtotal"]
            + ["Total (inclusive of fees)", "Fees", "Notes"],
            coinbase.parse_coinbase_v2,
        ),
        (
            HEADER[1:5]
            + [
                "GBP Spot Price at Transaction",
                "GBP Subtotal",
                "GBP Total (inclusive of fees)",
                "GBP Fees",
                "Notes",
            ],
            coinbase.parse_coinbase_v1,
        ),
    ],
)
def test_legacy_headers_remain_fixed(header: List[str], handler: Callable[..., None]) -> None:
    parser = DataParser.match_header(header, 0)

    assert parser.all_handler is handler
    assert parser.header_fixed


@pytest.mark.parametrize("tx_type", ["Receive", "Send", "Retail MGX DEX Send"])
def test_address_columns_are_preserved(monkeypatch: pytest.MonkeyPatch, tx_type: str) -> None:
    monkeypatch.setattr(config, "ccy", "GBP")
    header = HEADER + ["Sender Address", "Recipient Address"]
    parser = DataParser.match_header(header, 0)
    row = DataRow(
        1,
        [
            "id",
            "2025-11-24 03:41:09 UTC",
            tx_type,
            "BTC",
            "1",
            "GBP",
            "£100",
            "£100",
            "£100",
            "£0",
            "legacy note",
            "sender",
            "recipient",
        ],
        header,
        "Coinbase",
    )

    DataRow.parse_all([row], parser)

    assert row.failure is None
    assert row.t_record is not None
    assert row.tx_raw == TxRawPos(tx_src_pos=11, tx_dest_pos=12)


@pytest.mark.parametrize("tx_type", ["Send", "Retail MGX DEX Send"])
def test_legacy_send_uses_notes_for_destination(
    monkeypatch: pytest.MonkeyPatch, tx_type: str
) -> None:
    monkeypatch.setattr(config, "ccy", "GBP")
    parser = DataParser.match_header(HEADER, 0)
    row = DataRow(
        1,
        [
            "id",
            "2025-11-24 03:41:09 UTC",
            tx_type,
            "BTC",
            "-1",
            "GBP",
            "£100",
            "£100",
            "£100",
            "£0",
            "legacy destination",
        ],
        HEADER,
        "Coinbase",
    )

    DataRow.parse_all([row], parser)

    assert row.failure is None
    assert row.t_record is not None
    assert row.tx_raw == TxRawPos(tx_dest_pos=10)


@pytest.mark.parametrize("quantity", ["100", "-100"])
def test_raise_offering_deposit_is_skipped(monkeypatch: pytest.MonkeyPatch, quantity: str) -> None:
    monkeypatch.setattr(config, "ccy", "GBP")
    parser = DataParser.match_header(HEADER, 0)
    row = DataRow(
        1,
        [
            "id",
            "2025-11-18 13:42:22 UTC",
            "Raise Offering Deposit",
            "USDC",
            quantity,
            "GBP",
            "£0.760516",
            "£76.05160",
            "£76.07061",
            "£0.0190129",
            "",
        ],
        HEADER,
        "Coinbase",
    )

    DataRow.parse_all([row], parser)

    assert row.failure is None
    assert row.t_record is None


@pytest.mark.parametrize("reverse", [False, True])
def test_raise_offering_trade(monkeypatch: pytest.MonkeyPatch, reverse: bool) -> None:
    monkeypatch.setattr(config, "ccy", "GBP")
    header = HEADER + ["Sender Address", "Recipient Address"]
    parser = DataParser.match_header(header, 0)
    distribution_row = DataRow(
        1,
        [
            "id",
            "2025-11-24 03:41:09 UTC",
            "Raise Offering Distribution",
            "MON",
            "4000",
            "GBP",
            "£0.0190901",
            "£86.74541",
            "£86.74541",
            "£0.00",
            "",
            "",
            "",
        ],
        header,
        "Coinbase",
    )
    pooling_row = DataRow(
        2,
        [
            "id",
            "2025-11-24 03:41:09 UTC",
            "Raise Offering Pooling",
            "USDC",
            "-100",
            "GBP",
            "£0.763604",
            "£86.74541",
            "£86.74541",
            "£0.00",
            "",
            "",
            "",
        ],
        header,
        "Coinbase",
    )
    rows = [pooling_row, distribution_row] if reverse else [distribution_row, pooling_row]
    DataRow.parse_all(rows, parser)

    assert distribution_row.parsed
    assert pooling_row.parsed
    assert all(row.failure is None for row in rows)
    record = rows[0].t_record
    assert record is not None
    assert rows[1].t_record is None
    assert record.t_type == TrType.TRADE
    assert record.buy_quantity == Decimal("4000")
    assert record.buy_asset == "MON"
    assert record.sell_quantity == Decimal("100")
    assert record.sell_asset == "USDC"
    assert record.buy_value == Decimal("76.3604")
    assert record.sell_value == Decimal("76.3604")


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(("currency", "rate"), [("GBP", "1"), ("USD", "0.75")])
def test_retail_mgx_dex_buy_values_use_transaction_prices(
    monkeypatch: pytest.MonkeyPatch, reverse: bool, currency: str, rate: str
) -> None:
    monkeypatch.setattr(config, "ccy", "GBP")
    monkeypatch.setattr(
        DataParser.price_data,
        "get_historical",
        lambda *_args: SimpleNamespace(price_ccy=Decimal(rate)),
    )
    parser = DataParser.match_header(HEADER, 0)
    buy = DataRow(
        1,
        [
            "id1",
            "2025-11-24 03:41:09 UTC",
            "Retail MGX DEX Buy",
            "ETH",
            "2",
            currency,
            "1,200.50",
            "2500",
            "2500",
            "0",
            "",
        ],
        HEADER,
        "Coinbase",
    )
    sell = DataRow(
        2,
        [
            "id2",
            "2025-11-24 03:41:09 UTC",
            "Retail MGX DEX Buy",
            "USDC",
            "-3000",
            currency,
            "0.80",
            "2500",
            "2500",
            "3",
            "",
        ],
        HEADER,
        "Coinbase",
    )
    rows = [sell, buy] if reverse else [buy, sell]

    DataRow.parse_all(rows, parser)

    assert all(row.failure is None and row.parsed for row in rows)
    record = rows[0].t_record
    assert record is not None
    assert rows[1].t_record is None
    assert record.t_type == TrType.TRADE
    assert record.buy_quantity == Decimal("2")
    assert record.buy_asset == "ETH"
    assert record.buy_value == Decimal("2401.00") * Decimal(rate)
    assert record.sell_quantity == Decimal("3000")
    assert record.sell_asset == "USDC"
    assert record.sell_value == Decimal("2400") * Decimal(rate)
    assert record.fee_quantity == Decimal("3") * Decimal(rate)
    assert record.fee_asset == "GBP"


@pytest.mark.parametrize(("price", "expected"), [("", None), ("0", Decimal("0"))])
def test_trade_with_missing_or_zero_price(
    monkeypatch: pytest.MonkeyPatch, price: str, expected: Optional[Decimal]
) -> None:
    monkeypatch.setattr(config, "ccy", "GBP")
    parser = DataParser.match_header(HEADER, 0)
    buy = DataRow(
        1,
        [
            "id1",
            "2025-11-24 03:41:09 UTC",
            "Retail MGX DEX Buy",
            "ETH",
            "2",
            "GBP",
            price,
            "100",
            "100",
            "0",
            "",
        ],
        HEADER,
        "Coinbase",
    )
    sell = DataRow(
        2,
        [
            "id2",
            "2025-11-24 03:41:09 UTC",
            "Retail MGX DEX Buy",
            "USDC",
            "-100",
            "GBP",
            "1",
            "100",
            "100",
            "0",
            "",
        ],
        HEADER,
        "Coinbase",
    )

    DataRow.parse_all([buy, sell], parser)

    assert buy.failure is None
    assert sell.failure is None
    assert buy.t_record is not None
    assert buy.t_record.buy_value == expected
    assert buy.t_record.sell_value == Decimal("100")


@pytest.mark.parametrize(
    ("buy_type", "sell_type"),
    [
        ("Raise Offering Distribution", "Raise Offering Pooling"),
        ("Retail MGX DEX Buy", "Retail MGX DEX Buy"),
    ],
)
@pytest.mark.parametrize(
    ("header", "price_fields", "values"),
    [
        (HEADER, ["Price at Transaction"], ["id", "GBP", "0.0190901"]),
        (
            HEADER[1:5] + ["Spot Price Currency", "Spot Price at Transaction"] + HEADER[7:],
            ["Spot Price at Transaction"],
            ["GBP", "0.0190901"],
        ),
        (
            HEADER[1:5]
            + ["Spot Price Currency", "Spot Price at Transaction", "Subtotal"]
            + ["Total (inclusive of fees)", "Fees", "Notes"],
            ["Spot Price at Transaction"],
            ["GBP", "0.0190901"],
        ),
        (
            HEADER[1:5]
            + [
                "GBP Spot Price at Transaction",
                "GBP Subtotal",
                "GBP Total (inclusive of fees)",
                "GBP Fees",
                "Notes",
            ],
            ["GBP Spot Price at Transaction"],
            ["0.0190901"],
        ),
    ],
)
def test_trade_legacy_formats(
    monkeypatch: pytest.MonkeyPatch,
    header: List[str],
    price_fields: List[str],
    values: List[str],
    buy_type: str,
    sell_type: str,
) -> None:
    monkeypatch.setattr(config, "ccy", "GBP")
    parser = DataParser.match_header(header, 0)
    common = ["2025-11-24 03:41:09 UTC", buy_type, "MON", "4000"]
    prefix = values[:1] if header[0] == "ID" else []
    price = values[1:] if prefix else values
    distribution = DataRow(
        1, prefix + common + price + ["86.74541", "86.74541", "0", ""], header, "Coinbase"
    )
    pooling_values = list(distribution.row)
    pooling_values[header.index("Transaction Type")] = sell_type
    pooling_values[header.index("Asset")] = "USDC"
    pooling_values[header.index("Quantity Transacted")] = "-100"
    pooling_values[header.index(price_fields[0])] = "0.763604"
    pooling = DataRow(2, pooling_values, header, "Coinbase")

    DataRow.parse_all([distribution, pooling], parser)

    assert distribution.failure is None
    assert pooling.failure is None
    assert distribution.t_record is not None
    assert distribution.t_record.buy_value == Decimal("76.3604")
    assert distribution.t_record.sell_value == Decimal("76.3604")
    assert pooling.t_record is None
