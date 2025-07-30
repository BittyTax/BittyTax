from decimal import Decimal
from typing import TYPE_CHECKING

from ....bt_types import TrType
from ...exceptions import UnexpectedTradingPairError, UnexpectedTypeError
from ...out_record import TransactionOutRecord
from .utils import WALLET, split_trading_pair

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from ...dataparser import DataParser, ParserArgs
    from ...datarow import DataRow


def parse_binance_trades(
    data_row: "DataRow", parser: "DataParser", **_kwargs: "Unpack[ParserArgs]"
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = parser.parse_timestamp(row_dict["Date(UTC)"])

    base_asset, quote_asset = split_trading_pair(row_dict["Market"])
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
