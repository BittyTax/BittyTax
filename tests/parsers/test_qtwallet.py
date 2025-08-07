import datetime
import io
from decimal import Decimal

import pytest
from dateutil.tz import tzutc

from bittytax.bt_types import TrType
from bittytax.config import config
from bittytax.conv.dataparser import DataParser
from bittytax.conv.datarow import DataRow
from bittytax.conv.exceptions import UnknownCryptoassetError
from bittytax.conv.parsers.qtwallet import _get_amount, parse_qt_wallet

config.ccy = "GBP"
config.config["local_timezone"] = "Europe/London"
config.config["date_is_day_first"] = True

# Priority for identifying the asset symbol name
# 1. Row, i.e. "0.00178181 BTC"
# 2. Header, i.e. "Amount (BTC)"
# 3. Argument, i.e. -ca BTC

row_deposit = [
    "true",
    "2019-01-03T16:40:36",
    "Received with",
    "Referral",
    "12AYsPD6z5KBadDgtCDFQVpGNwRi5RTCrG",
    "0.00178181",
    "ec26e177814a7c59e1bb2985777a2cdbd20fad06a23f5731abc031147031f6ce",
]

row_deposit_unconfirmed = [
    "false",
    "2019-01-03T16:40:36",
    "Received with",
    "Referral",
    "12AYsPD6z5KBadDgtCDFQVpGNwRi5RTCrG",
    "0.00178181",
    "ec26e177814a7c59e1bb2985777a2cdbd20fad06a23f5731abc031147031f6ce",
]

row_deposit_with_symbol = [
    "true",
    "2019-01-03T16:40:36",
    "Received with",
    "Referral",
    "12AYsPD6z5KBadDgtCDFQVpGNwRi5RTCrG",
    "0.00178181 WDC",
    "ec26e177814a7c59e1bb2985777a2cdbd20fad06a23f5731abc031147031f6ce",
]


def test_parser() -> None:
    parser = DataParser.match_header(
        ["Confirmed", "Date", "Type", "Label", "Address", "Amount (BTC)", "ID"], 0
    )
    assert parser.all_handler is parse_qt_wallet
    assert parser.args[0].group(2) == "BTC"

    data_row = DataRow(
        1,
        row_deposit,
        parser.in_header,
        "Qt Wallet",
    )

    parse_qt_wallet([data_row], parser, unconfirmed=False, cryptoasset="")

    assert (
        str(data_row.t_record)
        == "Deposit 0.00178181 BTC 'Qt Wallet' 2019-01-03T16:40:36 UTC 'Referral'"
    )

    assert str(data_row.timestamp) == "2019-01-03 16:40:36+00:00"
    assert data_row.timestamp == datetime.datetime(2019, 1, 3, 16, 40, 36, tzinfo=tzutc())

    assert data_row.t_record is not None
    assert data_row.t_record.t_type == TrType.DEPOSIT
    assert data_row.t_record.timestamp == data_row.timestamp
    assert data_row.t_record.buy_quantity == Decimal("0.00178181")
    assert data_row.t_record.buy_asset == "BTC"
    assert data_row.t_record.buy_value is None
    assert data_row.t_record.sell_quantity is None
    assert data_row.t_record.sell_asset == ""
    assert data_row.t_record.sell_value is None
    assert data_row.t_record.fee_quantity is None
    assert data_row.t_record.fee_asset == ""
    assert data_row.t_record.fee_value is None
    assert data_row.t_record.wallet == "Qt Wallet"
    assert data_row.t_record.note == "Referral"


def test_parse_qt_wallet_header_contains_symbol() -> None:
    parser = DataParser.match_header(
        ["Confirmed", "Date", "Type", "Label", "Address", "Amount (LTC)", "ID"], 0
    )
    assert parser.all_handler is parse_qt_wallet
    assert parser.args[0].group(2) == "LTC"

    data_row = DataRow(1, row_deposit, parser.in_header, "Qt Wallet")

    parse_qt_wallet(
        [data_row], parser, unconfirmed=False, cryptoasset="FTC", filename="qtwallet.csv"
    )

    assert (
        str(data_row.t_record)
        == "Deposit 0.00178181 LTC 'Qt Wallet' 2019-01-03T16:40:36 UTC 'Referral'"
    )


def test_parse_qt_wallet_row_contains_symbol() -> None:
    parser = DataParser.match_header(
        ["Confirmed", "Date", "Type", "Label", "Address", "Amount (LTC)", "ID"], 0
    )
    assert parser.all_handler is parse_qt_wallet
    assert parser.args[0].group(2) == "LTC"

    data_row = DataRow(1, row_deposit_with_symbol, parser.in_header, "Qt Wallet")

    parse_qt_wallet(
        [data_row], parser, unconfirmed=False, cryptoasset="FTC", filename="qtwallet.csv"
    )

    assert (
        str(data_row.t_record)
        == "Deposit 0.00178181 WDC 'Qt Wallet' 2019-01-03T16:40:36 UTC 'Referral'"
    )


def test_parse_qt_wallet_header_no_symbol_no_input(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = DataParser.match_header(
        ["Confirmed", "Date", "Type", "Label", "Address", "Amount", "ID"], 0
    )
    assert parser.all_handler is parse_qt_wallet
    assert not parser.args

    data_row = DataRow(1, row_deposit, parser.in_header, "Qt Wallet")

    monkeypatch.setattr("sys.stdin", io.StringIO("\n"))

    with pytest.raises(UnknownCryptoassetError):
        parse_qt_wallet(
            [data_row], parser, unconfirmed=False, cryptoasset="", filename="qtwallet.csv"
        )


def test_parse_qt_wallet_header_no_symbol_symbol_input(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = DataParser.match_header(
        ["Confirmed", "Date", "Type", "Label", "Address", "Amount", "ID"], 0
    )
    assert parser.all_handler is parse_qt_wallet
    assert not parser.args

    data_row = DataRow(1, row_deposit, parser.in_header, "Qt Wallet")

    monkeypatch.setattr("sys.stdin", io.StringIO("DOGE\n"))

    parse_qt_wallet([data_row], parser, unconfirmed=False, cryptoasset="", filename="qtwallet.csv")

    assert (
        str(data_row.t_record)
        == "Deposit 0.00178181 DOGE 'Qt Wallet' 2019-01-03T16:40:36 UTC 'Referral'"
    )


def test_parse_qt_wallet_header_no_symbol_crytoasset_specified() -> None:
    parser = DataParser.match_header(
        ["Confirmed", "Date", "Type", "Label", "Address", "Amount", "ID"], 0
    )
    assert parser.all_handler is parse_qt_wallet
    assert not parser.args

    data_row = DataRow(1, row_deposit, parser.in_header, "Qt Wallet")

    parse_qt_wallet(
        [data_row], parser, unconfirmed=False, cryptoasset="FTC", filename="qtwallet.csv"
    )

    assert (
        str(data_row.t_record)
        == "Deposit 0.00178181 FTC 'Qt Wallet' 2019-01-03T16:40:36 UTC 'Referral'"
    )


def test_func_get_amount_positive() -> None:
    amount, symbol = _get_amount("1.00000000 BTC")

    assert amount == Decimal("1") and symbol == "BTC"


def test_func_get_amount_negative() -> None:
    amount, symbol = _get_amount("-1.00000000 BTC")

    assert amount == Decimal("-1") and symbol == "BTC"
