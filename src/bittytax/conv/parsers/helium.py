# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Helium"


def parse_helium_fairspot(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["date"])
    amount_ccy = DataParser.convert_currency(row_dict["usd_amount"], "USD", data_row.timestamp)
    fee_ccy = DataParser.convert_currency(row_dict["usd_fee"], "USD", data_row.timestamp)

    if row_dict["type"] == "rewards_v1":
        data_row.t_record = TransactionOutRecord(
            TrType.MINING,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["hnt_amount"]),
            buy_asset="HNT",
            buy_value=amount_ccy,
            wallet=WALLET,
        )
    elif row_dict["type"] == "payment_v2":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["hnt_amount"]),
            buy_asset="HNT",
            buy_value=amount_ccy,
            fee_quantity=Decimal(row_dict["hnt_fee"]),
            fee_asset="HNT",
            fee_value=fee_ccy,
            wallet=WALLET,
        )
    elif row_dict["type"] == "payment_v1":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["hnt_amount"]),
            sell_asset="HNT",
            sell_value=amount_ccy,
            fee_quantity=Decimal(row_dict["hnt_fee"]),
            fee_asset="HNT",
            fee_value=fee_ccy,
            wallet=WALLET,
        )
    elif row_dict["type"] == "transfer_hotspot_v1":
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["hnt_amount"]),
            sell_asset="HNT",
            sell_value=amount_ccy,
            fee_quantity=Decimal(row_dict["hnt_fee"]),
            fee_asset="HNT",
            fee_value=fee_ccy,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def parse_helium_explorer(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["Tag"] == "mined":
        data_row.t_record = TransactionOutRecord(
            TrType.MINING,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Received Quantity"]),
            buy_asset=row_dict["Received Currency"],
            fee_quantity=Decimal(row_dict["Fee Amount"]),
            fee_asset=row_dict["Fee Currency"],
            wallet=WALLET,
        )
    elif row_dict["Tag"] == "payment" and row_dict["Received Quantity"]:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Received Quantity"]),
            buy_asset=row_dict["Received Currency"],
            fee_quantity=Decimal(row_dict["Fee Amount"]),
            fee_asset=row_dict["Fee Currency"],
            wallet=WALLET,
        )

    elif row_dict["Tag"] == "payment" and row_dict["Sent Quantity"]:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Sent Quantity"]),
            sell_asset=row_dict["Sent Currency"],
            fee_quantity=Decimal(row_dict["Fee Amount"]),
            fee_asset=row_dict["Fee Currency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Tag"), "Tag", row_dict["Tag"])


DataParser(
    ParserType.WALLET,
    "Helium",
    [
        "block",
        "date",
        "type",
        "transaction_hash",
        "hnt_amount",
        "hnt_fee",
        "usd_oracle_price",
        "usd_amount",
        "usd_fee",
        "payer",
        "payee",
    ],
    worksheet_name="Helium",
    row_handler=parse_helium_fairspot,
)

DataParser(
    ParserType.EXPLORER,
    "Helium Explorer",
    [
        "Date",
        "Received Quantity",
        "Received From",
        "Received Currency",
        "Sent Quantity",
        "Sent To",
        "Sent Currency",
        "Fee Amount",
        "Fee Currency",
        "Tag",
        "Note",
        "Hotspot",
        "Reward Type",
        "Block",
        "Hash",
    ],
    worksheet_name="Helium",
    row_handler=parse_helium_explorer,
)
