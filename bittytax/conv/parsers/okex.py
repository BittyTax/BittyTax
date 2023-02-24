# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal

import dateutil.tz
from colorama import Fore

from ...config import config
from ..dataparser import DataParser
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

WALLET = "OKEx"
TZ_INFOS = {"CST": dateutil.tz.gettz("Asia/Shanghai")}


def parse_okex_trades(data_rows, parser, **_kwargs):
    for buy_row, sell_row in zip(data_rows[0::2], data_rows[1::2]):
        try:
            if config.debug:
                sys.stderr.write(
                    "%sconv: row[%s] %s\n"
                    % (
                        Fore.YELLOW,
                        parser.in_header_row_num + buy_row.line_num,
                        buy_row,
                    )
                )
                sys.stderr.write(
                    "%sconv: row[%s] %s\n"
                    % (
                        Fore.YELLOW,
                        parser.in_header_row_num + sell_row.line_num,
                        sell_row,
                    )
                )

            parse_okex_trades_row(buy_row, sell_row, parser)
        except DataRowError as e:
            buy_row.failure = e


def parse_okex_trades_row(buy_row, sell_row, parser):
    buy_row.timestamp = DataParser.parse_timestamp(buy_row.row_dict["time"], tzinfos=TZ_INFOS)
    sell_row.timestamp = DataParser.parse_timestamp(sell_row.row_dict["time"], tzinfos=TZ_INFOS)

    if buy_row.row_dict["type"] == "buy" and sell_row.row_dict["type"] == "sell":
        buy_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            buy_row.timestamp,
            buy_quantity=buy_row.row_dict["size"],
            buy_asset=buy_row.row_dict["currency"],
            sell_quantity=abs(Decimal(sell_row.row_dict["size"])),
            sell_asset=sell_row.row_dict["currency"],
            fee_quantity=abs(Decimal(buy_row.row_dict["fee"])),
            fee_asset=buy_row.row_dict["currency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", buy_row.row_dict["type"])


DataParser(
    DataParser.TYPE_EXCHANGE,
    "OKEx",
    ["time", "type", "size", "balance", "fee", "currency"],
    worksheet_name="OKEx",
    all_handler=parse_okex_trades,
)
