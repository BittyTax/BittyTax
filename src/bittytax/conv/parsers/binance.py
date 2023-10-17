# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...config import config
from ...constants import WARNING
from ...types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import (
    DataFilenameError,
    DataRowError,
    UnexpectedTradingPairError,
    UnexpectedTypeError,
)
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

PRECISION = Decimal("0." + "0" * 8)

WALLET = "Binance"

QUOTE_ASSETS = [
    "ARS",
    "AUD",
    "BIDR",
    "BKRW",
    "BNB",
    "BRL",
    "BTC",
    "BUSD",
    "BVND",
    "DAI",
    "DOGE",
    "DOT",
    "ETH",
    "EUR",
    "FDUSD",
    "GBP",
    "GYEN",
    "IDRT",
    "NGN",
    "PAX",
    "PLN",
    "RON",
    "RUB",
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
    "XRP",
    "ZAR",
]

BASE_ASSETS = ["1INCH", "1INCHDOWN", "1INCHUP"]


def parse_binance_trades(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date(UTC)"])

    base_asset, quote_asset = _split_trading_pair(row_dict["Market"])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(
            parser.in_header.index("Market"), "Market", row_dict["Market"]
        )

    if row_dict["Type"] == "BUY":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=base_asset,
            sell_quantity=Decimal(row_dict["Total"]),
            sell_asset=quote_asset,
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Fee Coin"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "SELL":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Total"]),
            buy_asset=quote_asset,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=base_asset,
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Fee Coin"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def parse_binance_convert(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["Status"] != "Successful":
        return

    base_asset, quote_asset = _split_trading_pair(row_dict["Pair"])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(parser.in_header.index("Pair"), "Pair", row_dict["Pair"])

    data_row.t_record = TransactionOutRecord(
        TrType.TRADE,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Buy"].split(" ")[0]),
        buy_asset=row_dict["Buy"].split(" ")[1],
        sell_quantity=Decimal(row_dict["Sell"].split(" ")[0]),
        sell_asset=row_dict["Sell"].split(" ")[1],
        wallet=WALLET,
    )


def parse_binance_trades_statement(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date(UTC)"])
    fee_quantity, fee_asset = _split_asset(row_dict["Fee"].replace(",", ""))

    if row_dict["Side"] == "BUY":
        buy_quantity, buy_asset = _split_asset(row_dict["Executed"].replace(",", ""))
        sell_quantity, sell_asset = _split_asset(row_dict["Amount"].replace(",", ""))

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["Side"] == "SELL":
        buy_quantity, buy_asset = _split_asset(row_dict["Amount"].replace(",", ""))
        sell_quantity, sell_asset = _split_asset(row_dict["Executed"].replace(",", ""))

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


def _split_trading_pair(trading_pair: str) -> Tuple[Optional[str], Optional[str]]:
    for quote_asset in QUOTE_ASSETS:
        if trading_pair.endswith(quote_asset):
            return trading_pair[: -len(quote_asset)], quote_asset

    return None, None


def _split_asset(amount: str) -> Tuple[Optional[Decimal], str]:
    for base_asset in BASE_ASSETS:
        if amount.endswith(base_asset):
            return Decimal(amount[: -len(base_asset)]), base_asset

    match = re.match(r"([\d|,]*\.\d+)(\w+)$", amount)
    if match:
        return Decimal(match.group(1)), match.group(2)
    return None, ""


def parse_binance_deposits_withdrawals_crypto(
    data_row: "DataRow", _parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(data_row.row[0])

    if row_dict["Status"] != "Completed":
        return

    if "deposit" in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Coin"],
            fee_quantity=Decimal(row_dict["TransactionFee"]),
            fee_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif "withdraw" in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Coin"],
            fee_quantity=Decimal(row_dict["TransactionFee"]),
            fee_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    else:
        raise DataFilenameError(kwargs["filename"], "Transaction Type (Deposit or Withdrawal)")


def parse_binance_deposits_withdrawals_cash(
    data_row: "DataRow", _parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date(UTC)"])

    if row_dict["Status"] != "Successful":
        return

    if "deposit" in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Indicated Amount"]),
            buy_asset=row_dict["Coin"],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif "withdraw" in kwargs["filename"].lower():
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
        raise DataFilenameError(kwargs["filename"], "Transaction Type (Deposit or Withdrawal)")


def parse_binance_statements(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    tx_times: Dict[str, List["DataRow"]] = {}
    for dr in data_rows:
        if dr.row_dict["UTC_Time"] in tx_times:
            tx_times[dr.row_dict["UTC_Time"]].append(dr)
        else:
            tx_times[dr.row_dict["UTC_Time"]] = [dr]

    for data_row in data_rows:
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
            _parse_binance_statements_row(tx_times, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_binance_statements_row(
    tx_times: Dict[str, List["DataRow"]], parser: DataParser, data_row: "DataRow"
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["UTC_Time"])

    if row_dict["Account"].lower() not in ("spot", "earn", "pool"):
        raise UnexpectedTypeError(parser.in_header.index("Account"), "Account", row_dict["Account"])

    if row_dict["Operation"] in (
        "Commission History",
        "Referrer rebates",
        "Commission Rebate",
        "Commission Fee Shared With You",
        "Cash Voucher distribution",
        "Referral Kickback",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.GIFT_RECEIVED,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] == "Distribution":
        if Decimal(row_dict["Change"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.AIRDROP,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Change"]),
                buy_asset=row_dict["Coin"],
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.SPEND,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Change"])),
                sell_asset=row_dict["Coin"],
                wallet=WALLET,
            )
    elif row_dict["Operation"] == "Super BNB Mining":
        data_row.t_record = TransactionOutRecord(
            TrType.MINING,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] in (
        "Savings Interest",
        "Simple Earn Flexible Interest",
        "Pool Distribution",
        "Savings distribution",
        "Savings Distribution",
        "Launchpool Interest",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.INTEREST,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] in (
        "POS savings interest",
        "Staking Rewards",
        "ETH 2.0 Staking Rewards",
        "Liquid Swap rewards",
        "Simple Earn Locked Rewards",
        "DOT Slot Auction Rewards",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.STAKING,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] in ("Small assets exchange BNB", "Small Assets Exchange BNB"):
        _make_trade(row_dict["Operation"], tx_times[row_dict["UTC_Time"]], parser, "BNB")
    elif row_dict["Operation"] == "ETH 2.0 Staking":
        _make_trade(row_dict["Operation"], tx_times[row_dict["UTC_Time"]], parser)
    elif row_dict["Operation"] in (
        "transfer_out",
        "transfer_in",
        "Savings purchase",
        "Simple Earn Flexible Subscription",
        "Savings Principal redemption",
        "Simple Earn Flexible Redemption",
        "POS savings purchase",
        "Staking Purchase",
        "POS savings redemption",
        "Staking Redemption",
        "Simple Earn Locked Subscription",
        "Simple Earn Locked Redemption",
    ):
        # Skip not taxable events
        return
    elif row_dict["Operation"] in (
        "Deposit",
        "Withdraw",
        "Transaction Related",
        "Fiat Deposit",
        "Fiat Withdraw",
        "Buy",
        "Sell",
        "Fee",
        "Transaction Buy",
        "Transaction Fee",
        "Transaction Spend",
        "Transaction Sold",
        "Transaction Revenue",
        "Large OTC trading",
        "Binance Convert",
    ):
        # Skip duplicate operations
        return
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Operation"), "Operation", row_dict["Operation"]
        )


def _make_trade(
    operation: str, tx_times: List["DataRow"], parser: DataParser, default_asset: str = ""
) -> None:
    op_rows = [dr for dr in tx_times if dr.row_dict["Operation"] == operation]
    buy_quantity, buy_asset = _get_buy_quantity(op_rows)

    if not buy_asset:
        buy_asset = default_asset

    sell_rows = [dr for dr in op_rows if not dr.parsed]
    tot_buy_quantity = Decimal(0)

    for cnt, sell_row in enumerate(sell_rows):
        sell_row.timestamp = DataParser.parse_timestamp(sell_row.row_dict["UTC_Time"])
        sell_row.parsed = True

        if buy_quantity and default_asset == "BNB":
            if cnt < len(sell_rows) - 1:
                split_buy_quantity = Decimal(buy_quantity / len(sell_rows)).quantize(PRECISION)
                tot_buy_quantity += split_buy_quantity
            else:
                split_buy_quantity = buy_quantity - tot_buy_quantity

            if config.debug:
                sys.stderr.write(f"{Fore.GREEN}conv: split_buy_quantity={split_buy_quantity}\n")

            sell_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                sell_row.timestamp,
                buy_quantity=split_buy_quantity,
                buy_asset=buy_asset,
                sell_quantity=abs(Decimal(sell_row.row_dict["Change"])),
                sell_asset=sell_row.row_dict["Coin"],
                wallet=WALLET,
            )
        else:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}row[{parser.in_header_row_num + sell_row.line_num}] {sell_row}\n"
                f"{WARNING} {buy_asset} amount is not available, "
                "you will need to add this manually\n"
            )

            sell_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                sell_row.timestamp,
                buy_quantity=buy_quantity,
                buy_asset=buy_asset,
                sell_quantity=abs(Decimal(sell_row.row_dict["Change"])),
                sell_asset=sell_row.row_dict["Coin"],
                wallet=WALLET,
            )


def _get_buy_quantity(op_rows: List["DataRow"]) -> Tuple[Optional[Decimal], str]:
    buy_found = False
    buy_quantity = None
    buy_asset = ""
    sell_assets = 0

    for data_row in op_rows:
        if Decimal(data_row.row_dict["Change"]) > 0:
            data_row.timestamp = DataParser.parse_timestamp(data_row.row_dict["UTC_Time"])
            data_row.parsed = True

            if not buy_found:
                buy_quantity = Decimal(data_row.row_dict["Change"])
                buy_asset = data_row.row_dict["Coin"]
                buy_found = True
            else:
                # Multiple buys, quantity will need to be added manually
                buy_quantity = None
                buy_asset = ""
        else:
            sell_assets += 1

    if sell_assets > 1:
        # Multiple sells, quantity will need to be added manually,
        #  unless configured to evenly split BNB
        if not config.binance_multi_bnb_split_even:
            buy_quantity = None
            buy_asset = ""

    return buy_quantity, buy_asset


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
    row_handler=parse_binance_deposits_withdrawals_crypto,
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
    row_handler=parse_binance_deposits_withdrawals_crypto,
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
    row_handler=parse_binance_deposits_withdrawals_crypto,
)

DataParser(
    ParserType.EXCHANGE,
    "Binance Deposits/Withdrawals",
    [
        "Date(UTC)",
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

DataParser(
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
