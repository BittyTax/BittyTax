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

WALLET = "Deribit"


def parse_deribit(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["Type"] == "deposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset=get_asset(row_dict["Info"]),
            wallet=WALLET,
        )
    elif row_dict["Type"] == "withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Change"])) - Decimal(row_dict["Fee Paid"]),
            sell_asset=get_asset(row_dict["Info"]),
            fee_quantity=Decimal(row_dict["Fee Paid"]),
            fee_asset=get_asset(row_dict["Info"]),
            wallet=WALLET,
        )
    elif row_dict["Type"] == "settlement":
        if Decimal(row_dict["Change"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_GAIN,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Change"]),
                buy_asset=row_dict["Instrument"].split("-")[0],
                wallet=WALLET,
            )
        elif Decimal(row_dict["Change"]) < 0:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_LOSS,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Change"])),
                sell_asset=row_dict["Instrument"].split("-")[0],
                wallet=WALLET,
            )
    elif row_dict["Type"] == "trade":
        if Decimal(row_dict["Fee Paid"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.MARGIN_FEE,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["Fee Paid"]),
                sell_asset=row_dict["Instrument"].split("-")[0],
                wallet=WALLET,
            )
        elif Decimal(row_dict["Fee Paid"]) < 0:
            data_row.t_record = TransactionOutRecord(
                TrType.GIFT_RECEIVED,  # Update to FEE_REBATE when merged
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Change"]),
                buy_asset=row_dict["Instrument"].split("-")[0],
                wallet=WALLET,
            )
    elif row_dict["Type"] == "transfer from insurance":
        data_row.t_record = TransactionOutRecord(
            TrType.GIFT_RECEIVED,  # Update to FEE_REBATE when merged
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset="BTC",
            wallet=WALLET,
        )
    elif row_dict["Type"] == "socialized fund":
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Change"])),
            sell_asset="BTC",
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def get_asset(address: str) -> str:
    if address.startswith("0x"):
        return "ETH"
    return "BTC"


DataParser(
    ParserType.EXCHANGE,
    "Deribit",
    [
        "ID",
        "UserSeq",
        "Date",
        "Instrument",
        "Type",
        "Side",
        "Size",
        "Position",
        "Price",
        "Mark Price",
        "Cash Flow",
        "Funding",
        "Fee Rate",
        "Fee Paid",
        "Fee Balance",
        "Change",
        "Balance",
        "Equity",
        "Trade ID",
        "Order ID",
        "Info",
    ],
    worksheet_name="Deribit",
    row_handler=parse_deribit,
)
