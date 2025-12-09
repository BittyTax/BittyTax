# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
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
    "IDR",
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
    "USD",
    "USD1",
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
    "0G",
    "1000CAT",
    "1000CHEEMS",
    "1000SATS",
    "1INCH",
    "1INCHDOWN",
    "1INCHUP",
    "1MBABYDOGE",
    "2Z",
]

TRADINGPAIR_TO_QUOTE_ASSET = {
    "ADAEUR": "EUR",
    "ARBIDR": "IDR",
    "BNBIDR": "IDR",
    "ENAEUR": "EUR",
    "GALAEUR": "EUR",
    "LUNAEUR": "EUR",
    "THETAEUR": "EUR",
    "USDTUSD": "USD",
}


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
    if trading_pair in TRADINGPAIR_TO_QUOTE_ASSET:
        quote_asset = TRADINGPAIR_TO_QUOTE_ASSET[trading_pair]
        base_asset = trading_pair[: -len(quote_asset)]
        return base_asset, quote_asset

    for quote_asset in QUOTE_ASSETS:
        if trading_pair.endswith(quote_asset):
            return trading_pair[: -len(quote_asset)], quote_asset

    return None, None


def _split_asset(amount: str) -> Tuple[Optional[Decimal], str]:
    for base_asset in BASE_ASSETS:
        if amount.endswith(base_asset):
            return Decimal(amount[: -len(base_asset)]), base_asset

    match = re.match(r"(\d+|\d+\.\d+)(\w+)$", amount)
    if match:
        return Decimal(match.group(1)), match.group(2)
    raise RuntimeError(f"Cannot split Quantity from Asset: {amount}")


def parse_binance_deposits_withdrawals_crypto_v2(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(_get_timestamp(row_dict["Date(UTC+0)"]))
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TXID"), tx_dest_pos=parser.in_header.index("Address")
    )

    if row_dict["Status"] != "Completed":
        return

    if "Fee" not in row_dict:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Coin"],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Coin"],
            wallet=WALLET,
        )


def _get_timestamp(timestamp: str) -> str:
    match = re.match(r"^\d{2}-\d{2}-\d{2}.*$", timestamp)

    if match:
        return f"20{timestamp}"
    return timestamp


def parse_binance_deposits_withdrawals_crypto_v1(
    data_row: "DataRow", parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(data_row.row[0])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TXID"), tx_dest_pos=parser.in_header.index("Address")
    )

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
    data_row: "DataRow", parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict

    timestamp_hdr = parser.args[0].group(1)
    utc_offset = parser.args[0].group(2)

    if utc_offset == "UTCnull":
        utc_offset = "UTC"

    data_row.timestamp = DataParser.parse_timestamp(f"{row_dict[timestamp_hdr]} {utc_offset}")

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
    tx_times: Dict[datetime, List["DataRow"]] = {}

    for dr in data_rows:
        dr.timestamp = DataParser.parse_timestamp(dr.row_dict["UTC_Time"])
        if dr.timestamp in tx_times:
            tx_times[dr.timestamp].append(dr)
        else:
            tx_times[dr.timestamp] = [dr]

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
    tx_times: Dict[datetime, List["DataRow"]], parser: DataParser, data_row: "DataRow"
) -> None:
    row_dict = data_row.row_dict

    if row_dict["Account"] in ("USDT-Futures", "USD-MFutures", "USD-M Futures", "Coin-M Futures"):
        _parse_binance_statements_futures_row(tx_times, parser, data_row)
        return

    if row_dict["Account"] in ("Isolated Margin", "CrossMargin", "Cross Margin"):
        _parse_binance_statements_margin_row(tx_times, parser, data_row)
        return

    if row_dict["Account"].lower() not in ("spot", "earn", "pool", "savings", "funding"):
        raise UnexpectedTypeError(parser.in_header.index("Account"), "Account", row_dict["Account"])

    if row_dict["Operation"] in (
        "Commission History",
        "Referrer rebates",
        "Commission Rebate",
        "Commission Fee Shared With You",
        "Referral Kickback",
        "Referral Commission",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.REFERRAL,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] in (
        "Airdrop Assets",
        "Cash Voucher distribution",
        "Simple Earn Flexible Airdrop",
        "Campaign Related Reward",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.AIRDROP,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] in (
        "Distribution",
        "Token Swap - Redenomination/Rebranding",
        "Token Swap - Distribution",
    ):
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
                sell_value=Decimal(0),
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
        "Launchpool Earnings Withdrawal",
        "BNB Vault Rewards",
        "Swap Farming Rewards",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.STAKING_REWARD,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] in ("Asset Recovery", "Leveraged Coin Consolidation"):
        # Replace with REBASE in the future
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Change"])),
            sell_asset=row_dict["Coin"],
            sell_value=Decimal(0),
            wallet=WALLET,
        )
    elif row_dict["Operation"] in ("Small assets exchange BNB", "Small Assets Exchange BNB"):
        if config.binance_multi_bnb_split_even:
            _make_bnb_trade(
                _get_op_rows(tx_times, data_row.timestamp, (row_dict["Operation"],)),
            )
        else:
            _make_trade(
                _get_op_rows(tx_times, data_row.timestamp, (row_dict["Operation"],)),
            )
    elif row_dict["Operation"] in (
        "ETH 2.0 Staking",
        "Leverage Token Redemption",
        "Stablecoins Auto-Conversion",
    ):
        _make_trade(
            _get_op_rows(tx_times, data_row.timestamp, (row_dict["Operation"],)),
        )
    elif row_dict["Operation"] in (
        "Swap Farming Transaction",
        "Liquid Swap Sell",
    ):
        # Trade before a Liquid Swap
        _make_trade(
            _get_op_rows(
                tx_times, data_row.timestamp, ("Swap Farming Transaction", "Liquid Swap Sell")
            ),
        )
    elif row_dict["Operation"] in (
        "transfer_out",
        "transfer_in",
        "Savings purchase",
        "Savings Principal redemption",
        "POS savings purchase",
        "POS savings redemption",
        "Staking Purchase",
        "Staking Redemption",
        "Simple Earn Locked Subscription",
        "Simple Earn Locked Redemption",
        "Transfer Between Spot Account and UM Futures Account",
        "Transfer Between Spot Account and CM Futures Account",
        "Transfer Between Main Account/Futures and Margin Account",
        "Launchpool Subscription/Redemption",
        "Launchpad Subscribe",
        "Simple Earn Flexible Subscription",  # See merger
        "Simple Earn Flexible Redemption",  # See merger
        "Liquid Swap Add",  # See merger
        "Liquid Swap Add/Sell",  # See merger
        "Liquidity Farming Remove",  # See merger
    ):
        # Skip non-taxable events and those which are handled by the merger
        return
    elif row_dict["Operation"] in ("Deposit", "Fiat Deposit"):
        if config.binance_statements_only:
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Change"]),
                buy_asset=row_dict["Coin"],
                wallet=WALLET,
            )
        else:
            # Skip duplicate operations
            return
    elif row_dict["Operation"] == "Send":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Change"])),
            sell_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] in ("Withdraw", "Fiat Withdraw"):
        if config.binance_statements_only:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Change"])),
                sell_asset=row_dict["Coin"],
                wallet=WALLET,
            )
        else:
            # Skip duplicate operations
            return
    elif row_dict["Operation"] in ("Binance Convert", "Large OTC trading"):
        if config.binance_statements_only:
            _make_trade(
                _get_op_rows(tx_times, data_row.timestamp, (row_dict["Operation"],)),
            )
        else:
            # Skip duplicate operations
            return
    elif row_dict["Operation"] in (
        "Buy",
        "Sell",
        "Fee",
        "Transaction Related",
        "Transaction Buy",
        "Transaction Fee",
        "Transaction Spend",
        "Transaction Sold",
        "Transaction Revenue",
    ):
        if config.binance_statements_only:
            _make_trade_with_fee(
                _get_op_rows(
                    tx_times,
                    data_row.timestamp,
                    (
                        "Buy",
                        "Sell",
                        "Fee",
                        "Transaction Related",
                        "Transaction Buy",
                        "Transaction Fee",
                        "Transaction Spend",
                        "Transaction Sold",
                        "Transaction Revenue",
                    ),
                ),
            )
        else:
            # Skip duplicate operations
            return
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Operation"), "Operation", row_dict["Operation"]
        )


def _parse_binance_statements_futures_row(
    tx_times: Dict[datetime, List["DataRow"]], parser: DataParser, data_row: "DataRow"
) -> None:
    row_dict = data_row.row_dict

    if row_dict["Operation"] in ("Realize profit and loss", "Realized Profit and Loss"):
        if Decimal(row_dict["Change"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_GAIN,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Change"]),
                buy_asset=row_dict["Coin"],
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_LOSS,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Change"])),
                sell_asset=row_dict["Coin"],
                wallet=WALLET,
            )
    elif row_dict["Operation"] in ("Fee", "Insurance Fund Compensation"):
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Change"])),
            sell_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] == "Funding Fee":
        if Decimal(row_dict["Change"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_FEE_REBATE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Change"]),
                buy_asset=row_dict["Coin"],
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_FEE,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Change"])),
                sell_asset=row_dict["Coin"],
                wallet=WALLET,
            )
    elif row_dict["Operation"] in ("Referrer rebates", "Referee rebates"):
        data_row.t_record = TransactionOutRecord(
            TrType.REFERRAL,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] in ("Asset Conversion Transfer", "Futures Convert"):
        _make_trade(
            _get_op_rows(tx_times, data_row.timestamp, (row_dict["Operation"],)),
        )
    elif row_dict["Operation"] in (
        "transfer_out",
        "transfer_in",
        "Transfer Between Spot Account and UM Futures Account",
        "Transfer Between Spot Account and CM Futures Account",
        "Transfer Between Main Account/Futures and Margin Account",
    ):
        # Skip not taxable events
        return
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Operation"), "Operation", row_dict["Operation"]
        )


def _parse_binance_statements_margin_row(
    tx_times: Dict[datetime, List["DataRow"]], parser: DataParser, data_row: "DataRow"
) -> None:
    row_dict = data_row.row_dict

    if row_dict["Operation"] in ("Margin loan", "Margin Loan", "Isolated Margin Loan"):
        data_row.t_record = TransactionOutRecord(
            TrType.LOAN,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] in ("Margin Repayment", "Isolated Margin Repayment"):
        data_row.t_record = TransactionOutRecord(
            TrType.LOAN_REPAYMENT,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Change"])),
            sell_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] in (
        "Buy",
        "Sell",
        "Fee",
        "Transaction Buy",
        "Transaction Fee",
        "Transaction Spend",
        "Transaction Sold",
        "Transaction Revenue",
    ):
        _make_trade_with_fee(
            _get_op_rows(
                tx_times,
                data_row.timestamp,
                (
                    "Buy",
                    "Sell",
                    "Fee",
                    "Transaction Buy",
                    "Transaction Fee",
                    "Transaction Spend",
                    "Transaction Sold",
                    "Transaction Revenue",
                ),
            ),
        )

    elif row_dict["Operation"] == "Transfer Between Main Account/Futures and Margin Account":
        # Skip not taxable events
        return
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Operation"), "Operation", row_dict["Operation"]
        )


def parse_binance_futures(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    tx_ids: Dict[str, List["DataRow"]] = {}
    for dr in data_rows:
        dr.timestamp = DataParser.parse_timestamp(dr.row_dict["Date(UTC)"])
        # Normalise fields to be compatible with Statements functions
        dr.row_dict["Operation"] = dr.row_dict["type"]
        dr.row_dict["Change"] = dr.row_dict["Amount"]
        dr.row_dict["Coin"] = dr.row_dict["Asset"]

        if dr.row_dict["Transaction ID"] in tx_ids:
            tx_ids[dr.row_dict["Transaction ID"]].append(dr)
        else:
            tx_ids[dr.row_dict["Transaction ID"]] = [dr]

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
            _parse_binance_futures_row(tx_ids, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_binance_futures_row(
    tx_ids: Dict[str, List["DataRow"]], parser: DataParser, data_row: "DataRow"
) -> None:
    row_dict = data_row.row_dict

    if row_dict["type"] == "REALIZED_PNL":
        if Decimal(row_dict["Amount"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_GAIN,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount"]),
                buy_asset=row_dict["Asset"],
                wallet=WALLET,
                note=row_dict["Symbol"],
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_LOSS,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Amount"])),
                sell_asset=row_dict["Asset"],
                wallet=WALLET,
                note=row_dict["Symbol"],
            )
    elif row_dict["type"] == "COMMISSION":
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=row_dict["Asset"],
            wallet=WALLET,
            note=row_dict["Symbol"],
        )
    elif row_dict["type"] == "FUNDING_FEE":
        if Decimal(row_dict["Amount"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_FEE_REBATE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount"]),
                buy_asset=row_dict["Asset"],
                wallet=WALLET,
                note=row_dict["Symbol"],
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_FEE,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Amount"])),
                sell_asset=row_dict["Asset"],
                wallet=WALLET,
                note=row_dict["Symbol"],
            )
    elif row_dict["type"] in ("COIN_SWAP_DEPOSIT", "COIN_SWAP_WITHDRAW"):
        _make_trade(tx_ids[row_dict["Transaction ID"]])
    elif row_dict["type"] in ("DEPOSIT", "WITHDRAW", "TRANSFER"):
        # Skip transfers
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def _get_op_rows(
    tx_times: Dict[datetime, List["DataRow"]],
    timestamp: datetime,
    operations: Tuple[str, ...],
) -> List["DataRow"]:
    timestamp_next_second = timestamp + timedelta(seconds=1)

    if timestamp_next_second in tx_times:
        tx_period = tx_times[timestamp] + tx_times[timestamp_next_second]
    else:
        tx_period = tx_times[timestamp]

    return [dr for dr in tx_period if dr.row_dict["Operation"] in operations and not dr.parsed]


def _make_bnb_trade(op_rows: List["DataRow"]) -> None:
    buy_quantity = _get_bnb_quantity(op_rows)
    sell_rows = [dr for dr in op_rows if not dr.parsed]
    tot_buy_quantity = Decimal(0)

    for cnt, sell_row in enumerate(sell_rows):
        sell_row.parsed = True

        if buy_quantity:
            if cnt < len(sell_rows) - 1:
                split_buy_quantity = Decimal(buy_quantity / len(sell_rows)).quantize(PRECISION)
                tot_buy_quantity += split_buy_quantity
            else:
                split_buy_quantity = buy_quantity - tot_buy_quantity

            if config.debug:
                sys.stderr.write(f"{Fore.GREEN}conv: split_buy_quantity={split_buy_quantity}\n")
        else:
            split_buy_quantity = None

        sell_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            sell_row.timestamp,
            buy_quantity=split_buy_quantity,
            buy_asset="BNB",
            sell_quantity=abs(Decimal(sell_row.row_dict["Change"])),
            sell_asset=sell_row.row_dict["Coin"],
            wallet=WALLET,
        )


def _get_bnb_quantity(op_rows: List["DataRow"]) -> Optional[Decimal]:
    buy_quantity = None

    for data_row in op_rows:
        if Decimal(data_row.row_dict["Change"]) > 0:
            data_row.parsed = True

            if data_row.row_dict["Coin"] != "BNB":
                continue

            if buy_quantity is None:
                buy_quantity = Decimal(data_row.row_dict["Change"])
            else:
                buy_quantity += Decimal(data_row.row_dict["Change"])

    return buy_quantity


def _make_trade(op_rows: List["DataRow"]) -> None:
    buy_quantity = sell_quantity = None
    buy_asset = sell_asset = ""
    trade_row = None

    for data_row in op_rows:
        row_dict = data_row.row_dict

        if Decimal(row_dict["Change"]) > 0:
            if buy_quantity is None:
                buy_quantity = Decimal(row_dict["Change"])
                buy_asset = row_dict["Coin"]
                data_row.parsed = True

        if Decimal(row_dict["Change"]) <= 0:
            if sell_quantity is None:
                sell_quantity = abs(Decimal(row_dict["Change"]))
                sell_asset = row_dict["Coin"]
                data_row.parsed = True

        if not trade_row:
            trade_row = data_row

        if buy_quantity and sell_quantity:
            break

    if trade_row:
        trade_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            trade_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            wallet=WALLET,
        )


def _make_trade_with_fee(op_rows: List["DataRow"]) -> None:
    buy_quantity = sell_quantity = fee_quantity = None
    buy_asset = sell_asset = fee_asset = ""
    trade_row = None

    for data_row in op_rows:
        row_dict = data_row.row_dict

        if Decimal(row_dict["Change"]) > 0:
            if buy_quantity is None:
                buy_quantity = Decimal(row_dict["Change"])
                buy_asset = row_dict["Coin"]
                data_row.parsed = True

        if Decimal(row_dict["Change"]) <= 0:
            if row_dict["Operation"] in ("Fee", "Transaction Fee"):
                if fee_quantity is None:
                    fee_quantity = abs(Decimal(row_dict["Change"]))
                    fee_asset = row_dict["Coin"]
                    data_row.parsed = True
            else:
                if sell_quantity is None:
                    sell_quantity = abs(Decimal(row_dict["Change"]))
                    sell_asset = row_dict["Coin"]
                    data_row.parsed = True

        if not trade_row:
            trade_row = data_row

        if buy_quantity and sell_quantity and fee_quantity:
            break

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
