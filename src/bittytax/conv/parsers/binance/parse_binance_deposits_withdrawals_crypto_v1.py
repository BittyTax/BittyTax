from decimal import Decimal
from typing import TYPE_CHECKING

from ....bt_types import TrType
from ...datarow import TxRawPos
from ...exceptions import DataFilenameError
from ...out_record import TransactionOutRecord
from .utils import WALLET

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from ...dataparser import DataParser, ParserArgs
    from ...datarow import DataRow


def parse_binance_deposits_withdrawals_crypto_v1(
    data_row: "DataRow", parser: "DataParser", **kwargs: "Unpack[ParserArgs]"
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = parser.parse_timestamp(data_row.row[0])
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
