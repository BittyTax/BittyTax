# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

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

WALLET = "Mercatox"


def parse_mercatox(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    if row_dict["Type"] == "Deposit":
        data_row.tx_raw = TxRawPos(parser.in_header.index("NT Transaction Id"))
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Withdraw":
        data_row.tx_raw = TxRawPos(
            parser.in_header.index("NT Transaction Id"),
            tx_dest_pos=parser.in_header.index("Withdraw addr"),
        )
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Currency"],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Currency"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Deal":
        if row_dict["Action"] == "buy":
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount"]),
                buy_asset=row_dict["Pair"].split("/")[0],
                sell_quantity=Decimal(row_dict["Total"]),
                sell_asset=row_dict["Pair"].split("/")[1],
                wallet=WALLET,
            )
        elif row_dict["Action"] == "sell":
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Total"]),
                buy_asset=row_dict["Pair"].split("/")[1],
                sell_quantity=Decimal(row_dict["Amount"]),
                sell_asset=row_dict["Pair"].split("/")[0],
                wallet=WALLET,
            )
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("Action"), "Action", row_dict["Action"]
            )
    elif row_dict["Type"] == "Promo":
        data_row.t_record = TransactionOutRecord(
            TrType.AIRDROP,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    ParserType.EXCHANGE,
    "Mercatox",
    [
        "MX Transaction Id",
        "NT Transaction Id",
        "Withdraw addr",
        "Type",
        "Currency",
        "Pair",
        "Fee",
        "Amount",
        "Price",
        "Total",
        "Action",
        "From",
        "To",
        "Time",
    ],
    worksheet_name="Mercatox",
    row_handler=parse_mercatox,
)
