from decimal import Decimal
from re import match
from typing import Optional, Tuple

# Constants
PRECISION = Decimal("0." + "0" * 8)

WALLET = "Binance"

# These constants are used by the sub-modules
QUOTE_ASSETS = [
    "AEUR",
    "ARS",
    "AUD",
    "BIDR",
    "BKRW",
    "BNB",
    "BRL",
    "BTC",
    "BUSD",
    "BVND",
    "COP",
    "CZK",
    "DAI",
    "DOGE",
    "DOT",
    "ETH",
    "EUR",
    "EURI",
    "FDUSD",
    "GBP",
    "GYEN",
    "IDRT",
    "JPY",
    "MXN",
    "NGN",
    "PAX",
    "PLN",
    "RON",
    "RUB",
    "SOL",
    "TRX",
    "TRY",
    "TUSD",
    "UAH",
    "USDC",
    "USDP",
    "USDS",
    "USDT",
    "UST",
    "VAI",
    "XMR",
    "XRP",
    "ZAR",
]

BASE_ASSETS = [
    "1000CAT",
    "1000CHEEMS",
    "1000SATS",
    "1INCH",
    "1INCHDOWN",
    "1INCHUP",
    "1MBABYDOGE",
]

TRADINGPAIR_TO_QUOTE_ASSET = {
    "ADAEUR": "EUR",
    "ENAEUR": "EUR",
    "GALAEUR": "EUR",
    "LUNAEUR": "EUR",
    "THETAEUR": "EUR",
}


def split_trading_pair(trading_pair: str) -> Tuple[Optional[str], Optional[str]]:
    if trading_pair in TRADINGPAIR_TO_QUOTE_ASSET:
        quote_asset = TRADINGPAIR_TO_QUOTE_ASSET[trading_pair]
        base_asset = trading_pair[: -len(quote_asset)]
        return base_asset, quote_asset

    for quote_asset in QUOTE_ASSETS:
        if trading_pair.endswith(quote_asset):
            return trading_pair[: -len(quote_asset)], quote_asset

    return None, None


def split_asset(amount: str) -> Tuple[Optional[Decimal], str]:
    for base_asset in BASE_ASSETS:
        if amount.endswith(base_asset):
            return Decimal(amount[: -len(base_asset)]), base_asset

    match_res = match(r"(\d+|\d+\.\d+)(\w+)$", amount)

    if match_res:
        return Decimal(match_res.group(1)), match_res.group(2)

    raise RuntimeError(f"Cannot split Quantity from Asset: {amount}")


def get_timestamp(timestamp: str) -> str:
    match_res = match(r"^\d{2}-\d{2}-\d{2}.*$", timestamp)

    if match_res:
        return f"20{timestamp}"

    return timestamp
