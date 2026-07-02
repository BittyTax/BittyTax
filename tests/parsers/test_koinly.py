from decimal import Decimal
from typing import Dict, List

from bittytax.bt_types import TrType
from bittytax.config import config
from bittytax.conv.dataparser import DataParser
from bittytax.conv.datarow import DataRow
from bittytax.conv.parsers.koinly import parse_koinly_bulk_edit

config.ccy = "GBP"

# Header of the Koinly "Bulk edit in Excel" transactions export. Currency and wallet cells carry
# a ";<id>" suffix and the value is held in "Net Value (read-only)", see:
# https://support.koinly.io/en/articles/9490043-bulk-edit-in-excel
HEADER = [
    "ID (read-only)",
    "Parent ID (read-only)",
    "Date (UTC)",
    "Type",
    "Tag",
    "From Wallet (read-only)",
    "From Wallet ID",
    "From Amount",
    "From Currency",
    "To Wallet (read-only)",
    "To Wallet ID",
    "To Amount",
    "To Currency",
    "Fee Amount",
    "Fee Currency",
    "Net Worth Amount",
    "Net Worth Currency",
    "Fee Worth Amount",
    "Fee Worth Currency",
    "Net Value (read-only)",
    "Fee Value (read-only)",
    "Value Currency (read-only)",
    "Deleted",
    "From Source (read-only)",
    "To Source (read-only)",
    "Negative Balances (read-only)",
    "Missing Rates (read-only)",
    "Missing Cost Basis (read-only)",
    "Synced To Accounting At (UTC read-only)",
    "TxSrc",
    "TxDest",
    "TxHash",
    "Description",
]


def _parse(**cells: str) -> DataRow:
    parser = DataParser.match_header(HEADER, 0)
    assert parser.row_handler is parse_koinly_bulk_edit

    values: Dict[str, str] = {col: "" for col in HEADER}
    values.update(cells)
    row: List[str] = [values[col] for col in HEADER]

    data_row = DataRow(1, row, parser.in_header, "Koinly")
    parse_koinly_bulk_edit(data_row, parser)
    return data_row


def test_deposit_reward() -> None:
    data_row = _parse(
        **{
            "Date (UTC)": "2025-01-03 22:19:40",
            "Type": "deposit",
            "Tag": "reward",
            "To Wallet (read-only)": "Flare (FLR);flare",
            "To Amount": "8121.9422723224",
            "To Currency": "WFLR;9546698",
            "Net Value (read-only)": "224.7162634542",
            "Value Currency (read-only)": "GBP;1",
        }
    )
    assert data_row.t_record is not None
    assert data_row.t_record.t_type == TrType.STAKING_REWARD
    assert data_row.t_record.buy_quantity == Decimal("8121.9422723224")
    assert data_row.t_record.buy_asset == "WFLR"
    assert data_row.t_record.buy_value == Decimal("224.7162634542")
    assert data_row.t_record.wallet == "Flare (FLR)"


def test_trade() -> None:
    data_row = _parse(
        **{
            "Date (UTC)": "2025-02-01 10:00:00",
            "Type": "trade",
            "From Amount": "1",
            "From Currency": "BTC;1",
            "To Amount": "15",
            "To Currency": "ETH;2",
            "Net Value (read-only)": "50000",
            "Value Currency (read-only)": "GBP",
        }
    )
    assert data_row.t_record is not None
    assert data_row.t_record.t_type == TrType.TRADE
    assert data_row.t_record.buy_quantity == Decimal("15")
    assert data_row.t_record.buy_asset == "ETH"
    assert data_row.t_record.sell_quantity == Decimal("1")
    assert data_row.t_record.sell_asset == "BTC"


def test_withdrawal_cost() -> None:
    data_row = _parse(
        **{
            "Date (UTC)": "2025-02-02 10:00:00",
            "Type": "withdrawal",
            "Tag": "Cost",
            "From Amount": "0.5",
            "From Currency": "ETH;2",
        }
    )
    assert data_row.t_record is not None
    assert data_row.t_record.t_type == TrType.SPEND
    assert data_row.t_record.sell_quantity == Decimal("0.5")
    assert data_row.t_record.sell_asset == "ETH"


def test_untagged_deposit_is_transfer() -> None:
    data_row = _parse(
        **{
            "Date (UTC)": "2025-02-05 10:00:00",
            "Type": "deposit",
            "To Amount": "2",
            "To Currency": "ADA;5",
        }
    )
    assert data_row.t_record is not None
    assert data_row.t_record.t_type == TrType.DEPOSIT


def test_unknown_tag_is_unmapped() -> None:
    data_row = _parse(
        **{
            "Date (UTC)": "2025-02-07 10:00:00",
            "Type": "deposit",
            "Tag": "SomeTag",
            "To Amount": "1",
            "To Currency": "XYZ;9",
        }
    )
    assert data_row.t_record is not None
    assert data_row.t_record.t_type == "_SomeTag"


def test_value_falls_back_to_net_worth() -> None:
    data_row = _parse(
        **{
            "Date (UTC)": "2025-02-04 10:00:00",
            "Type": "deposit",
            "Tag": "reward",
            "To Amount": "5",
            "To Currency": "DOT;4",
            "Net Worth Amount": "200",
            "Net Worth Currency": "GBP",
        }
    )
    assert data_row.t_record is not None
    assert data_row.t_record.buy_value == Decimal("200")
