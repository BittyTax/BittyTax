# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2025

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Blockchain.com Exchange"


def parse_blockchain_exchange(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict

    if not row_dict:
        # Skip empty rows
        return

    data_row.timestamp = DataParser.parse_timestamp(row_dict["date_time_utc"])
    data_row.tx_raw = TxRawPos(parser.in_header.index("tx_hash"))

    if row_dict["transaction_type"] == "DEPOSIT":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["quantity_transacted"]),
            buy_asset=row_dict["asset"],
            wallet=WALLET,
        )
    elif row_dict["transaction_type"] == "WITHDRAWAL":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["counter_amount"]),
            sell_asset=row_dict["counter_asset"],
            fee_quantity=Decimal(row_dict["fee_amount"]),
            fee_asset=row_dict["fee_asset"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("transaction_type"),
            "transaction_type",
            row_dict["transaction_type"],
        )


DataParser(
    ParserType.EXCHANGE,
    "Blockchain.com Exchange",
    [
        "date_time_utc",
        "transaction_type",
        "asset",
        "quantity_transacted",
        "counter_asset",
        "counter_amount",
        "price",
        "fee_asset",
        "fee_amount",
        "order_id",
        "transaction_id",
        "tx_hash",
    ],
    worksheet_name="Blockchain.com Exchange",
    row_handler=parse_blockchain_exchange,
)
