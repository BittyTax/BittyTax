# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2025

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "sFOX"


def parse_sfox(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["OrderDate"][:-38])

    fees = DataParser.convert_currency(row_dict["FeesUSD"], "USD", data_row.timestamp)
    principal_amount = DataParser.convert_currency(
        row_dict["PrincipalAmountUSD"], "USD", data_row.timestamp
    )

    if row_dict["Action"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]),
            buy_asset=row_dict["Asset"].upper(),
            sell_quantity=principal_amount,
            sell_asset=config.ccy,
            fee_quantity=fees,
            fee_asset=config.ccy,
            wallet=WALLET,
        )
    elif row_dict["Action"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=principal_amount,
            buy_asset=config.ccy,
            sell_quantity=Decimal(row_dict["Quantity"]),
            sell_asset=row_dict["Asset"].upper(),
            fee_quantity=fees,
            fee_asset=config.ccy,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Action"), "Action", row_dict["Action"])


DataParser(
    ParserType.EXCHANGE,
    "sFOX",
    [
        "OrderId",
        "OrderDate",
        "AddedByUserEmail",
        "Action",
        "AssetPair",
        "Quantity",
        "Asset",
        "AssetUSDFXRate",
        "UnitPrice",
        "PriceCurrency",
        "PrincipalAmount",
        "PriceUSDFXRate",
        "PrincipalAmountUSD",
        "Fees",
        "FeesUSD",
        "Total",
        "TotalUSD",
    ],
    worksheet_name="sFOX",
    row_handler=parse_sfox,
)
