# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re

from ...dataparser import DataParser, ParserType
from .parse_binance_convert import parse_binance_convert
from .parse_binance_deposits_withdrawals_cash import parse_binance_deposits_withdrawals_cash
from .parse_binance_deposits_withdrawals_crypto_v1 import (
    parse_binance_deposits_withdrawals_crypto_v1,
)
from .parse_binance_deposits_withdrawals_crypto_v2 import (
    parse_binance_deposits_withdrawals_crypto_v2,
)
from .parse_binance_futures import parse_binance_futures
from .parse_binance_statements import parse_binance_statements

# Import handler functions from sub-modules
from .parse_binance_trades import parse_binance_trades
from .parse_binance_trades_statement import parse_binance_trades_statement

DataParser(
    ParserType.EXCHANGE,
    "Binance Trades",
    ["Date(UTC)", "Market", "Type", "Price", "Amount", "Total", "Fee", "Fee Coin"],
    worksheet_name="Binance T",
    row_handler=parse_binance_trades,
)

DataParser(
    ParserType.EXCHANGE,
    "Binance Trades",
    [
        "Date",
        "Pair",
        "Type",
        "Sell",
        "Buy",
        "Price",
        "Inverse Price",
        "Date Updated",
        "Status",
    ],
    worksheet_name="Binance T",
    row_handler=parse_binance_convert,
)

DataParser(
    ParserType.EXCHANGE,
    "Binance Trades",
    [
        "Date",
        "Wallet",
        "Pair",
        "Type",
        "Sell",
        "Buy",
        "Price",
        "Inverse Price",
        "Date Updated",
        "Status",
    ],
    worksheet_name="Binance T",
    row_handler=parse_binance_convert,
)

DataParser(
    ParserType.EXCHANGE,
    "Binance Trades",
    ["Date(UTC)", "Pair", "Side", "Price", "Executed", "Amount", "Fee"],
    worksheet_name="Binance T",
    row_handler=parse_binance_trades_statement,
)

DataParser(
    ParserType.EXCHANGE,
    "Binance Deposits",
    ["Date(UTC+0)", "Coin", "Network", "Amount", "Address", "TXID", "Status"],
    worksheet_name="Binance D,W",
    row_handler=parse_binance_deposits_withdrawals_crypto_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "Binance Withdrawals",
    ["Date(UTC+0)", "Coin", "Network", "Amount", "Fee", "Address", "TXID", "Status"],
    worksheet_name="Binance D,W",
    row_handler=parse_binance_deposits_withdrawals_crypto_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "Binance Deposits/Withdrawals",
    [
        "Date(UTC)",
        "Coin",
        "Network",
        "Amount",
        "TransactionFee",
        "Address",
        "TXID",
        "SourceAddress",
        "PaymentID",
        "Status",
    ],
    worksheet_name="Binance D,W",
    row_handler=parse_binance_deposits_withdrawals_crypto_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "Binance Deposits/Withdrawals",
    [
        "Date(UTC)",
        "Coin",
        "Amount",
        "TransactionFee",
        "Address",
        "TXID",
        "SourceAddress",
        "PaymentID",
        "Status",
    ],
    worksheet_name="Binance D,W",
    row_handler=parse_binance_deposits_withdrawals_crypto_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "Binance Deposits/Withdrawals",
    [
        "Date",
        "Coin",
        "Amount",
        "TransactionFee",
        "Address",
        "TXID",
        "SourceAddress",
        "PaymentID",
        "Status",
    ],
    worksheet_name="Binance D,W",
    row_handler=parse_binance_deposits_withdrawals_crypto_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "Binance Deposits/Withdrawals",
    [
        lambda c: re.match(r"(^Date\((UTC|UTCnull|UTC[-+]\d{1,2})\))", c),
        "Coin",
        "Amount",
        "Status",
        "Payment Method",
        "Indicated Amount",
        "Fee",
        "Order ID",
    ],
    worksheet_name="Binance D,W",
    row_handler=parse_binance_deposits_withdrawals_cash,
)

statements = DataParser(
    ParserType.EXCHANGE,
    "Binance Statements",
    ["User_ID", "UTC_Time", "Account", "Operation", "Coin", "Change", "Remark"],
    worksheet_name="Binance S",
    all_handler=parse_binance_statements,
)

DataParser(
    ParserType.EXCHANGE,
    "Binance Statements",
    ["UTC_Time", "Account", "Operation", "Coin", "Change", "Remark"],
    worksheet_name="Binance S",
    all_handler=parse_binance_statements,
)

DataParser(
    ParserType.EXCHANGE,
    "Binance Futures",
    ["Date(UTC)", "type", "Amount", "Asset", "Symbol", "Transaction ID"],
    worksheet_name="Binance F",
    all_handler=parse_binance_futures,
)
