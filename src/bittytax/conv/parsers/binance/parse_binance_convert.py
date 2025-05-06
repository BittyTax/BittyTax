from decimal import Decimal
from typing import TYPE_CHECKING

from ....bt_types import TrType
from ...exceptions import UnexpectedTradingPairError
from ...out_record import TransactionOutRecord
from .utils import (
    WALLET,
    split_trading_pair,
)

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from ...dataparser import DataParser, ParserArgs
    from ...datarow import DataRow


def parse_binance_convert(
    data_row: "DataRow", parser: "DataParser", **_kwargs: "Unpack[ParserArgs]"
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = parser.parse_timestamp(row_dict["Date"])

    if row_dict["Status"] != "Successful":
        return

    base_asset, quote_asset = split_trading_pair(row_dict["Pair"])
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
