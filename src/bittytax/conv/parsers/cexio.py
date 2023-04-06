# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

import re
import sys
from decimal import ROUND_DOWN, Decimal

from colorama import Fore

from ...config import config
from ..dataparser import DataParser
from ..exceptions import DataRowError, UnexpectedContentError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

WALLET = "CEX.IO"


def parse_cexio(data_rows, parser, **_kwargs):
    tx_times = {}

    for dr in data_rows:
        if dr.row_dict["DateUTC"] in tx_times:
            tx_times[dr.row_dict["DateUTC"]].append(dr)
        else:
            tx_times[dr.row_dict["DateUTC"]] = [dr]

    for data_row in data_rows:
        if config.debug:
            sys.stderr.write(
                "%sconv: row[%s] %s\n"
                % (Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row)
            )

        if data_row.parsed:
            continue

        try:
            _parse_cexio_row(tx_times, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_cexio_row(tx_times, parser, data_row):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["DateUTC"])

    if row_dict["FeeAmount"]:
        fee_quantity = row_dict["FeeAmount"]
        fee_asset = row_dict["FeeSymbol"]
    else:
        fee_quantity = None
        fee_asset = ""

    if row_dict["Type"] == "deposit":
        if row_dict["Balance"] == "pending":
            return

        if row_dict["Comment"].endswith("Completed") or row_dict["Comment"].startswith("Confirmed"):
            data_row.t_record = TransactionOutRecord(
                TransactionOutRecord.TYPE_DEPOSIT,
                data_row.timestamp,
                buy_quantity=row_dict["Amount"],
                buy_asset=row_dict["Symbol"],
                fee_quantity=fee_quantity,
                fee_asset=fee_asset,
                wallet=WALLET,
                note=row_dict["Comment"],
            )
    elif row_dict["Type"] == "withdraw":
        if fee_quantity:
            sell_quantity = abs(Decimal(row_dict["Amount"])) - Decimal(fee_quantity)
        else:
            sell_quantity = abs(Decimal(row_dict["Amount"]))

        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=sell_quantity,
            sell_asset=row_dict["Symbol"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
            note=row_dict["Comment"],
        )
    elif row_dict["Type"] in ("buy", "sell"):
        trade_info = _get_trade_info(row_dict["Comment"], row_dict["Type"])

        if trade_info is None:
            raise UnexpectedContentError(
                parser.in_header.index("Comment"), "Comment", row_dict["Comment"]
            )

        if trade_info[0] == "Bought":
            buy_quantity = row_dict["Amount"]
            buy_asset = row_dict["Symbol"]
            sell_quantity = Decimal(trade_info[1]) * Decimal(trade_info[3])
            sell_asset = trade_info[4]
            if sell_asset in config.fiat_list:
                sell_quantity = sell_quantity.quantize(Decimal("0.00"), ROUND_DOWN)
        elif trade_info[0] == "Sold":
            if fee_quantity:
                buy_quantity = Decimal(row_dict["Amount"]) + Decimal(fee_quantity)
            else:
                buy_quantity = Decimal(row_dict["Amount"])
            buy_asset = row_dict["Symbol"]
            sell_quantity = trade_info[1]
            sell_asset = trade_info[2]
        else:
            # Skip corresponding "Buy/Sell Order" row
            return

        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
            note=row_dict["Comment"],
        )
    elif row_dict["Type"] in ("wallet_buy", "wallet_sell"):
        _make_trade(tx_times[row_dict["DateUTC"]], data_row, parser)
    elif row_dict["Type"] in ("referral", "checksum", "costsNothing"):
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_GIFT_RECEIVED,
            data_row.timestamp,
            buy_quantity=row_dict["Amount"],
            buy_asset=row_dict["Symbol"],
            wallet=WALLET,
            note=row_dict["Comment"],
        )
    elif row_dict["Type"] == "staking":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_STAKING,
            data_row.timestamp,
            buy_quantity=row_dict["Amount"],
            buy_asset=row_dict["Symbol"],
            wallet=WALLET,
            note=row_dict["Comment"],
        )
    elif row_dict["Type"] == "cancel":
        # Skip
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _get_trade_info(comment, t_type):
    if t_type == "buy":
        match = re.match(
            r"^(Bought) (\d+|\d+\.\d+) (\w+) at (\d+|\d+\.\d+) (\w+)$|^Buy Order.*$",
            comment,
        )
    elif t_type == "sell":
        match = re.match(
            r"^(Sold) (\d+|\d+\.\d+) (\w+) at (\d+|\d+\.\d+) (\w+)$|^Sell Order.*$",
            comment,
        )
    else:
        return None

    if match:
        return match.groups()
    return None


def _make_trade(tx_times, data_row, parser):
    buy_rows = [dr for dr in tx_times if dr.row_dict["Type"] == "wallet_buy"]
    sell_rows = [dr for dr in tx_times if dr.row_dict["Type"] == "wallet_sell"]

    if len(buy_rows) == 1 and len(sell_rows) == 1:
        if data_row == buy_rows[0]:
            sell_rows[0].timestamp = data_row.timestamp
            sell_rows[0].parsed = True
        else:
            buy_rows[0].timestamp = data_row.timestamp
            buy_rows[0].parsed = True

        # Assumes there are no trading fees
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=buy_rows[0].row_dict["Amount"],
            buy_asset=buy_rows[0].row_dict["Symbol"],
            sell_quantity=abs(Decimal(sell_rows[0].row_dict["Amount"])),
            sell_asset=sell_rows[0].row_dict["Symbol"],
            wallet=WALLET,
        )
    else:
        data_row.failure = UnexpectedContentError(
            parser.in_header.index("Type"), "Type", data_row.row_dict["Type"]
        )


DataParser(
    DataParser.TYPE_EXCHANGE,
    "CEX.IO",
    [
        "DateUTC",
        "Amount",
        "Symbol",
        "Balance",
        "Type",
        "Pair",
        "FeeSymbol",
        "FeeAmount",
        "Comment",
    ],
    worksheet_name="CEX.IO",
    all_handler=parse_cexio,
)
