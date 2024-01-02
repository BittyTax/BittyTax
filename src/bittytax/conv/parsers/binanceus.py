# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

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

PRECISION = Decimal("0." + "0" * 8)

WALLET = "Binance.us"

STANDARDIZE_ASSET = {
    "UST": "USTC",
}


def parse_binanceus(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    primary_asset = row_dict["Primary_Asset"]
    base_asset = row_dict["Base_Asset"]
    quote_asset = row_dict["Quote_Asset"]
    fee_asset = row_dict["Fee_Asset"]

    # Convert assets to a recognised token name.
    for wallet_asset, asset in STANDARDIZE_ASSET.items():
        primary_asset = primary_asset.replace(wallet_asset, asset)
        base_asset = base_asset.replace(wallet_asset, asset)
        quote_asset = quote_asset.replace(wallet_asset, asset)
        fee_asset = fee_asset.replace(wallet_asset, asset)

    # Convert values to fiat currency set in configuration, if needed.
    if (
        row_dict.get("Realized_Amount_For_Primary_Asset_In_USD_Value")
        and primary_asset != config.ccy
    ):
        primary_value = DataParser.convert_currency(
            row_dict["Realized_Amount_For_Primary_Asset_In_USD_Value"], "USD", data_row.timestamp
        )
    else:
        primary_value = None

    if row_dict.get("Realized_Amount_For_Base_Asset_In_USD_Value") and base_asset != config.ccy:
        base_value = DataParser.convert_currency(
            row_dict["Realized_Amount_For_Base_Asset_In_USD_Value"], "USD", data_row.timestamp
        )
    else:
        base_value = None

    if row_dict.get("Realized_Amount_For_Quote_Asset_In_USD_Value") and quote_asset != config.ccy:
        quote_value = DataParser.convert_currency(
            row_dict["Realized_Amount_For_Quote_Asset_In_USD_Value"], "USD", data_row.timestamp
        )
    else:
        quote_value = None

    if row_dict.get("Realized_Amount_For_Fee_Asset_In_USD_Value") and fee_asset != config.ccy:
        fee_value = DataParser.convert_currency(
            row_dict["Realized_Amount_For_Fee_Asset_In_USD_Value"], "USD", data_row.timestamp
        )
    else:
        fee_value = None

    if row_dict["Category"] in ("Deposit", "Distribution"):
        # Ignore token name conversions because the new asset name "shows up" without referencing
        # the original asset. Instead, we'll adjust the name directly on the earlier transactions.
        if row_dict["Operation"] == "Others":
            return

        if "Deposit" in row_dict["Operation"]:
            tr_type = TrType.DEPOSIT
        elif row_dict["Operation"] == "Staking Rewards":
            tr_type = TrType.STAKING
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("Operation"), "Operation", row_dict["Operation"]
            )

        data_row.t_record = TransactionOutRecord(
            tr_type,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Realized_Amount_For_Primary_Asset"]),
            buy_asset=primary_asset,
            buy_value=primary_value,
            wallet=WALLET,
        )
    elif row_dict["Category"] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Realized_Amount_For_Primary_Asset"]),
            sell_asset=primary_asset,
            sell_value=primary_value,
            fee_quantity=Decimal(row_dict["Realized_Amount_For_Fee_Asset"]),
            fee_asset=fee_asset,
            fee_value=fee_value,
            wallet=WALLET,
        )
    elif row_dict["Category"] in ("Buy", "Quick Buy", "Convert"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Realized_Amount_For_Quote_Asset"]),
            buy_asset=quote_asset,
            buy_value=quote_value,
            sell_quantity=Decimal(row_dict["Realized_Amount_For_Base_Asset"]),
            sell_asset=base_asset,
            sell_value=base_value,
            fee_quantity=Decimal(row_dict["Realized_Amount_For_Fee_Asset"]),
            fee_asset=fee_asset,
            fee_value=fee_value,
            wallet=WALLET,
        )
    elif row_dict["Category"] == "Spot Trading":
        if row_dict["Operation"] == "Buy":
            buy_quantity = Decimal(row_dict["Realized_Amount_For_Base_Asset"])
            buy_asset = base_asset
            buy_value = base_value
            sell_quantity = Decimal(row_dict["Realized_Amount_For_Quote_Asset"])
            sell_asset = quote_asset
            sell_value = quote_value
        elif row_dict["Operation"] == "Sell":
            buy_quantity = Decimal(row_dict["Realized_Amount_For_Quote_Asset"])
            buy_asset = quote_asset
            buy_value = quote_value
            sell_quantity = Decimal(row_dict["Realized_Amount_For_Base_Asset"])
            sell_asset = base_asset
            sell_value = base_value
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("Operation"), "Operation", row_dict["Operation"]
            )

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=buy_value,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            sell_value=sell_value,
            fee_quantity=Decimal(row_dict["Realized_Amount_For_Fee_Asset"]),
            fee_asset=fee_asset,
            fee_value=fee_value,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    ParserType.EXCHANGE,
    "Binance.us",
    [
        "User_Id",
        "Time",
        "Category",
        "Operation",
        "Order_Id",
        "Transaction_Id",
        "Primary_Asset",
        "Realized_Amount_For_Primary_Asset",
        "Realized_Amount_For_Primary_Asset_In_USD_Value",
        "Base_Asset",
        "Realized_Amount_For_Base_Asset",
        "Realized_Amount_For_Base_Asset_In_USD_Value",
        "Quote_Asset",
        "Realized_Amount_For_Quote_Asset",
        "Realized_Amount_For_Quote_Asset_In_USD_Value",
        "Fee_Asset",
        "Realized_Amount_For_Fee_Asset",
        "Realized_Amount_For_Fee_Asset_In_USD_Value",
        "Payment_Method",
        "Withdrawal_Method",
        "Additional_Note",
    ],
    worksheet_name="Binance.us",
    row_handler=parse_binanceus,
)
