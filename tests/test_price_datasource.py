# pylint: disable=protected-access

from datetime import datetime
from typing import Dict, List, Optional, Type
from unittest.mock import Mock, call

import pytest
import requests
from requests.structures import CaseInsensitiveDict

from bittytax.bt_types import AssetSymbol, QuoteSymbol, Timestamp
from bittytax.config import config
from bittytax.price.datasource import (
    BittyTaxAPI,
    CoinGecko,
    CoinPaprika,
    CoinStats,
    CryptoCompare,
    DataSourceBase,
)
from bittytax.price.exceptions import DataSourceApiError


@pytest.mark.parametrize("api_key", [None, "", "test-key"])
def test_bittytax_api_authenticates_initial_request(
    monkeypatch: pytest.MonkeyPatch, api_key: Optional[str]
) -> None:
    if api_key is None:
        monkeypatch.delitem(config.config, "bittytax_api_key", raising=False)
    else:
        monkeypatch.setitem(config.config, "bittytax_api_key", api_key)
    monkeypatch.setattr(BittyTaxAPI, "_load_assets", lambda self: None)
    monkeypatch.setattr(BittyTaxAPI, "_load_prices", lambda self: None)
    monkeypatch.setattr(BittyTaxAPI, "_save_assets", lambda self: None)
    monkeypatch.setattr(BittyTaxAPI, "_rate_limit", lambda self: None)
    response = Mock(status_code=200)
    response.json.return_value = {"symbols": {}}
    session = Mock()
    session.get.return_value = response
    monkeypatch.setattr(BittyTaxAPI, "_get_session", lambda self: session)

    BittyTaxAPI()

    headers = session.get.call_args.kwargs["headers"]
    assert headers.get("Authorization") == (f"Bearer {api_key}" if api_key is not None else None)
    assert "test-key" not in session.get.call_args.args[0]


def test_bittytax_api_root_is_used_for_all_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(BittyTaxAPI, "API_ROOT", "http://localhost:5000")
    monkeypatch.setattr(BittyTaxAPI, "_load_assets", lambda self: None)
    monkeypatch.setattr(BittyTaxAPI, "_load_prices", lambda self: None)
    monkeypatch.setattr(BittyTaxAPI, "_save_assets", lambda self: None)
    request = Mock(side_effect=[{"symbols": {}}, {"rates": {"GBP": 1}}, {"rates": {"GBP": 1}}])
    monkeypatch.setattr(BittyTaxAPI, "_get_json", request)
    monkeypatch.setattr(BittyTaxAPI, "_update_prices", Mock())
    source = BittyTaxAPI()
    source.get_latest(AssetSymbol("USD"), QuoteSymbol("GBP"))
    source.get_historical(AssetSymbol("USD"), QuoteSymbol("GBP"), Timestamp(datetime(2024, 1, 15)))
    assert request.call_args_list == [
        call("http://localhost:5000/v1/symbols"),
        call("http://localhost:5000/v1/latest?base=USD&symbols=GBP"),
        call("http://localhost:5000/v1/2024-01-15?base=USD&symbols=GBP"),
    ]


def test_cryptocompare_uses_bittytax_api_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(BittyTaxAPI, "API_ROOT", "http://localhost:5000")
    monkeypatch.setattr(CryptoCompare, "_load_ids", lambda self: None)
    monkeypatch.setattr(CryptoCompare, "_save_ids", lambda self: None)
    monkeypatch.setattr(CryptoCompare, "_load_prices", lambda self: None)
    monkeypatch.setattr(CryptoCompare, "_get_config_assets", lambda self: None)
    request = Mock(return_value={"Response": "Success", "Data": {}})
    monkeypatch.setattr(CryptoCompare, "_get_json", request)

    CryptoCompare()

    request.assert_called_once_with("http://localhost:5000/v1/ext/cc")


@pytest.fixture(name="api_source")
def make_api_source(monkeypatch: pytest.MonkeyPatch) -> BittyTaxAPI:
    monkeypatch.delitem(config.config, "bittytax_api_key", raising=False)
    monkeypatch.setattr(BittyTaxAPI, "_load_assets", lambda self: {})
    monkeypatch.setattr(BittyTaxAPI, "_load_prices", lambda self: None)
    return BittyTaxAPI()


def make_response(status: int = 200, headers: Optional[Dict[str, str]] = None) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.headers = CaseInsensitiveDict(headers or {})
    response._content = b'{"success": true}'
    return response


@pytest.mark.parametrize("limit", ["", "0", "-1", "bad"])
def test_missing_or_invalid_minute_limit_uses_anonymous_fallback(
    api_source: BittyTaxAPI, limit: str
) -> None:
    api_source._handle_response(make_response(headers={"X-RateLimit-Limit-Minute": "300"}), "")
    api_source._handle_response(make_response(headers={"X-RateLimit-Limit-Minute": limit}), "")
    assert api_source.rate_limit == 100 / 60


def test_minute_limits_are_instance_scoped(api_source: BittyTaxAPI) -> None:
    second = BittyTaxAPI()
    api_source._handle_response(make_response(headers={"x-ratelimit-limit-minute": "300"}), "")
    assert api_source.rate_limit == 5
    assert second.rate_limit == 100 / 60
    assert BittyTaxAPI.RATE_LIMIT == 100 / 60
    api_source._handle_response(make_response(), "")
    assert api_source.rate_limit == 100 / 60


def test_response_limit_controls_next_request_pacing(
    api_source: BittyTaxAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("bittytax.price.datasource.time.time", lambda: 1000.0)
    waits: List[float] = []
    monkeypatch.setattr("bittytax.price.datasource.time.sleep", waits.append)
    session = Mock()
    session.get.return_value = make_response(
        headers={
            "X-RateLimit-Limit-Minute": "300",
            "X-RateLimit-Remaining-Minute": "0",
            "X-RateLimit-Reset-Minute": "1100",
        }
    )
    monkeypatch.setattr(api_source, "_get_session", lambda: session)
    api_source._get_json("https://api.bitty.tax/v1/symbols")
    api_source._get_json("https://api.bitty.tax/v1/symbols")
    assert waits == [pytest.approx(0.25)]


@pytest.mark.parametrize("retry_after,expected", [("12", 12), ("bad", 5), (None, 5)])
def test_minute_429_uses_retry_after(
    api_source: BittyTaxAPI,
    monkeypatch: pytest.MonkeyPatch,
    retry_after: Optional[str],
    expected: int,
) -> None:
    monkeypatch.setattr(api_source, "_rate_limit", lambda: None)
    retry = Mock(return_value=True)
    monkeypatch.setattr(api_source, "_retry", retry)
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    session = Mock()
    session.get.side_effect = [make_response(429, headers=headers), make_response()]
    monkeypatch.setattr(api_source, "_get_session", lambda: session)
    assert api_source._get_json("https://api.bitty.tax/v1/symbols") == {"success": True}
    retry.assert_called_once_with(0, expected)


def test_other_sources_keep_existing_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    source = DataSourceBase()
    monkeypatch.setattr(source, "_rate_limit", lambda: None)
    session = Mock()
    session.get.return_value = make_response(headers={"X-RateLimit-Limit-Minute": "300"})
    monkeypatch.setattr(source, "_get_session", lambda: session)
    assert source._get_json("https://example.com") == {"success": True}
    assert source.rate_limit == 5


@pytest.mark.parametrize(
    "source_class,key,expected",
    [
        (CoinGecko, None, 2),
        (CoinGecko, "coingecko_demo_api_key", 2),
        (CoinGecko, "coingecko_pro_api_key", 20),
        (CoinPaprika, None, 2),
        (CoinPaprika, "coinpaprika_api_key", 20),
    ],
)
def test_provider_configured_rate_is_instance_scoped(
    monkeypatch: pytest.MonkeyPatch,
    source_class: Type[DataSourceBase],
    key: Optional[str],
    expected: int,
) -> None:
    for name in ("coingecko_pro_api_key", "coingecko_demo_api_key", "coinpaprika_api_key"):
        monkeypatch.delitem(config.config, name, raising=False)
    monkeypatch.setitem(config.config, "data_source_select", {})
    if key:
        monkeypatch.setitem(config.config, key, "test-key")
    monkeypatch.setattr(source_class, "_load_ids", lambda self: {})
    monkeypatch.setattr(source_class, "_load_prices", lambda self: None)
    source = source_class()
    assert source.rate_limit == expected
    assert source_class.RATE_LIMIT == DataSourceBase.RATE_LIMIT


def test_provider_class_default_initializes_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(config.config, "coinstats_api_key", raising=False)
    assert CoinStats().rate_limit == CoinStats.RATE_LIMIT == 2


@pytest.mark.parametrize("reset", [None, "2027-01-01T00:00:00+00:00"])
def test_monthly_429_fails_without_retry(
    api_source: BittyTaxAPI, monkeypatch: pytest.MonkeyPatch, reset: Optional[str]
) -> None:
    monkeypatch.setattr(api_source, "_rate_limit", lambda: None)
    retry = Mock()
    monkeypatch.setattr(api_source, "_retry", retry)
    headers = {"X-RateLimit-Remaining-Month": "0"}
    if reset:
        headers["X-RateLimit-Reset-Month"] = reset
    session = Mock()
    session.get.return_value = make_response(429, headers=headers)
    monkeypatch.setattr(api_source, "_get_session", lambda: session)
    with pytest.raises(DataSourceApiError, match="monthly rate limit exceeded") as error:
        api_source._get_json("https://api.bitty.tax/v1/symbols")
    if reset:
        assert reset in str(error.value)
    assert session.get.call_count == 1
    retry.assert_not_called()


def test_headerless_429_uses_shared_retries(
    api_source: BittyTaxAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api_source, "_rate_limit", lambda: None)
    waits: List[float] = []
    monkeypatch.setattr(
        api_source, "_countdown_sleep", lambda _label, duration: waits.append(duration)
    )
    response = make_response(429)
    response._content = b'{"error": "Monthly rate limit exceeded"}'
    session = Mock()
    session.get.return_value = response
    monkeypatch.setattr(api_source, "_get_session", lambda: session)
    with pytest.raises(DataSourceApiError, match="HTTP 429"):
        api_source._get_json("https://api.bitty.tax/v1/symbols")
    assert session.get.call_count == 1 + api_source.RETRIES
    assert waits == [5, 5, 5]


def test_success_with_no_monthly_remaining_is_returned(
    api_source: BittyTaxAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api_source, "_rate_limit", lambda: None)
    session = Mock()
    session.get.return_value = make_response(headers={"X-RateLimit-Remaining-Month": "0"})
    monkeypatch.setattr(api_source, "_get_session", lambda: session)
    assert api_source._get_json("https://api.bitty.tax/v1/symbols") == {"success": True}


def test_anonymous_pacing_and_debug_output(
    api_source: BittyTaxAPI, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(config, "debug", True)
    monkeypatch.setattr("bittytax.price.datasource.time.time", lambda: 1000.0)
    waits: List[float] = []
    monkeypatch.setattr("bittytax.price.datasource.time.sleep", waits.append)
    api_source.last_request_time = 1000.0
    api_source.headers["Authorization"] = "Bearer secret-key"
    session = Mock()
    session.get.return_value = make_response()
    monkeypatch.setattr(api_source, "_get_session", lambda: session)
    api_source._get_json("https://api.bitty.tax/v1/symbols")
    assert waits == [pytest.approx(0.65)]
    assert "secret-key" not in capsys.readouterr().out
