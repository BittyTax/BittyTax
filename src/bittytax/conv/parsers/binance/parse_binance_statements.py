from datetime import datetime, timedelta
from decimal import Decimal
from sys import stderr
from typing import TYPE_CHECKING, Dict, List, Optional

from colorama import Fore

from ....bt_types import TrType
from ....config import config
from ...exceptions import DataRowError, UnexpectedTypeError
from ...out_record import TransactionOutRecord
from .utils import PRECISION, WALLET

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from ...dataparser import DataParser, ParserArgs
    from ...datarow import DataRow

def _get_op_rows(
    tx_times: Dict[datetime, List["DataRow"]],
    timestamp: datetime,
    operations: tuple[str, ...],
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
                stderr.write(f"{Fore.GREEN}conv: split_buy_quantity={split_buy_quantity}\n")
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


def _parse_binance_statements_row(
    tx_times: Dict[datetime, List["DataRow"]], parser: "DataParser", data_row: "DataRow"
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
        "Launchpool Airdrop",
        "HODLer Airdrops Distribution",
        "Megadrop Rewards",
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
            TrType.STAKING,
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
    elif row_dict["Operation"] in (
        "Small assets exchange BNB",
        "Small Assets Exchange BNB",
        "BNB Fee Deduction",
    ):
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
        # Trade before a Liquid Swap
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
        "Transfer Between Main and Funding Wallet",
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
    elif row_dict["Operation"] == "Binance Card Spending":
        if Decimal(row_dict["Change"]) < 0:
            data_row.t_record = TransactionOutRecord(
                TrType.SPEND,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Change"])),
                sell_asset=row_dict["Coin"],
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.CASHBACK,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Change"]),
                buy_asset=row_dict["Coin"],
                wallet=WALLET,
            )
    elif row_dict["Operation"] == "Binance Card Cashback":
        data_row.t_record = TransactionOutRecord(
            TrType.CASHBACK,
            data_row.timestamp,
            buy_quantity=abs(Decimal(row_dict["Change"])),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] in (
        "Crypto - Asset Transfer",
        "Fiat OCBS - Add Fiat and Fees",
        "Asset - Transfer",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] == "Crypto Box":
        data_row.t_record = TransactionOutRecord(
            TrType.GIFT_RECEIVED,
            data_row.timestamp,
            buy_quantity=abs(Decimal(row_dict["Change"])),
            buy_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif row_dict["Operation"] in (
        "Withdraw",
        "Fiat Withdraw",
        "Fiat Withdrawal",
    ):
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
    elif row_dict["Operation"] == "Buy Crypto With Card":
        _make_trade(
            _get_op_rows(tx_times, data_row.timestamp, (row_dict["Operation"],)),
        )
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
    tx_times: Dict[datetime, List["DataRow"]], parser: "DataParser", data_row: "DataRow"
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
    elif row_dict["Operation"] in ("Funding Fee", "Insurance Fund Refund"):
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
    tx_times: Dict[datetime, List["DataRow"]], parser: "DataParser", data_row: "DataRow"
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
    elif row_dict["Operation"] in (
        "Margin Repayment",
        "Isolated Margin Repayment",
        "Cross Margin Liquidation - Repayment",
    ):
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
    elif row_dict["Operation"] in (
        "Small assets exchange BNB",
        "Small Assets Exchange BNB",
        "BNB Fee Deduction",
    ):
        if config.binance_multi_bnb_split_even:
            _make_bnb_trade(
                _get_op_rows(tx_times, data_row.timestamp, (row_dict["Operation"],)),
            )
        else:
            _make_trade(
                _get_op_rows(tx_times, data_row.timestamp, (row_dict["Operation"],)),
            )
    elif row_dict["Operation"] == "Transfer Between Main Account/Futures and Margin Account":
        # Skip not taxable events
        return
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Operation"), "Operation", row_dict["Operation"]
        )


def parse_binance_statements(
    data_rows: List["DataRow"], parser: "DataParser", **_kwargs: "Unpack[ParserArgs]"
) -> None:
    tx_times: Dict[datetime, List["DataRow"]] = {}

    for dr in data_rows:
        dr.timestamp = parser.parse_timestamp(dr.row_dict["UTC_Time"])
        if dr.timestamp in tx_times:
            tx_times[dr.timestamp].append(dr)
        else:
            tx_times[dr.timestamp] = [dr]

    for data_row in data_rows:
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            stderr.write(
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
