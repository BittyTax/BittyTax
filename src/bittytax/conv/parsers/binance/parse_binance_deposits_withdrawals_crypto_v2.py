from decimal import Decimal
from typing import TYPE_CHECKING

from ....bt_types import TrType
from ...datarow import TxRawPos
from ...out_record import TransactionOutRecord
from .utils import WALLET, get_timestamp

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from ...dataparser import DataParser, ParserArgs
    from ...datarow import DataRow


def parse_binance_deposits_withdrawals_crypto_v2(
    data_row: "DataRow", parser: "DataParser", **_kwargs: "Unpack[ParserArgs]"
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = parser.parse_timestamp(get_timestamp(row_dict["Date(UTC+0)"]))
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
