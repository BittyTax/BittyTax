from decimal import Decimal
from typing import TYPE_CHECKING

from ....bt_types import TrType
from ...exceptions import DataFilenameError
from ...out_record import TransactionOutRecord
from .utils import WALLET

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from ...dataparser import DataParser, ParserArgs
    from ...datarow import DataRow


def parse_binance_deposits_withdrawals_cash(
    data_row: "DataRow", parser: "DataParser", **kwargs: "Unpack[ParserArgs]"
) -> None:
    row_dict = data_row.row_dict

    timestamp_hdr = parser.args[0].group(1)
    utc_offset = parser.args[0].group(2)

    if utc_offset == "UTCnull":
        utc_offset = "UTC"

    data_row.timestamp = parser.parse_timestamp(f"{row_dict[timestamp_hdr]} {utc_offset}")

    if row_dict["Status"] != "Successful":
        return

    if "deposit" in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Indicated Amount"]),
            buy_asset=row_dict["Coin"],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    elif "withdraw" in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Coin"],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Coin"],
            wallet=WALLET,
        )
    else:
        raise DataFilenameError(kwargs["filename"], "Transaction Type (Deposit or Withdrawal)")
