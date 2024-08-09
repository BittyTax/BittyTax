# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Voyager"


def parse_voyager(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["transaction_date"])
    value = DataParser.convert_currency(Decimal(row_dict["net_amount"]), "USD", data_row.timestamp)

    if row_dict["transaction_direction"] == "deposit":
        if row_dict["transaction_type"] == "REWARD":
            t_type = TrType.REFERRAL
        else:
            t_type = TrType.DEPOSIT

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["quantity"]),
            buy_asset=row_dict["base_asset"],
            buy_value=value,
            wallet=WALLET,
        )
    elif row_dict["transaction_direction"] == "withdrawal":
        if row_dict["transaction_type"] == "FEE":
            data_row.t_record = TransactionOutRecord(
                TrType.SPEND,
                data_row.timestamp,
                sell_quantity=Decimal(0),
                sell_asset=row_dict["base_asset"],
                fee_quantity=Decimal(row_dict["quantity"]),
                fee_asset=row_dict["base_asset"],
                fee_value=value,
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["quantity"]),
                sell_asset=row_dict["base_asset"],
                sell_value=value,
                wallet=WALLET,
            )
    elif row_dict["transaction_direction"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["quantity"]),
            buy_asset=row_dict["base_asset"],
            buy_value=value,
            sell_quantity=Decimal(row_dict["net_amount"]),
            sell_asset=row_dict["quote_asset"],
            sell_value=value,
            wallet=WALLET,
        )
    elif row_dict["transaction_direction"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["net_amount"]),
            buy_asset=row_dict["quote_asset"],
            buy_value=value,
            sell_quantity=Decimal(row_dict["quantity"]),
            sell_asset=row_dict["base_asset"],
            sell_value=value,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("transaction_direction"),
            "transaction_direction",
            row_dict["transaction_direction"],
        )


DataParser(
    ParserType.EXCHANGE,
    "Voyager",
    [
        "transaction_date",
        "transaction_id",
        "transaction_direction",
        "transaction_type",
        "base_asset",
        "quote_asset",
        "quantity",
        "net_amount",
        "price",
    ],
    worksheet_name="Voyager",
    row_handler=parse_voyager,
)
