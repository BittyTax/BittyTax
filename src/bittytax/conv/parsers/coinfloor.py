# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

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

WALLET = "Coinfloor"


def parse_coinfloor_trades(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date & Time"])

    base_asset = row_dict["Base Asset"].replace("XBT", "BTC")
    counter_asset = row_dict["Counter Asset"].replace("XBT", "BTC")

    if row_dict["Order Type"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=base_asset,
            sell_quantity=Decimal(row_dict["Total"]),
            sell_asset=counter_asset,
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=counter_asset,
            wallet=WALLET,
        )
    elif row_dict["Order Type"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Total"]),
            buy_asset=counter_asset,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=base_asset,
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=counter_asset,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Order Type"), "Order Type", row_dict["Order Type"]
        )


def parse_coinfloor_deposits_withdrawals(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date & Time"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("Transaction Hash"),
        tx_dest_pos=parser.in_header.index("Address"),
    )

    if row_dict["Type"] == "Deposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    ParserType.EXCHANGE,
    "Coinfloor Trades",
    [
        "Date & Time",
        "Base Asset",
        "Counter Asset",
        "Amount",
        "Price",
        "Total",
        "Fee",
        "Order Type",
    ],
    worksheet_name="Coinfloor T",
    row_handler=parse_coinfloor_trades,
)

DataParser(
    ParserType.EXCHANGE,
    "Coinfloor Trades",
    [
        "Date & Time",
        "Base Asset",
        "Counter Asset",
        "Amount",
        "Price",
        "Total",
        "Fee",
        "Order Type",
        "Trade ID",
        "Order ID",
    ],
    worksheet_name="Coinfloor T",
    row_handler=parse_coinfloor_trades,
)

DataParser(
    ParserType.EXCHANGE,
    "Coinfloor Deposits/Withdrawals",
    ["Date & Time", "Amount", "Asset", "Type"],
    worksheet_name="Coinfloor D,W",
    row_handler=parse_coinfloor_deposits_withdrawals,
)

DataParser(
    ParserType.EXCHANGE,
    "Coinfloor Deposits/Withdrawals",
    ["Date & Time", "Amount", "Asset", "Type", "Address", "Transaction Hash"],
    worksheet_name="Coinfloor D,W",
    row_handler=parse_coinfloor_deposits_withdrawals,
)
