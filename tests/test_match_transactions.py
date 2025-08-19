import copy
from decimal import Decimal
from typing import List, Optional, Tuple, Union, cast

from bittytax.bt_types import (
    AssetSymbol,
    CostBasisMethod,
    DisposalType,
    Note,
    TaxRules,
    Timestamp,
    TrType,
    Wallet,
)
from bittytax.config import config
from bittytax.price.valueasset import ValueAsset
from bittytax.t_record import TransactionRecord
from bittytax.t_row import TransactionRow
from bittytax.tax import TaxCalculator
from bittytax.tax_event import TaxEventCapitalGains
from bittytax.transactions import Buy, Sell, TransactionHistory

config.ccy = "USD"
config.debug = True
config.config["local_timezone"] = "America/New_York"
config.config["date_is_day_first"] = True
config.config["cost_basis_zero_if_missing"] = True

# Remove all data sources since no price looks are required
config.config["data_source_fiat"] = []
config.config["data_source_crypto"] = []
config.config["data_source_select"] = {}


def add_buy(
    quantity: float,
    asset: str,
    value: float,
    wallet: str,
    timestamp: str,
    fee: Optional[float] = None,
) -> TransactionRecord:
    buy = TransactionRow(
        [
            TrType.TRADE.value,
            str(quantity),
            asset,
            str(value),
            str(value),
            config.ccy,
            str(value),
            str(fee) if fee is not None else "",
            config.ccy if fee is not None else "",
            str(fee) if fee is not None else "",
            wallet,
            timestamp,
            "",
        ],
        1,
    )
    buy.parse()
    assert buy.t_record
    return buy.t_record


def add_sell(
    quantity: float,
    asset: str,
    value: float,
    wallet: str,
    timestamp: str,
    fee: Optional[float] = None,
) -> TransactionRecord:
    sell = TransactionRow(
        [
            TrType.TRADE.value,
            str(value),
            config.ccy,
            str(value),
            str(quantity),
            asset,
            str(value),
            str(fee) if fee is not None else "",
            config.ccy if fee is not None else "",
            str(fee) if fee is not None else "",
            wallet,
            timestamp,
            "",
        ],
        1,
    )
    sell.parse()
    assert sell.t_record
    return sell.t_record


def get_transactions(transaction_records: List[TransactionRecord]) -> List[Union[Buy, Sell]]:
    transaction_records.sort()

    TransactionRecord.cnt = 0
    for t_record in transaction_records:
        t_record.set_tid()

    return TransactionHistory(transaction_records, ValueAsset()).transactions


def make_buy(
    quantity: float,
    asset: str,
    value: float,
    wallet: str,
    timestamp: Timestamp,
    fee: Optional[float] = None,
    tid: Optional[List[int]] = None,
) -> Buy:
    buy = Buy(TrType.TRADE, Decimal(quantity), AssetSymbol(asset), Decimal(value))
    buy.timestamp = timestamp
    buy.matched = True
    buy.wallet = Wallet(wallet)
    if fee is not None:
        buy.fee_value = Decimal(fee)
    if value == Decimal(0):
        buy.note = Note("Added as cost basis zero")
    if tid:
        buy.tid = tid
    return buy


def do_match(
    transactions: List[Union[Buy, Sell]], tax_rules: TaxRules
) -> Tuple[TaxCalculator, List[TaxEventCapitalGains]]:
    tax = TaxCalculator(transactions, tax_rules)
    tax.order_transactions()
    if tax_rules is TaxRules.US_INDIVIDUAL_FIFO:
        tax.match_transactions(CostBasisMethod.FIFO)
    elif tax_rules is TaxRules.US_INDIVIDUAL_LIFO:
        tax.match_transactions(CostBasisMethod.LIFO)
    elif tax_rules is TaxRules.US_INDIVIDUAL_HIFO:
        tax.match_transactions(CostBasisMethod.HIFO)
    elif tax_rules is TaxRules.US_INDIVIDUAL_LOFO:
        tax.match_transactions(CostBasisMethod.LOFO)
    else:
        raise RuntimeError(f"Unexpected tax_rules: {tax_rules}")

    tax_events = []
    for _, events in tax.tax_events.items():
        tax_events.extend(cast(List[TaxEventCapitalGains], events))

    return tax, tax_events


def test_fifo_1() -> None:
    tr_buy1 = add_buy(1, "BTC", 18000, "Main", "2023-02-27 12:00:00")
    tr_buy2 = add_buy(1, "BTC", 50000, "Main", "2024-01-01 12:00:00")
    tr_sell1 = add_sell(3.5, "BTC", 70000, "Main", "2023-02-28 22:01:11")
    tr_sell2 = add_sell(1, "BTC", 70000, "Main", "2024-03-28 22:01:11")
    tr_buy3 = add_buy(1, "BTC", 600000, "Main", "2024-04-01 12:00:00")
    tr_buy4 = add_buy(1, "BTC", 18000, "Main", "2018-01-01 12:00:00")
    transactions = get_transactions([tr_buy1, tr_buy2, tr_sell1, tr_sell2, tr_buy3, tr_buy4])

    # Keep copy of buys/sells to detect any changes
    buy1 = copy.deepcopy(tr_buy1.buy)
    buy2 = copy.deepcopy(tr_buy2.buy)
    sell1 = copy.deepcopy(tr_sell1.sell)
    sell2 = copy.deepcopy(tr_sell2.sell)
    buy3 = copy.deepcopy(tr_buy3.buy)
    buy4 = copy.deepcopy(tr_buy4.buy)
    assert buy1
    assert buy2
    assert sell1
    assert sell2
    assert buy3
    assert buy4

    tax, tax_events = do_match(transactions, TaxRules.US_INDIVIDUAL_FIFO)

    assert len(tax_events) == 3
    assert tax_events[0].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[0].cost == 18000
    assert tax_events[0].proceeds == 50000
    assert str(tax_events[0].sell) == str(sell1)
    z_buy1 = make_buy(1.5, "BTC", 0, "", sell1.timestamp)
    assert [str(b) for b in tax_events[0].buys] == [str(buy1), str(z_buy1)]

    assert tax_events[1].disposal_type is DisposalType.LONG_TERM
    assert tax_events[1].cost == 18000
    assert tax_events[1].proceeds == 20000
    assert str(tax_events[1].sell) == str(sell1)
    assert [str(b) for b in tax_events[1].buys] == [str(buy4)]

    assert tax_events[2].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[2].cost == 50000
    assert tax_events[2].proceeds == 70000
    assert str(tax_events[2].sell) == str(sell2)
    assert [str(b) for b in tax_events[2].buys] == [str(buy2)]

    assert tr_buy1.buy and tr_buy1.buy.matched is True
    assert tr_buy2.buy and tr_buy2.buy.matched is True
    assert tr_sell1.sell and tr_sell1.sell.matched is True
    assert tr_sell2.sell and tr_sell2.sell.matched is True
    assert tr_buy3.buy and tr_buy3.buy.matched is False
    assert tr_buy4.buy and tr_buy4.buy.matched is True

    assert [str(b) for b in tax.buy_queue[AssetSymbol("BTC")].buys] == [
        str(buy4),
        str(buy1),
        str(buy2),
        str(buy3),
        str(z_buy1),
    ]


def test_fifo_2() -> None:
    tr_buy1 = add_buy(1, "BTC", 18000, "Main", "2023-02-27 12:00:00")
    tr_buy2 = add_buy(4, "BTC", 200000, "Main", "2024-01-01 12:00:00")
    tr_sell1 = add_sell(3.5, "BTC", 70000, "Main", "2023-02-28 22:01:11")
    tr_sell2 = add_sell(1, "BTC", 70000, "Main", "2024-03-28 22:01:11")
    tr_buy3 = add_buy(1, "BTC", 600000, "Main", "2024-04-01 12:00:00")
    tr_buy4 = add_buy(1, "BTC", 18000, "Main", "2018-01-01 12:00:00")
    transactions = get_transactions([tr_buy1, tr_buy2, tr_sell1, tr_sell2, tr_buy3, tr_buy4])

    # Keep copy of buys/sells to detect any changes
    buy1 = copy.deepcopy(tr_buy1.buy)
    buy2 = copy.deepcopy(tr_buy2.buy)
    sell1 = copy.deepcopy(tr_sell1.sell)
    sell2 = copy.deepcopy(tr_sell2.sell)
    buy3 = copy.deepcopy(tr_buy3.buy)
    buy4 = copy.deepcopy(tr_buy4.buy)
    assert buy1
    assert buy2
    assert sell1
    assert sell2
    assert buy3
    assert buy4

    tax, tax_events = do_match(transactions, TaxRules.US_INDIVIDUAL_FIFO)

    assert len(tax_events) == 3
    assert tax_events[0].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[0].cost == 18000
    assert tax_events[0].proceeds == 50000
    assert str(tax_events[0].sell) == str(sell1)
    z_buy1 = make_buy(1.5, "BTC", 0, "", sell1.timestamp)
    assert [str(b) for b in tax_events[0].buys] == [str(buy1), str(z_buy1)]

    assert tax_events[1].disposal_type is DisposalType.LONG_TERM
    assert tax_events[1].cost == 18000
    assert tax_events[1].proceeds == 20000
    assert str(tax_events[1].sell) == str(sell1)
    assert [str(b) for b in tax_events[1].buys] == [str(buy4)]

    assert tax_events[2].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[2].cost == 50000
    assert tax_events[2].proceeds == 70000
    assert str(tax_events[2].sell) == str(sell2)
    s_buy2_1 = make_buy(1, "BTC", 50000, buy2.wallet, buy2.timestamp, tid=[4, 3])
    s_buy2_2 = make_buy(3, "BTC", 150000, buy2.wallet, buy2.timestamp, tid=[4, 4])
    assert [str(b) for b in tax_events[2].buys] == [str(s_buy2_1)]

    assert tr_buy1.buy and tr_buy1.buy.matched is True
    assert tr_buy2.buy and tr_buy2.buy.matched is True
    assert tr_sell1.sell and tr_sell1.sell.matched is True
    assert tr_sell2.sell and tr_sell2.sell.matched is True
    assert tr_buy3.buy and tr_buy3.buy.matched is False
    assert tr_buy4.buy and tr_buy4.buy.matched is True

    assert [str(b) for b in tax.buy_queue[AssetSymbol("BTC")].buys] == [
        str(buy4),
        str(buy1),
        str(s_buy2_1),
        str(buy3),
        str(z_buy1),
        str(s_buy2_2),
    ]


def test_hifo_1() -> None:
    tr_buy1 = add_buy(2, "BTC", 4950, "Main", "2017-09-22 00:00:00", 50)
    tr_buy2 = add_buy(1, "BTC", 1990, "Main", "2018-01-06 00:00:00", 10)
    tr_buy3 = add_buy(1, "BTC", 7920, "Main", "2018-04-19 00:00:00", 80)
    tr_sell1 = add_sell(1, "BTC", 4040, "Main", "2018-05-03 00:00:00", 40)
    tr_sell2 = add_sell(1, "BTC", 6060, "Main", "2018-06-11 00:00:00", 60)
    tr_sell3 = add_sell(1, "BTC", 2020, "Main", "2018-08-01 00:00:00", 20)
    transactions = get_transactions([tr_buy1, tr_buy2, tr_buy3, tr_sell1, tr_sell2, tr_sell3])

    # Keep copy of buys/sells to detect any changes
    buy1 = copy.deepcopy(tr_buy1.buy)
    buy2 = copy.deepcopy(tr_buy2.buy)
    buy3 = copy.deepcopy(tr_buy3.buy)
    sell1 = copy.deepcopy(tr_sell1.sell)
    sell2 = copy.deepcopy(tr_sell2.sell)
    sell3 = copy.deepcopy(tr_sell3.sell)
    assert buy1
    assert buy2
    assert buy3
    assert sell1
    assert sell2
    assert sell3

    tax, tax_events = do_match(transactions, TaxRules.US_INDIVIDUAL_HIFO)

    assert len(tax_events) == 3
    assert tax_events[0].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[0].cost == 8000
    assert tax_events[0].proceeds == 4000
    assert str(tax_events[0].sell) == str(sell1)
    assert [str(b) for b in tax_events[0].buys] == [str(buy3)]

    assert tax_events[1].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[1].cost == 2500
    assert tax_events[1].proceeds == 6000
    assert str(tax_events[1].sell) == str(sell2)
    s_buy1_1 = make_buy(1, "BTC", 2475, buy1.wallet, buy1.timestamp, fee=25, tid=[1, 4])
    s_buy1_2 = make_buy(1, "BTC", 2475, buy1.wallet, buy1.timestamp, fee=25, tid=[1, 5])
    assert [str(b) for b in tax_events[1].buys] == [str(s_buy1_1)]

    assert tax_events[2].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[2].cost == 2500
    assert tax_events[2].proceeds == 2000
    assert str(tax_events[2].sell) == str(sell3)
    assert [str(b) for b in tax_events[2].buys] == [str(s_buy1_2)]

    assert tr_buy1.buy and tr_buy1.buy.matched is True
    assert tr_buy2.buy and tr_buy2.buy.matched is False
    assert tr_buy3.buy and tr_buy3.buy.matched is True
    assert tr_sell1.sell and tr_sell1.sell.matched is True
    assert tr_sell2.sell and tr_sell2.sell.matched is True
    assert tr_sell3.sell and tr_sell3.sell.matched is True

    assert [str(b) for b in tax.buy_queue[AssetSymbol("BTC")].buys] == [
        str(s_buy1_1),
        str(buy2),
        str(buy3),
        str(s_buy1_2),
    ]


def test_hifo_2() -> None:
    tr_buy1 = add_buy(2, "BTC", 5000, "Main", "2017-09-22 00:00:00")
    tr_buy2 = add_buy(1, "BTC", 2000, "Main", "2018-01-06 00:00:00")
    tr_buy3 = add_buy(1, "BTC", 8000, "Main", "2018-04-19 00:00:00")
    tr_sell1 = add_sell(1, "BTC", 4000, "Main", "2018-05-03 00:00:00")
    tr_sell2 = add_sell(1, "BTC", 6000, "Main", "2018-06-11 00:00:00")
    tr_sell3 = add_sell(1, "BTC", 2000, "Main", "2018-08-01 00:00:00")
    transactions = get_transactions([tr_buy1, tr_buy2, tr_buy3, tr_sell1, tr_sell2, tr_sell3])

    # Keep copy of buys/sells to detect any changes
    buy1 = copy.deepcopy(tr_buy1.buy)
    buy2 = copy.deepcopy(tr_buy2.buy)
    buy3 = copy.deepcopy(tr_buy3.buy)
    sell1 = copy.deepcopy(tr_sell1.sell)
    sell2 = copy.deepcopy(tr_sell2.sell)
    sell3 = copy.deepcopy(tr_sell3.sell)
    assert buy1
    assert buy2
    assert buy3
    assert sell1
    assert sell2
    assert sell3

    tax, tax_events = do_match(transactions, TaxRules.US_INDIVIDUAL_HIFO)

    assert len(tax_events) == 3
    assert tax_events[0].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[0].cost == 8000
    assert tax_events[0].proceeds == 4000
    assert str(tax_events[0].sell) == str(sell1)
    assert [str(b) for b in tax_events[0].buys] == [str(buy3)]

    assert tax_events[1].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[1].cost == 2500
    assert tax_events[1].proceeds == 6000
    assert str(tax_events[1].sell) == str(sell2)
    s_buy1_1 = make_buy(1, "BTC", 2500, buy1.wallet, buy1.timestamp, tid=[1, 3])
    s_buy1_2 = make_buy(1, "BTC", 2500, buy1.wallet, buy1.timestamp, tid=[1, 4])
    assert [str(b) for b in tax_events[1].buys] == [str(s_buy1_1)]

    assert tax_events[2].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[2].cost == 2500
    assert tax_events[2].proceeds == 2000
    assert str(tax_events[2].sell) == str(sell3)
    assert [str(b) for b in tax_events[2].buys] == [str(s_buy1_2)]

    assert tr_buy1.buy and tr_buy1.buy.matched is True
    assert tr_buy2.buy and tr_buy2.buy.matched is False
    assert tr_buy3.buy and tr_buy3.buy.matched is True
    assert tr_sell1.sell and tr_sell1.sell.matched is True
    assert tr_sell2.sell and tr_sell2.sell.matched is True
    assert tr_sell3.sell and tr_sell3.sell.matched is True

    assert [str(b) for b in tax.buy_queue[AssetSymbol("BTC")].buys] == [
        str(s_buy1_1),
        str(buy2),
        str(buy3),
        str(s_buy1_2),
    ]


def test_lifo_1() -> None:
    tr_buy1 = add_buy(2, "BTC", 4950, "Main", "2017-09-22 12:00:00", 50)
    tr_buy2 = add_buy(1, "BTC", 1990, "Main", "2018-01-06 12:00:00", 10)
    tr_buy3 = add_buy(1, "BTC", 7920, "Main", "2018-04-19 12:00:00", 80)
    tr_sell1 = add_sell(1, "BTC", 4040, "Main", "2018-05-03 12:00:00", 40)
    tr_sell2 = add_sell(1, "BTC", 6060, "Main", "2018-06-11 12:00:00", 60)
    tr_sell3 = add_sell(1, "BTC", 2020, "Main", "2018-08-01 12:00:00", 20)
    transactions = get_transactions([tr_buy1, tr_buy2, tr_buy3, tr_sell1, tr_sell2, tr_sell3])

    # Keep copy of buys/sells to detect any changes
    buy1 = copy.deepcopy(tr_buy1.buy)
    buy2 = copy.deepcopy(tr_buy2.buy)
    buy3 = copy.deepcopy(tr_buy3.buy)
    sell1 = copy.deepcopy(tr_sell1.sell)
    sell2 = copy.deepcopy(tr_sell2.sell)
    sell3 = copy.deepcopy(tr_sell3.sell)
    assert buy1
    assert buy2
    assert buy3
    assert sell1
    assert sell2
    assert sell3

    tax, tax_events = do_match(transactions, TaxRules.US_INDIVIDUAL_LIFO)

    assert len(tax_events) == 3
    assert tax_events[0].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[0].cost == 8000
    assert tax_events[0].proceeds == 4000
    assert str(tax_events[0].sell) == str(sell1)
    assert [str(b) for b in tax_events[0].buys] == [str(buy3)]

    assert tax_events[1].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[1].cost == 2000
    assert tax_events[1].proceeds == 6000
    assert str(tax_events[1].sell) == str(sell2)
    assert [str(b) for b in tax_events[1].buys] == [str(buy2)]

    assert tax_events[2].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[2].cost == 2500
    assert tax_events[2].proceeds == 2000
    s_buy1_1 = make_buy(1, "BTC", 2475, buy1.wallet, buy1.timestamp, fee=25, tid=[1, 4])
    s_buy1_2 = make_buy(1, "BTC", 2475, buy1.wallet, buy1.timestamp, fee=25, tid=[1, 5])
    assert str(tax_events[2].sell) == str(sell3)
    assert [str(b) for b in tax_events[2].buys] == [str(s_buy1_1)]

    assert tr_buy1.buy and tr_buy1.buy.matched is True
    assert tr_buy2.buy and tr_buy2.buy.matched is True
    assert tr_buy3.buy and tr_buy3.buy.matched is True
    assert tr_sell1.sell and tr_sell1.sell.matched is True
    assert tr_sell2.sell and tr_sell2.sell.matched is True
    assert tr_sell3.sell and tr_sell3.sell.matched is True

    assert [str(b) for b in tax.buy_queue[AssetSymbol("BTC")].buys] == [
        str(s_buy1_1),
        str(buy2),
        str(buy3),
        str(s_buy1_2),
    ]


def test_lofo_1() -> None:
    tr_buy1 = add_buy(2, "BTC", 5000, "Main", "2017-09-22 12:00:00")
    tr_buy2 = add_buy(1, "BTC", 2000, "Main", "2018-01-06 12:00:00")
    tr_buy3 = add_buy(1, "BTC", 8000, "Main", "2018-04-19 12:00:00")
    tr_sell1 = add_sell(1, "BTC", 4000, "Main", "2018-05-03 12:00:00")
    tr_sell2 = add_sell(1, "BTC", 6000, "Main", "2018-06-11 12:00:00")
    tr_sell3 = add_sell(1, "BTC", 2000, "Main", "2018-08-01 12:00:00")
    transactions = get_transactions([tr_buy1, tr_buy2, tr_buy3, tr_sell1, tr_sell2, tr_sell3])

    # Keep copy of buys/sells to detect any changes
    buy1 = copy.deepcopy(tr_buy1.buy)
    buy2 = copy.deepcopy(tr_buy2.buy)
    buy3 = copy.deepcopy(tr_buy3.buy)
    sell1 = copy.deepcopy(tr_sell1.sell)
    sell2 = copy.deepcopy(tr_sell2.sell)
    sell3 = copy.deepcopy(tr_sell3.sell)
    assert buy1
    assert buy2
    assert buy3
    assert sell1
    assert sell2
    assert sell3

    tax, tax_events = do_match(transactions, TaxRules.US_INDIVIDUAL_LOFO)

    assert len(tax_events) == 3
    assert tax_events[0].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[0].cost == 2000
    assert tax_events[0].proceeds == 4000
    assert str(tax_events[0].sell) == str(sell1)
    assert [str(b) for b in tax_events[0].buys] == [str(buy2)]

    assert tax_events[1].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[1].cost == 2500
    assert tax_events[1].proceeds == 6000
    assert str(tax_events[1].sell) == str(sell2)
    s_buy1_1 = make_buy(1, "BTC", 2500, buy1.wallet, buy1.timestamp, tid=[1, 3])
    s_buy1_2 = make_buy(1, "BTC", 2500, buy1.wallet, buy1.timestamp, tid=[1, 4])
    assert [str(b) for b in tax_events[1].buys] == [str(s_buy1_1)]

    assert tax_events[2].disposal_type is DisposalType.SHORT_TERM
    assert tax_events[2].cost == 2500
    assert tax_events[2].proceeds == 2000
    assert str(tax_events[2].sell) == str(sell3)
    assert [str(b) for b in tax_events[2].buys] == [str(s_buy1_2)]

    assert tr_buy1.buy and tr_buy1.buy.matched is True
    assert tr_buy2.buy and tr_buy2.buy.matched is True
    assert tr_buy3.buy and tr_buy3.buy.matched is False
    assert tr_sell1.sell and tr_sell1.sell.matched is True
    assert tr_sell2.sell and tr_sell2.sell.matched is True
    assert tr_sell3.sell and tr_sell3.sell.matched is True

    assert [str(b) for b in tax.buy_queue[AssetSymbol("BTC")].buys] == [
        str(s_buy1_1),
        str(buy2),
        str(buy3),
        str(s_buy1_2),
    ]
