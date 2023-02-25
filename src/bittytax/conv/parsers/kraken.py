# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import copy
import sys
from decimal import Decimal

from colorama import Fore

from ...config import config
from ..dataparser import DataParser
from ..exceptions import (
    DataRowError,
    UnexpectedContentError,
    UnexpectedTradingPairError,
    UnexpectedTypeError,
)
from ..out_record import TransactionOutRecord

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

ASSETS_SHORT = ["MC", "MV", "SC", "T"]


def parse_kraken_ledgers(data_rows, parser, **_kwargs):
    ref_ids = {}

    for dr in data_rows:
        if dr.row_dict["refid"] in ref_ids:
            ref_ids[dr.row_dict["refid"]].append(dr)
        else:
            ref_ids[dr.row_dict["refid"]] = [dr]

    for row_index, data_row in enumerate(data_rows):
        if config.debug:
            sys.stderr.write(
                "%sconv: row[%s] %s\n"
                % (Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row)
            )

        if data_row.parsed:
            continue

        try:
            _parse_kraken_ledgers_row(ref_ids, data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e


def _parse_kraken_ledgers_row(ref_ids, data_rows, parser, data_row, row_index):
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
                TransactionOutRecord.TYPE_DEPOSIT,
                data_row.timestamp,
                buy_quantity=row_dict["amount"],
                buy_asset=_normalise_asset(row_dict["asset"]),
                fee_quantity=row_dict["fee"],
                fee_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TransactionOutRecord.TYPE_WITHDRAWAL,
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
                    TransactionOutRecord.TYPE_GIFT_RECEIVED,
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
                TransactionOutRecord.TYPE_WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["amount"])),
                sell_asset=_normalise_asset(row_dict["asset"]),
                fee_quantity=row_dict["fee"],
                fee_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TransactionOutRecord.TYPE_DEPOSIT,
                data_row.timestamp,
                buy_quantity=row_dict["amount"],
                buy_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
                note="Reverse failed Withdrawal",
            )
            if Decimal(row_dict["fee"]) < 0:
                dup_data_row = copy.copy(data_row)
                dup_data_row.row = []
                dup_data_row.t_record = TransactionOutRecord(
                    TransactionOutRecord.TYPE_GIFT_RECEIVED,
                    data_row.timestamp,
                    buy_quantity=abs(Decimal(row_dict["fee"])),
                    buy_asset=_normalise_asset(row_dict["asset"]),
                    wallet=WALLET,
                    note="Reverse failed Withdrawal fee",
                )
                data_rows.insert(row_index + 1, dup_data_row)
    elif row_dict["type"] == "invite bonus":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_GIFT_RECEIVED,
            data_row.timestamp,
            buy_quantity=row_dict["amount"],
            buy_asset=_normalise_asset(row_dict["asset"]),
            wallet=WALLET,
        )
    elif row_dict["type"] == "staking":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_STAKING,
            data_row.timestamp,
            buy_quantity=row_dict["amount"],
            buy_asset=_normalise_asset(row_dict["asset"]),
            wallet=WALLET,
        )
    elif row_dict["type"] == "transfer":
        if len(_get_ref_ids(ref_ids, row_dict["refid"], row_dict["type"])) > 1:
            # Multiple transfer rows is a rebase? Not currently supported
            raise UnexpectedContentError(
                parser.in_header.index("refid"), "refid", row_dict["refid"]
            )

        if row_dict["subtype"] == "":
            if Decimal(row_dict["amount"]) >= 0:
                # Fork or Airdrop
                data_row.t_record = TransactionOutRecord(
                    TransactionOutRecord.TYPE_AIRDROP,
                    data_row.timestamp,
                    buy_quantity=row_dict["amount"],
                    buy_asset=_normalise_asset(row_dict["asset"]),
                    wallet=WALLET,
                )
            else:
                # Delisting
                data_row.t_record = TransactionOutRecord(
                    TransactionOutRecord.TYPE_LOST,
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
        ):
            # Skip internal transfers
            return
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("subtype"), "subtype", row_dict["subtype"]
            )
    elif row_dict["type"] in ("trade", "spend", "receive"):
        _make_trade(_get_ref_ids(ref_ids, row_dict["refid"], row_dict["type"]))
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def _get_ref_ids(ref_ids, ref_id, k_type):
    return [dr for dr in ref_ids[ref_id] if dr.row_dict["type"] == k_type]


def _make_trade(ref_ids):
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
                TransactionOutRecord.TYPE_SPEND,
                data_row.timestamp,
                sell_quantity=Decimal(0),
                sell_asset=_normalise_asset(row_dict["asset"]),
                fee_quantity=row_dict["fee"],
                fee_asset=_normalise_asset(row_dict["asset"]),
                wallet=WALLET,
                note="Trading fee",
            )
            continue

        if Decimal(row_dict["amount"]) > 0:
            buy_quantity = row_dict["amount"]
            buy_asset = _normalise_asset(row_dict["asset"])

        if Decimal(row_dict["amount"]) < 0:
            sell_quantity = abs(Decimal(row_dict["amount"]))
            sell_asset = _normalise_asset(row_dict["asset"])

        if not trade_row:
            trade_row = data_row

        if Decimal(row_dict["fee"]) > 0:
            if not fee_quantity:
                fee_quantity = row_dict["fee"]
                fee_asset = _normalise_asset(row_dict["asset"])
            else:
                # Add as secondary fee
                data_row.t_record = TransactionOutRecord(
                    TransactionOutRecord.TYPE_SPEND,
                    data_row.timestamp,
                    sell_quantity=Decimal(0),
                    sell_asset=_normalise_asset(row_dict["asset"]),
                    fee_quantity=row_dict["fee"],
                    fee_asset=_normalise_asset(row_dict["asset"]),
                    wallet=WALLET,
                    note="Trading fee",
                )
    if trade_row:
        trade_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            trade_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )


def parse_kraken_trades(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])

    base_asset, quote_asset = _split_trading_pair(row_dict["pair"])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(parser.in_header.index("pair"), "pair", row_dict["pair"])

    if row_dict["type"] == "buy":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=row_dict["vol"],
            buy_asset=_normalise_asset(base_asset),
            sell_quantity=row_dict["cost"],
            sell_asset=_normalise_asset(quote_asset),
            fee_quantity=row_dict["fee"],
            fee_asset=_normalise_asset(quote_asset),
            wallet=WALLET,
        )
    elif row_dict["type"] == "sell":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=row_dict["cost"],
            buy_asset=_normalise_asset(quote_asset),
            sell_quantity=row_dict["vol"],
            sell_asset=_normalise_asset(base_asset),
            fee_quantity=row_dict["fee"],
            fee_asset=_normalise_asset(quote_asset),
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def _split_trading_pair(trading_pair):
    for quote_asset in sorted(QUOTE_ASSETS, reverse=True):
        if trading_pair.endswith(quote_asset):
            base_asset = trading_pair[: -len(quote_asset)]

            if len(base_asset) < 3:
                if base_asset in ASSETS_SHORT:
                    return base_asset, quote_asset
            else:
                return base_asset, quote_asset

    return None, None


def _normalise_asset(asset):
    if asset in ALT_ASSETS:
        asset = ALT_ASSETS.get(asset)

    if asset == "XBT":
        return "BTC"

    if asset.endswith(".S"):
        return asset[:-2]
    return asset


LEDGERS = DataParser(
    DataParser.TYPE_EXCHANGE,
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
    DataParser.TYPE_EXCHANGE,
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
    DataParser.TYPE_EXCHANGE,
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
    deprecated=LEDGERS,
    row_handler=parse_kraken_trades,
)

DataParser(
    DataParser.TYPE_EXCHANGE,
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
    deprecated=LEDGERS,
    row_handler=parse_kraken_trades,
)
