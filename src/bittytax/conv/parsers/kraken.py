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

QUOTE_ASSETS = [
    "AED",
    "AUD",
    "CAD",
    "CHF",
    "DAI",
    "DOT",
    "ETH",
    "EUR",
    "GBP",
    "JPY",
    "PYUSD",
    "USD",
    "USDC",
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
    "ZAUD": "AUD",
    "ZCAD": "CAD",
    "ZEUR": "EUR",
    "ZGBP": "GBP",
    "ZJPY": "JPY",
    "ZUSD": "USD",
}

TRADINGPAIR_TO_QUOTE_ASSET = {
    "BLZEUR": "EUR",
    "BLZUSD": "USD",
    "CHZEUR": "EUR",
    "CHZUSD": "USD",
    "ETHPYUSD": "PYUSD",
    "ICXETH": "ETH",
    "ICXXBT": "XBT",
    "SNXETH": "ETH",
    "SNXXBT": "XBT",
    "TRXETH": "ETH",
    "TRXXBT": "XBT",
    "XBTPYUSD": "PYUSD",
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

    if row_dict["type"] == "deposit":
        if Decimal(row_dict["amount"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["amount"]),
                buy_asset=_normalise_asset(row_dict["asset"]),
                fee_quantity=Decimal(row_dict["fee"]),
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
            if Decimal(row_dict["fee"]) < 0:
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
                fee_quantity=Decimal(row_dict["fee"]),
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
            if Decimal(row_dict["fee"]) < 0:
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
        data_row.t_record = TransactionOutRecord(
            TrType.STAKING,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount"]),
            buy_asset=_normalise_asset(row_dict["asset"]),
            wallet=WALLET,
        )
    elif row_dict["type"] == "transfer":
        if len(_get_ref_ids(ref_ids, row_dict["refid"], ("transfer",))) > 1:
            # Multiple transfer rows is a rebase? Not currently supported
            raise UnexpectedContentError(
                parser.in_header.index("refid"), "refid", row_dict["refid"]
            )

        if row_dict["subtype"] == "":
            if Decimal(row_dict["amount"]) >= 0:
                # Fork or Airdrop
                data_row.t_record = TransactionOutRecord(
                    TrType.AIRDROP,
                    data_row.timestamp,
                    buy_quantity=Decimal(row_dict["amount"]),
                    buy_asset=_normalise_asset(row_dict["asset"]),
                    wallet=WALLET,
                )
            else:
                # Delisting
                data_row.t_record = TransactionOutRecord(
                    TrType.LOST,
                    data_row.timestamp,
                    sell_quantity=abs(Decimal(row_dict["amount"])),
                    sell_asset=_normalise_asset(row_dict["asset"]),
                    wallet=WALLET,
                )
        elif row_dict["subtype"] in (
            "spottostaking",
            "stakingtospot",
            "spotfromstaking",
            "stakingfromspot",
            "spotfromfutures",
        ):
            # Skip internal transfers
            return
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("subtype"), "subtype", row_dict["subtype"]
            )
    elif row_dict["type"] == "trade":
        _make_trade(_get_ref_ids(ref_ids, row_dict["refid"], ("trade",)))
    elif row_dict["type"] in ("spend", "receive"):
        _make_trade(_get_ref_ids(ref_ids, row_dict["refid"], ("spend", "receive")))
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def _get_ref_ids(
    ref_ids: Dict[str, List["DataRow"]], ref_id: str, k_type: Tuple[str, ...]
) -> List["DataRow"]:
    return [dr for dr in ref_ids[ref_id] if dr.row_dict["type"] in k_type]


def _make_trade(ref_ids: List["DataRow"]) -> None:
    buy_quantity = sell_quantity = fee_quantity = None
    buy_asset = sell_asset = fee_asset = ""
    trade_row = None

    for data_row in ref_ids:
        row_dict = data_row.row_dict
        data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])
        data_row.parsed = True

        if Decimal(row_dict["amount"]) == 0:
            # Assume zero amount is a secondary fee
            data_row.t_record = TransactionOutRecord(
                TrType.SPEND,
                data_row.timestamp,
                sell_quantity=Decimal(0),
                sell_asset=_normalise_asset(row_dict["asset"]),
                fee_quantity=Decimal(row_dict["fee"]),
                fee_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
                note="Trading fee",
            )
            continue

        if Decimal(row_dict["amount"]) > 0:
            buy_quantity = Decimal(row_dict["amount"])
            buy_asset = _normalise_asset(row_dict["asset"])

        if Decimal(row_dict["amount"]) < 0:
            sell_quantity = abs(Decimal(row_dict["amount"]))
            sell_asset = _normalise_asset(row_dict["asset"])

        if not trade_row:
            trade_row = data_row

        if Decimal(row_dict["fee"]) > 0:
            if not fee_quantity:
                fee_quantity = Decimal(row_dict["fee"])
                fee_asset = _normalise_asset(row_dict["asset"])
            else:
                # Add as secondary fee
                data_row.t_record = TransactionOutRecord(  # type: ignore[unreachable]
                    TrType.SPEND,
                    data_row.timestamp,
                    sell_quantity=Decimal(0),
                    sell_asset=_normalise_asset(row_dict["asset"]),
                    fee_quantity=Decimal(row_dict["fee"]),
                    fee_asset=_normalise_asset(row_dict["asset"]),
                    wallet=WALLET,
                    note="Trading fee",
                )
    if trade_row:
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

    if asset.endswith(".S"):
        return asset[:-2]
    return asset


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
