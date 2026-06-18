# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import copy
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ...constants import WARNING
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import (
    DataRowError,
    UnexpectedContentError,
    UnexpectedTradingPairError,
    UnexpectedTypeError,
)
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Kraken"

# Kraken fee credits (KFEE/"FEE") have a fixed value of 0.01 USD (1000 KFEE = 10 USD)
# and no market price of their own.
KFEE_USD_RATE = Decimal("0.01")

# One-sided trade rows below this quantity are rounding dust and are dropped.
DUST_THRESHOLD = Decimal("0.001")

QUOTE_ASSETS = [
    "AED",
    "AUD",
    "AUSD",
    "CAD",
    "CHF",
    "DAI",
    "DOT",
    "ETH",
    "EUR",
    "EURC",
    "EUROP",
    "FIDD",
    "GBP",
    "JPY",
    "POL",
    "PYUSD",
    "RLUSD",
    "SOL",
    "USD",
    "USD1",
    "USD:BTNL",
    "USDC",
    "USDD",
    "USDQ",
    "USDR",
    "USDT",
    "XBT",
    "XETH",
    "XXBT",
    "ZAUD",
    "ZCAD",
    "ZEUR",
    "ZGBP",
    "ZJPY",
    "ZUSD",
]

ALT_ASSETS = {
    "KFEE": "FEE",
    "XETC": "ETC",
    "XETH": "ETH",
    "XLTC": "LTC",
    "XMLN": "MLN",
    "XREP": "REP",
    "XXBT": "XBT",
    "XXDG": "XDG",
    "XXLM": "XLM",
    "XXMR": "XMR",
    "XXRP": "XRP",
    "XZEC": "ZEC",
    "ZARS": "ARS",
    "ZAUD": "AUD",
    "ZCAD": "CAD",
    "ZCLP": "CLP",
    "ZCOP": "COP",
    "ZDKK": "DKK",
    "ZEUR": "EUR",
    "ZGBP": "GBP",
    "ZGEL": "GEL",
    "ZGHS": "GHS",
    "ZJPY": "JPY",
    "ZLKR": "LKR",
    "ZMXN": "MXN",
    "ZPLN": "PLN",
    "ZSEK": "SEK",
    "ZUGX": "UGX",
    "ZUSD": "USD",
    "ZVND": "VND",
    "ZXOF": "XOF",
}

STAKED_SUFFIX = [
    ".HOLD",
    ".M",
    ".P",
    ".S",
    "03.S",
    "04.S",
    "07.S",
    "14.S",
    "21.S",
    "28.S",
]

TRADINGPAIR_TO_QUOTE_ASSET = {
    "2ZEUR": "EUR",
    "2ZUSD": "USD",
    "AI16ZEUR": "EUR",
    "AI16ZUSD": "USD",
    "AIOZEUR": "EUR",
    "AIOZUSD": "USD",
    "BLZEUR": "EUR",
    "BLZUSD": "USD",
    "CHZEUR": "EUR",
    "CHZUSD": "USD",
    "ETHPYUSD": "PYUSD",
    "ICXETH": "ETH",
    "ICXXBT": "XBT",
    "MONAUSD": "AUSD",
    "REZEUR": "EUR",
    "REZUSD": "USD",
    "SNXETH": "ETH",
    "SNXXBT": "XBT",
    "TRXETH": "ETH",
    "TRXXBT": "XBT",
    "XBTAUSD": "AUSD",
    "XBTPYUSD": "PYUSD",
    "XRPRLUSD": "RLUSD",
    "XTZAUD": "AUD",
    "XTZEUR": "EUR",
    "XTZGBP": "GBP",
    "XTZUSD": "USD",
    "ZRXXBT": "XBT",
}


def parse_kraken_ledgers(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    ref_ids: Dict[str, List["DataRow"]] = {}

    for dr in data_rows:
        if dr.row_dict["refid"] in ref_ids:
            ref_ids[dr.row_dict["refid"]].append(dr)
        else:
            ref_ids[dr.row_dict["refid"]] = [dr]

    for row_index, data_row in enumerate(data_rows):
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f"row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if data_row.parsed:
            continue

        try:
            _parse_kraken_ledgers_row(ref_ids, data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_kraken_ledgers_row(
    ref_ids: Dict[str, List["DataRow"]],
    data_rows: List["DataRow"],
    parser: DataParser,
    data_row: "DataRow",
    row_index: int,
) -> None:
    # https://support.kraken.com/hc/en-us/articles/360001169383-How-to-interpret-Ledger-history-fields
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])
    data_row.parsed = True

    if row_dict["txid"] == "":
        # Skip failed transactions
        return

    if (
        row_dict["type"] in ("deposit", "withdrawal")
        and _normalise_asset(row_dict["asset"]) == "FEE"
    ):
        # Kraken fee credits (KFEE) are not a tradeable asset; skip standalone deposits/
        # withdrawals of them. KFEE spent as a trading fee is valued in _make_trade().
        return

    if row_dict["type"] == "deposit":
        if Decimal(row_dict["amount"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["amount"]),
                buy_asset=_normalise_asset(row_dict["asset"]),
                fee_quantity=abs(Decimal(row_dict["fee"])),
                fee_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["amount"])),
                sell_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
                note="Reverse failed Deposit",
            )
            if Decimal(row_dict["fee"]) != 0:
                dup_data_row = copy.copy(data_row)
                dup_data_row.row = []
                dup_data_row.t_record = TransactionOutRecord(
                    TrType.FEE_REBATE,
                    data_row.timestamp,
                    buy_quantity=abs(Decimal(row_dict["fee"])),
                    buy_asset=_normalise_asset(row_dict["asset"]),
                    wallet=WALLET,
                    note="Reverse failed Deposit fee",
                )
                data_rows.insert(row_index + 1, dup_data_row)
    elif row_dict["type"] == "withdrawal":
        if Decimal(row_dict["amount"]) < 0:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["amount"])),
                sell_asset=_normalise_asset(row_dict["asset"]),
                fee_quantity=abs(Decimal(row_dict["fee"])),
                fee_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["amount"]),
                buy_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
                note="Reverse failed Withdrawal",
            )
            if Decimal(row_dict["fee"]) != 0:
                dup_data_row = copy.copy(data_row)
                dup_data_row.row = []
                dup_data_row.t_record = TransactionOutRecord(
                    TrType.FEE_REBATE,
                    data_row.timestamp,
                    buy_quantity=abs(Decimal(row_dict["fee"])),
                    buy_asset=_normalise_asset(row_dict["asset"]),
                    wallet=WALLET,
                    note="Reverse failed Withdrawal fee",
                )
                data_rows.insert(row_index + 1, dup_data_row)
    elif row_dict["type"] == "invite bonus":
        data_row.t_record = TransactionOutRecord(
            TrType.REFERRAL,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount"]),
            buy_asset=_normalise_asset(row_dict["asset"]),
            wallet=WALLET,
        )
    elif row_dict["type"] == "staking":
        if Decimal(row_dict["amount"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.STAKING_REWARD,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["amount"]),
                buy_asset=_normalise_asset(row_dict["asset"]),
                fee_quantity=abs(Decimal(row_dict["fee"])),
                fee_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.SPEND,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["amount"])),
                sell_asset=_normalise_asset(row_dict["asset"]),
                fee_quantity=abs(Decimal(row_dict["fee"])),
                fee_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
    elif row_dict["type"] == "dividend":
        data_row.t_record = TransactionOutRecord(
            TrType.DIVIDEND,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount"]),
            buy_asset=_normalise_asset(row_dict["asset"]),
            wallet=WALLET,
        )
    elif row_dict["type"] == "adjustment":
        if Decimal(row_dict["amount"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.AIRDROP,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["amount"]),
                buy_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.SPEND,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["amount"])),
                sell_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
    elif row_dict["type"] == "transfer":
        # An empty subtype is a fork/airdrop or a delisting; "delistingconversion" is the
        # forced conversion of a delisted asset. Both arrive as unpaired single legs (the
        # in/out sides have different refids, often days apart), so they can't be combined
        # into one trade; book each leg on its own (received = Airdrop, sent = Spend).
        if row_dict["subtype"] in ("", "delistingconversion"):
            if Decimal(row_dict["amount"]) > 0:
                # Fork or Airdrop
                data_row.t_record = TransactionOutRecord(
                    TrType.AIRDROP,
                    data_row.timestamp,
                    buy_quantity=Decimal(row_dict["amount"]),
                    buy_asset=_normalise_asset(row_dict["asset"]),
                    wallet=WALLET,
                )
            else:
                # Delisting?
                data_row.t_record = TransactionOutRecord(
                    TrType.SPEND,
                    data_row.timestamp,
                    sell_quantity=abs(Decimal(row_dict["amount"])),
                    sell_asset=_normalise_asset(row_dict["asset"]),
                    wallet=WALLET,
                )
        elif row_dict["subtype"] == "airdrop":
            data_row.t_record = TransactionOutRecord(
                TrType.AIRDROP,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["amount"]),
                buy_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
        elif row_dict["subtype"] in (
            "spottostaking",
            "stakingtospot",
            "spotfromstaking",
            "stakingfromspot",
            "spottofutures",
            "spotfromfutures",
        ):
            # Skip internal transfers
            return
        else:
            sys.stderr.write(
                f"{WARNING} Skipping unknown Kraken 'transfer' subtype: "
                f"'{row_dict['subtype']}'\n"
            )
            return
    elif row_dict["type"] == "margin":
        if Decimal(row_dict["amount"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_GAIN,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["amount"]),
                buy_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
        elif Decimal(row_dict["amount"]) < 0:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_LOSS,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["amount"])),
                sell_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_FEE,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["fee"])),
                sell_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )

        if Decimal(row_dict["amount"]) != 0 and Decimal(row_dict["fee"]) != 0:
            # Insert extra row to contain the MARGIN_FEE in addition to a MARGIN_GAIN/LOSS
            dup_data_row = copy.copy(data_row)
            dup_data_row.row = []
            dup_data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_FEE,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["fee"])),
                sell_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
            data_rows.insert(row_index + 1, dup_data_row)
    elif row_dict["type"] == "rollover":
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["fee"])),
            sell_asset=_normalise_asset(row_dict["asset"]),
            wallet=WALLET,
        )
    elif row_dict["type"] == "settled":
        _make_trade(_get_ref_ids(ref_ids, row_dict["refid"], ("settled",)), parser)
    elif row_dict["type"] == "trade":
        _make_trade(_get_ref_ids(ref_ids, row_dict["refid"], ("trade",)), parser)
    elif row_dict["type"] in ("spend", "receive"):
        _make_trade(_get_ref_ids(ref_ids, row_dict["refid"], ("spend", "receive")), parser)
    elif row_dict["type"] == "earn":
        if row_dict["subtype"] in (
            "migration",
            "autoallocate",
            "allocation",
            "deallocation",
            "autoallocation",
        ):
            # Skip internal transfers (moving funds in/out of the Earn product)
            return
        if row_dict["subtype"] == "" and not Decimal(row_dict["fee"]):
            # An "earn" with no subtype and no fee is an internal transfer, so skip
            return
        if row_dict["subtype"] not in ("reward", ""):
            sys.stderr.write(
                f"{WARNING} Unknown Kraken 'earn' subtype: "
                f"'{row_dict['subtype']}', assuming reward\n"
            )

        # Kraken Earn rewards (bonded/locked/liquid/flexible staking) are staking income.
        # A fee-bearing "earn" with no subtype, or an unknown subtype, is treated the same.
        if Decimal(row_dict["amount"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.STAKING_REWARD,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["amount"]),
                buy_asset=_normalise_asset(row_dict["asset"]),
                fee_quantity=abs(Decimal(row_dict["fee"])),
                fee_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.SPEND,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["amount"])),
                sell_asset=_normalise_asset(row_dict["asset"]),
                fee_quantity=abs(Decimal(row_dict["fee"])),
                fee_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def _get_ref_ids(
    ref_ids: Dict[str, List["DataRow"]], ref_id: str, k_type: Tuple[str, ...]
) -> List["DataRow"]:
    return [dr for dr in ref_ids[ref_id] if dr.row_dict["type"] in k_type]


def _make_trade(ref_ids: List["DataRow"], parser: DataParser) -> None:
    buy_quantity = sell_quantity = Decimal(0)
    fee_quantity = None
    buy_asset = sell_asset = config.ccy
    fee_asset = ""
    trade_row = None

    for data_row in ref_ids:
        row_dict = data_row.row_dict
        data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])
        data_row.parsed = True

        amount = Decimal(row_dict["amount"])
        fee = Decimal(row_dict["fee"])

        if amount == 0:
            # Assume zero amount is a secondary fee (e.g. a Kraken fee credit leg)
            norm_fee_asset, norm_fee_quantity = _normalise_fee(row_dict["asset"], abs(fee))
            data_row.t_record = TransactionOutRecord(
                TrType.SPEND,
                data_row.timestamp,
                sell_quantity=Decimal(0),
                sell_asset=norm_fee_asset,
                fee_quantity=norm_fee_quantity,
                fee_asset=norm_fee_asset,
                wallet=WALLET,
                note="Trading fee",
            )
            continue

        # Accumulate, so a trade that liquidates the same asset from more than one wallet
        # (e.g. spot + earn in a single order) sums the legs instead of overwriting them.
        # Legs on the same side must share an asset; if they ever differ, fail loudly
        # rather than silently summing unlike assets into a single quantity.
        norm_asset = _normalise_asset(row_dict["asset"])
        if amount > 0:
            if buy_quantity and norm_asset != buy_asset:
                raise UnexpectedContentError(
                    parser.in_header.index("asset"), "asset", row_dict["asset"]
                )
            buy_quantity += amount
            buy_asset = norm_asset
        else:
            if sell_quantity and norm_asset != sell_asset:
                raise UnexpectedContentError(
                    parser.in_header.index("asset"), "asset", row_dict["asset"]
                )
            sell_quantity += abs(amount)
            sell_asset = norm_asset

        if not trade_row:
            trade_row = data_row

        if fee != 0:
            norm_fee_asset, norm_fee_quantity = _normalise_fee(row_dict["asset"], abs(fee))
            if fee_quantity is None:
                fee_quantity = norm_fee_quantity
                fee_asset = norm_fee_asset
            else:
                # Add as secondary fee
                data_row.t_record = TransactionOutRecord(
                    TrType.SPEND,
                    data_row.timestamp,
                    sell_quantity=Decimal(0),
                    sell_asset=norm_fee_asset,
                    fee_quantity=norm_fee_quantity,
                    fee_asset=norm_fee_asset,
                    wallet=WALLET,
                    note="Trading fee",
                )

    if trade_row:
        if (buy_quantity == 0) != (sell_quantity == 0) and max(
            buy_quantity, sell_quantity
        ) < DUST_THRESHOLD:
            # One-sided dust (rounding residue with no counterparty leg); drop it.
            return

        trade_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            trade_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )


def parse_kraken_trades(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])

    base_asset, quote_asset = _split_trading_pair(row_dict["pair"])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(parser.in_header.index("pair"), "pair", row_dict["pair"])

    if row_dict["type"] == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["vol"]),
            buy_asset=_normalise_asset(base_asset),
            sell_quantity=Decimal(row_dict["cost"]),
            sell_asset=_normalise_asset(quote_asset),
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=_normalise_asset(quote_asset),
            wallet=WALLET,
        )
    elif row_dict["type"] == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["cost"]),
            buy_asset=_normalise_asset(quote_asset),
            sell_quantity=Decimal(row_dict["vol"]),
            sell_asset=_normalise_asset(base_asset),
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=_normalise_asset(quote_asset),
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def _split_trading_pair(trading_pair: str) -> Tuple[Optional[str], Optional[str]]:
    if "/" in trading_pair:
        base_asset, quote_asset = trading_pair.split("/")
        return base_asset, quote_asset

    if trading_pair in TRADINGPAIR_TO_QUOTE_ASSET:
        quote_asset = TRADINGPAIR_TO_QUOTE_ASSET[trading_pair]
        base_asset = trading_pair[: -len(quote_asset)]
        return base_asset, quote_asset

    for quote_asset in sorted(QUOTE_ASSETS, reverse=True):
        if trading_pair.endswith(quote_asset):
            base_asset = trading_pair[: -len(quote_asset)]
            return base_asset, quote_asset

    return None, None


def _normalise_asset(asset: str) -> str:
    asset = ALT_ASSETS.get(asset, asset)

    if asset == "XBT":
        return "BTC"

    for suffix in sorted(STAKED_SUFFIX, reverse=True):
        if asset.endswith(suffix):
            return asset[: -len(suffix)]
    return asset


def _normalise_fee(asset: str, fee_quantity: Decimal) -> Tuple[str, Decimal]:
    # Kraken fee credits (KFEE/"FEE") have a fixed value of 0.01 USD and no market price,
    # so express the fee in USD rather than against an unpriceable asset.
    if _normalise_asset(asset) == "FEE":
        return "USD", fee_quantity * KFEE_USD_RATE
    return _normalise_asset(asset), fee_quantity


kraken_ledgers = DataParser(
    ParserType.EXCHANGE,
    "Kraken Ledgers",
    [
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
    ],
    worksheet_name="Kraken L",
    all_handler=parse_kraken_ledgers,
)

DataParser(
    ParserType.EXCHANGE,
    "Kraken Ledgers",
    [
        "txid",
        "refid",
        "time",
        "type",
        "subtype",
        "aclass",
        "asset",
        "wallet",
        "amount",
        "fee",
        "balance",
        "amountusd",
    ],
    worksheet_name="Kraken L",
    all_handler=parse_kraken_ledgers,
)

DataParser(
    ParserType.EXCHANGE,
    "Kraken Ledgers",
    [
        "txid",
        "refid",
        "time",
        "type",
        "subtype",
        "aclass",
        "asset",
        "wallet",
        "amount",
        "fee",
        "balance",
    ],
    worksheet_name="Kraken L",
    all_handler=parse_kraken_ledgers,
)

DataParser(
    ParserType.EXCHANGE,
    "Kraken Ledgers",
    [
        "txid",
        "refid",
        "time",
        "type",
        "subtype",
        "aclass",
        "asset",
        "amount",
        "fee",
        "balance",
        "amountusd",
    ],
    worksheet_name="Kraken L",
    all_handler=parse_kraken_ledgers,
)

DataParser(
    ParserType.EXCHANGE,
    "Kraken Ledgers",
    [
        "txid",
        "refid",
        "time",
        "type",
        "subtype",
        "aclass",
        "asset",
        "amount",
        "fee",
        "balance",
    ],
    worksheet_name="Kraken L",
    all_handler=parse_kraken_ledgers,
)

DataParser(
    ParserType.EXCHANGE,
    "Kraken Ledgers",
    [
        "txid",
        "refid",
        "time",
        "type",
        "subtype",
        "aclass",
        "asset",
        "wallet",
        "amount",
        "fee",
        "balance",
    ],
    worksheet_name="Kraken L",
    all_handler=parse_kraken_ledgers,
)

DataParser(
    ParserType.EXCHANGE,
    "Kraken Ledgers",
    [
        "txid",
        "refid",
        "time",
        "type",
        "subtype",
        "aclass",
        "asset",
        "amount",
        "fee",
        "balance",
        "",
    ],
    worksheet_name="Kraken L",
    all_handler=parse_kraken_ledgers,
)

DataParser(
    ParserType.EXCHANGE,
    "Kraken Trades",
    [
        "txid",
        "ordertxid",
        "pair",
        "time",
        "type",
        "ordertype",
        "price",
        "cost",
        "fee",
        "vol",
        "margin",
        "misc",
        "ledgers",
        "postxid",
        "posstatus",
        "cprice",
        "ccost",
        "cfee",
        "cvol",
        "cmargin",
        "net",
        "trades",
    ],
    worksheet_name="Kraken T",
    deprecated=kraken_ledgers,
    row_handler=parse_kraken_trades,
)

DataParser(
    ParserType.EXCHANGE,
    "Kraken Trades",
    [
        "txid",
        "ordertxid",
        "pair",
        "time",
        "type",
        "ordertype",
        "price",
        "cost",
        "fee",
        "vol",
        "margin",
        "misc",
        "ledgers",
    ],
    worksheet_name="Kraken T",
    deprecated=kraken_ledgers,
    row_handler=parse_kraken_trades,
)
