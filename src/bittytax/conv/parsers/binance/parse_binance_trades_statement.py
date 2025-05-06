from typing import TYPE_CHECKING

from ....bt_types import TrType
from ...exceptions import UnexpectedTypeError
from ...out_record import TransactionOutRecord
from .utils import WALLET, split_asset

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from ...dataparser import DataParser, ParserArgs
    from ...datarow import DataRow


def parse_binance_trades_statement(
    data_row: "DataRow", parser: "DataParser", **_kwargs: "Unpack[ParserArgs]"
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = parser.parse_timestamp(row_dict["Date(UTC)"])
    fee_quantity, fee_asset = split_asset(row_dict["Fee"].replace(",", ""))

    if row_dict["Side"] == "BUY":
        buy_quantity, buy_asset = split_asset(row_dict["Executed"].replace(",", ""))
        sell_quantity, sell_asset = split_asset(row_dict["Amount"].replace(",", ""))

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
        buy_quantity, buy_asset = split_asset(row_dict["Amount"].replace(",", ""))
        sell_quantity, sell_asset = split_asset(row_dict["Executed"].replace(",", ""))

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
