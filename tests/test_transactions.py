from decimal import Decimal

from bittytax.bt_types import AssetSymbol, TrType
from bittytax.transactions import Buy


def test_nft1() -> None:
    buy = Buy(
        TrType.TRADE,
        buy_quantity=Decimal(1),
        buy_asset=AssetSymbol("CryptoPunk #101"),
        buy_value=None,
    )
    assert buy.is_nft() is True


def test_nft2() -> None:
    buy = Buy(TrType.TRADE, buy_quantity=Decimal(1), buy_asset=AssetSymbol("BTC"), buy_value=None)
    assert buy.is_nft() is False


def test_nft3() -> None:
    buy = Buy(
        TrType.TRADE,
        buy_quantity=Decimal(1),
        buy_asset=AssetSymbol("Frog Cartel #3683"),
        buy_value=None,
    )
    assert buy.is_nft() is True


def test_nft4() -> None:
    buy = Buy(
        TrType.TRADE,
        buy_quantity=Decimal(1),
        buy_asset=AssetSymbol("XYZ #"),
        buy_value=None,
    )
    assert buy.is_nft() is False


def test_nft5() -> None:
    buy = Buy(
        TrType.TRADE,
        buy_quantity=Decimal(1),
        buy_asset=AssetSymbol("XYZ #1"),
        buy_value=None,
    )
    assert buy.is_nft() is True


def test_nft6() -> None:
    buy = Buy(
        TrType.TRADE,
        buy_quantity=Decimal(1),
        buy_asset=AssetSymbol("XYZ 1"),
        buy_value=None,
    )
    assert buy.is_nft() is False
