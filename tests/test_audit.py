from decimal import Decimal
from typing import List

import pytest

from bittytax.audit import AuditRecords, AuditWallet
from bittytax.bt_types import AssetSymbol, Wallet
from bittytax.config import config
from bittytax.t_record import TransactionRecord
from bittytax.t_row import TransactionRow


@pytest.mark.parametrize("hide_empty", [False, True])
@pytest.mark.parametrize("show_empty", [False, True])
def test_empty_ledger(monkeypatch: pytest.MonkeyPatch, hide_empty: bool, show_empty: bool) -> None:
    monkeypatch.setitem(config.config, "audit_hide_empty", hide_empty)
    monkeypatch.setitem(config.config, "show_empty_wallets", show_empty)
    records: List[TransactionRecord] = []
    rows = [
        ["Deposit", "1", "GBP", "", "", "", "", "", "", "", "Test", "2026-07-04", ""],
        ["Trade", "1", "BTC", "", "1", "GBP", "", "", "", "", "Test", "2026-07-05", ""],
        ["Trade", "2", "GBP", "", "1", "BTC", "", "", "", "", "Test", "2026-07-06", ""],
        ["Withdrawal", "", "", "", "2", "GBP", "", "", "", "", "Test", "2026-07-08", ""],
    ]
    for row_number, row in enumerate(rows, start=1):
        t_row = TransactionRow(row, row_number)
        t_row.parse()
        assert t_row.t_record is not None
        records.append(t_row.t_record)

    audit = AuditRecords(records)

    if hide_empty:
        assert not audit.wallets
    else:
        assert audit.wallets == {
            Wallet("Test"): {AssetSymbol("BTC"): AuditWallet(), AssetSymbol("GBP"): AuditWallet()}
        }
    assert all(totals.total == 0 for totals in audit.totals.values())
    assert len(audit.audit_log[AssetSymbol("BTC")]) == 2
    assert len(audit.audit_log[AssetSymbol("GBP")]) == 4


@pytest.mark.parametrize(
    "balance, staked",
    [
        ("0", "0"),
        ("1", "0"),
        ("0", "1"),
        ("-1", "0"),
        ("0", "-1"),
        ("1", "-1"),
        ("0.000000000000000001", "0"),
        ("0", "0.000000000000000001"),
    ],
)
def test_prune_empty_balances(monkeypatch: pytest.MonkeyPatch, balance: str, staked: str) -> None:
    monkeypatch.setitem(config.config, "audit_hide_empty", True)
    audit = AuditRecords([])
    wallet = Wallet("Test")
    asset = AssetSymbol("BTC")
    holding = AuditWallet(Decimal(balance), Decimal(staked))
    audit.wallets = {
        wallet: {asset: holding, AssetSymbol("GBP"): AuditWallet()},
        Wallet("Empty"): {asset: AuditWallet()},
    }

    audit._prune_empty()  # pylint: disable=protected-access

    if holding.balance or holding.staked:
        assert audit.wallets == {wallet: {asset: holding}}
    else:
        assert not audit.wallets
