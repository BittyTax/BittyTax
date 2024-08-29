# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import re
from decimal import Decimal
from typing import TYPE_CHECKING

import dateutil.tz
from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Cash App"
TZ_INFOS = {
    "EST": dateutil.tz.gettz("America/New_York"),
    "EDT": dateutil.tz.gettz("America/New_York"),
}


def parse_cash_app(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"], tzinfos=TZ_INFOS)

    amount = Decimal(re.sub(r"[^-\d.]+", "", row_dict["Amount"]))
    fee = Decimal(re.sub(r"[^-\d.]+", "", row_dict["Fee"]))

    if row_dict["Transaction Type"] in ("Received P2P", "Cash in"):
        if amount > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=amount,
                buy_asset=row_dict["Currency"],
                fee_quantity=abs(fee),
                fee_asset=row_dict["Currency"],
                wallet=WALLET,
                note=row_dict["Notes"],
            )
        else:
            # PAYMENT REFUNDED
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=abs(amount),
                sell_asset=row_dict["Currency"],
                fee_quantity=fee,
                fee_asset=row_dict["Currency"],
                wallet=WALLET,
                note=f"{row_dict['Notes']} (Payment Refunded)",
            )
    elif row_dict["Transaction Type"] in ("Sent P2P", "Cash out"):
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(amount),
            sell_asset=row_dict["Currency"],
            fee_quantity=abs(fee),
            fee_asset=row_dict["Currency"],
            wallet=WALLET,
            note=row_dict["Notes"],
        )
    elif row_dict["Transaction Type"] == "Cash Card Debit":
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=abs(amount),
            sell_asset=row_dict["Currency"],
            fee_quantity=abs(fee),
            fee_asset=row_dict["Currency"],
            wallet=WALLET,
            note=row_dict["Notes"],
        )
    elif row_dict["Transaction Type"] == "Bitcoin Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Asset Amount"]),
            buy_asset=row_dict["Asset Type"],
            sell_quantity=abs(amount),
            sell_asset=row_dict["Currency"],
            fee_quantity=abs(fee),
            fee_asset=row_dict["Currency"],
            wallet=WALLET,
            note=row_dict["Notes"],
        )
    elif row_dict["Transaction Type"] == "Boost Payment":
        data_row.t_record = TransactionOutRecord(
            TrType.CASHBACK,
            data_row.timestamp,
            buy_quantity=amount,
            buy_asset=row_dict["Currency"],
            fee_quantity=abs(fee),
            fee_asset=row_dict["Currency"],
            wallet=WALLET,
            note=row_dict["Notes"],
        )
    elif row_dict["Transaction Type"] == "Bitcoin Boost":
        data_row.t_record = TransactionOutRecord(
            TrType.CASHBACK,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Asset Amount"]),
            buy_asset=row_dict["Asset Type"],
            buy_value=amount,
            fee_quantity=abs(fee),
            fee_asset=row_dict["Currency"],
            wallet=WALLET,
            note=row_dict["Notes"],
        )
    elif row_dict["Transaction Type"] == "Bitcoin Withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Asset Amount"]),
            sell_asset=row_dict["Asset Type"],
            fee_quantity=abs(fee),
            fee_asset=row_dict["Currency"],
            wallet=WALLET,
            note=row_dict["Notes"],
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Transaction Type"),
            "Transaction Type",
            row_dict["Transaction Type"],
        )


DataParser(
    ParserType.EXCHANGE,
    "Cash App",
    [
        "Transaction ID",
        "Date",
        "Transaction Type",
        "Currency",
        "Amount",
        "Fee",
        "Net Amount",
        "Asset Type",
        "Asset Price",
        "Asset Amount",
        "Status",
        "Notes",
        "Name of sender/receiver",
        "Account",
    ],
    worksheet_name="Cash App",
    row_handler=parse_cash_app,
)
