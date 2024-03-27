# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import copy
import re
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, List

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "KuCoin"


def parse_kucoin_trades_v4(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["createdDate"], tz="Asia/Singapore")

    if row_dict["direction"].lower() == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount"]),
            buy_asset=row_dict["symbol"].split("-")[0],
            sell_quantity=Decimal(row_dict["dealValue"]),
            sell_asset=row_dict["symbol"].split("-")[1],
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=row_dict["symbol"].split("-")[1],
            wallet=WALLET,
        )
    elif row_dict["direction"].lower() == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["dealValue"]),
            buy_asset=row_dict["symbol"].split("-")[1],
            sell_quantity=Decimal(row_dict["amount"]),
            sell_asset=row_dict["symbol"].split("-")[0],
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=row_dict["symbol"].split("-")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("direction"), "direction", row_dict["direction"]
        )


def parse_kucoin_trades_v3(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["tradeCreatedAt"], tz="Asia/Singapore")

    if row_dict["side"] == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["size"]),
            buy_asset=row_dict["symbol"].split("-")[0],
            sell_quantity=Decimal(row_dict["funds"]),
            sell_asset=row_dict["symbol"].split("-")[1],
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=row_dict["feeCurrency"],
            wallet=WALLET,
        )
    elif row_dict["side"] == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["funds"]),
            buy_asset=row_dict["symbol"].split("-")[1],
            sell_quantity=Decimal(row_dict["size"]),
            sell_asset=row_dict["symbol"].split("-")[0],
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=row_dict["feeCurrency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("side"), "side", row_dict["side"])


def parse_kucoin_trades_v2(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["created_at"], tz="Asia/Singapore")

    if row_dict["direction"].lower() == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount_coin"]),
            buy_asset=row_dict["symbol"].split("-")[0],
            sell_quantity=Decimal(row_dict["funds"]),
            sell_asset=row_dict["symbol"].split("-")[1],
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=row_dict["symbol"].split("-")[1],
            wallet=WALLET,
        )
    elif row_dict["direction"].lower() == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["funds"]),
            buy_asset=row_dict["symbol"].split("-")[1],
            sell_quantity=Decimal(row_dict["amount_coin"]),
            sell_asset=row_dict["symbol"].split("-")[0],
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=row_dict["symbol"].split("-")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("direction"), "direction", row_dict["direction"]
        )


def parse_kucoin_trades_v1(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["created_at"], tz="Asia/Singapore")

    if row_dict["direction"].lower() == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount"]),
            buy_asset=row_dict["symbol"].split("-")[0],
            sell_quantity=Decimal(row_dict["deal_value"]),
            sell_asset=row_dict["symbol"].split("-")[1],
            wallet=WALLET,
        )
    elif row_dict["direction"].lower() == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["deal_value"]),
            buy_asset=row_dict["symbol"].split("-")[1],
            sell_quantity=Decimal(row_dict["amount"]),
            sell_asset=row_dict["symbol"].split("-")[0],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("direction"), "direction", row_dict["direction"]
        )


def parse_kucoin_deposits_withdrawals_v1(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["created_at"], tz="Asia/Singapore")

    if row_dict["type"] == "DEPOSIT":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["vol"]),
            buy_asset=row_dict["coin_type"],
            wallet=WALLET,
        )
    elif row_dict["type"] == "WITHDRAW":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["vol"]),
            sell_asset=row_dict["coin_type"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def parse_kucoin_deposits(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"], tz="Asia/Singapore")

    data_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount"]),
        buy_asset=row_dict["Coin"],
        wallet=WALLET,
    )


def parse_kucoin_withdrawals(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"], tz="Asia/Singapore")

    data_row.t_record = TransactionOutRecord(
        TrType.WITHDRAWAL,
        data_row.timestamp,
        sell_quantity=Decimal(row_dict["Amount"]),
        sell_asset=row_dict["Coin"],
        wallet=WALLET,
    )


def parse_kucoin_deposits_withdrawals_v2(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    timestamp_hdr = parser.args[0].group(1)
    utc_offset = parser.args[0].group(2)
    data_row.timestamp = DataParser.parse_timestamp(f"{row_dict[timestamp_hdr]} {utc_offset}")

    if row_dict["Status"] != "SUCCESS":
        return

    if "Withdrawal Address/Account" in row_dict:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Coin"],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Coin"],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Coin"],
            wallet=WALLET,
        )


def parse_kucoin_staking_income(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    timestamp_hdr = parser.args[0].group(1)
    utc_offset = parser.args[0].group(2)
    data_row.timestamp = DataParser.parse_timestamp(f"{row_dict[timestamp_hdr]} {utc_offset}")

    data_row.t_record = TransactionOutRecord(
        TrType.STAKING,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount"]),
        buy_asset=row_dict["Earnings Coin"],
        wallet=WALLET,
    )


def parse_kucoin_futures(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
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
            _parse_kucoin_futures_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_kucoin_futures_row(
    data_rows: List["DataRow"],
    parser: DataParser,
    data_row: "DataRow",
    row_index: int,
) -> None:
    row_dict = data_row.row_dict
    timestamp_hdr = parser.args[1].group(1)
    utc_offset = parser.args[1].group(2)
    data_row.timestamp = DataParser.parse_timestamp(f"{row_dict[timestamp_hdr]} {utc_offset}")
    data_row.parsed = True

    if Decimal(row_dict["Realized PNL"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_GAIN,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Realized PNL"]),
            buy_asset="USDT",
            wallet=WALLET,
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_LOSS,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Realized PNL"])),
            sell_asset="USDT",
            wallet=WALLET,
        )

    if Decimal(row_dict["Total Funding Fees"]) + Decimal(row_dict["Total Trading Fees"]) > 0:
        dup_data_row = copy.copy(data_row)
        dup_data_row.row = []
        dup_data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Total Funding Fees"])
            + Decimal(row_dict["Total Trading Fees"]),
            sell_asset="USDT",
            wallet=WALLET,
        )
        data_rows.insert(row_index + 1, dup_data_row)


DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "oid",
        "symbol",
        "dealPrice",
        "dealValue",
        "amount",
        "fee",
        "direction",
        "createdDate",
        "",
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v4,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "tradeCreatedAt",
        "orderId",
        "symbol",
        "side",
        "price",
        "size",
        "funds",
        "fee",
        "liquidity",
        "feeCurrency",
        "orderType",
        "",
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v3,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "tradeCreatedAt",
        "orderId",
        "symbol",
        "side",
        "price",
        "size",
        "funds",
        "fee",
        "liquidity",
        "feeCurrency",
        "orderType",
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v3,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "uid",
        "symbol",
        "order_type",
        "price",
        "amount_coin",
        "direction",
        "funds",
        "fee",
        "created_at",
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    ["uid", "symbol", "direction", "deal_price", "amount", "deal_value", "created_at"],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Deposits",
    ["Time", "Coin", "Amount", "Type", "Remark"],
    worksheet_name="KuCoin D",
    row_handler=parse_kucoin_deposits,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Withdrawals",
    ["Time", "Coin", "Amount", "Type", "Wallet Address", "Remark"],
    worksheet_name="KuCoin W",
    row_handler=parse_kucoin_withdrawals,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Deposits/Withdrawals",
    ["coin_type", "type", "add", "hash", "vol", "created_at"],
    worksheet_name="Kucoin D,W",
    row_handler=parse_kucoin_deposits_withdrawals_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Deposits",
    [
        "UID",
        "Account Type",
        lambda c: re.match(r"(^Time\((UTC[-+]\d{2}:\d{2})\))", c),
        "Remarks",
        "Status",
        "Fee",
        "Amount",
        "Coin",
        "Transfer Network",
    ],
    worksheet_name="Kucoin D,W",
    row_handler=parse_kucoin_deposits_withdrawals_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Withdrawals",
    [
        "UID",
        "Account Type",
        lambda c: re.match(r"(^Time\((UTC[-+]\d{2}:\d{2})\))", c),
        "Remarks",
        "Status",
        "Fee",
        "Amount",
        "Coin",
        "Transfer Network",
        "Withdrawal Address/Account",
    ],
    worksheet_name="Kucoin D,W",
    row_handler=parse_kucoin_deposits_withdrawals_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Staking",
    [
        "UID",
        "Account Type",
        "Order ID",
        lambda c: re.match(r"(^Time\((UTC[-+]\d{2}:\d{2})\))", c),
        "Staked Coin",
        "Product Type",
        "Product Name",
        "Earnings Coin",
        "Earnings Type",
        "Remarks",
        "Amount",
        "Amount（USDT）",
        "Fee",
    ],
    worksheet_name="Kucoin S",
    row_handler=parse_kucoin_staking_income,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Bundle Futures Orders Realized PNL",
    [
        "UID",
        "Account Type",
        "Symbol",
        "Close Type",
        "Realized PNL",
        "Total Realized PNL",
        "Total Funding Fees",
        "Total Trading Fees",
        lambda c: re.match(r"(^Position Opening Time\((UTC[-+]\d{2}:\d{2})\))", c),
        lambda c: re.match(r"(^Position Closing Time\((UTC[-+]\d{2}:\d{2})\))", c),
    ],
    worksheet_name="Kucoin F",
    all_handler=parse_kucoin_futures,
)
