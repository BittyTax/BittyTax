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

WALLET = "Binance.US"


def parse_binance_us(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"])

    primary_value = DataParser.convert_currency(
        row_dict["Realized_Amount_For_Primary_Asset_In_USD_Value"], "USD", data_row.timestamp
    )
    base_value = DataParser.convert_currency(
        row_dict["Realized_Amount_For_Base_Asset_In_USD_Value"], "USD", data_row.timestamp
    )
    quote_value = DataParser.convert_currency(
        row_dict["Realized_Amount_For_Quote_Asset_In_USD_Value"], "USD", data_row.timestamp
    )
    fee_value = DataParser.convert_currency(
        row_dict["Realized_Amount_For_Fee_Asset_In_USD_Value"], "USD", data_row.timestamp
    )

    if row_dict["Category"] == "Deposit":
        if row_dict["Realized_Amount_For_Fee_Asset"]:
            fee_quantity = Decimal(row_dict["Realized_Amount_For_Fee_Asset"])
            fee_asset = row_dict["Fee_Asset"]
        else:
            fee_quantity = None
            fee_asset = ""

        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Realized_Amount_For_Primary_Asset"]),
            buy_asset=row_dict["Primary_Asset"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            fee_value=fee_value,
            wallet=WALLET,
        )
    elif row_dict["Category"] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Realized_Amount_For_Primary_Asset"]),
            sell_asset=row_dict["Primary_Asset"],
            fee_quantity=Decimal(row_dict["Realized_Amount_For_Fee_Asset"]),
            fee_asset=row_dict["Fee_Asset"],
            fee_value=fee_value,
            wallet=WALLET,
        )
    elif row_dict["Category"] == "Distribution":
        if row_dict["Operation"] == "Others":
            data_row.t_record = TransactionOutRecord(
                TrType.AIRDROP,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Realized_Amount_For_Primary_Asset"]),
                buy_asset=row_dict["Primary_Asset"],
                buy_value=primary_value,
                wallet=WALLET,
            )
        elif row_dict["Operation"] == "Staking Rewards":
            if Decimal(row_dict["Realized_Amount_For_Primary_Asset"]) > 0:
                data_row.t_record = TransactionOutRecord(
                    TrType.STAKING,
                    data_row.timestamp,
                    buy_quantity=Decimal(row_dict["Realized_Amount_For_Primary_Asset"]),
                    buy_asset=row_dict["Primary_Asset"],
                    buy_value=primary_value,
                    wallet=WALLET,
                )
            else:
                # Negative amount is a service fee
                data_row.t_record = TransactionOutRecord(
                    TrType.SPEND,
                    data_row.timestamp,
                    sell_quantity=abs(Decimal(row_dict["Realized_Amount_For_Primary_Asset"])),
                    sell_asset=row_dict["Primary_Asset"],
                    sell_value=primary_value,
                    wallet=WALLET,
                )
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("Operation"), "Operation", row_dict["Operation"]
            )
    elif row_dict["Category"] in ("Buy", "Quick Buy", "Convert"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Realized_Amount_For_Quote_Asset"]),
            buy_asset=row_dict["Quote_Asset"],
            buy_value=quote_value,
            sell_quantity=Decimal(row_dict["Realized_Amount_For_Base_Asset"]),
            sell_asset=row_dict["Base_Asset"],
            sell_value=base_value,
            fee_quantity=Decimal(row_dict["Realized_Amount_For_Fee_Asset"]),
            fee_asset=row_dict["Fee_Asset"],
            fee_value=fee_value,
            wallet=WALLET,
        )
    elif row_dict["Category"] == "Spot Trading":
        if not row_dict["Realized_Amount_For_Quote_Asset"] and row_dict["Quote_Asset"] in (
            "USD",
            "USDT",
            "BUSD",
        ):
            quote_amount = row_dict["Realized_Amount_For_Quote_Asset_In_USD_Value"]

        else:
            quote_amount = row_dict["Realized_Amount_For_Quote_Asset"]

        if row_dict["Operation"] == "Buy":
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Realized_Amount_For_Base_Asset"]),
                buy_asset=row_dict["Base_Asset"],
                buy_value=base_value,
                sell_quantity=Decimal(quote_amount),
                sell_asset=row_dict["Quote_Asset"],
                sell_value=quote_value,
                fee_quantity=Decimal(row_dict["Realized_Amount_For_Fee_Asset"]),
                fee_asset=row_dict["Fee_Asset"],
                fee_value=fee_value,
                wallet=WALLET,
            )
        elif row_dict["Operation"] == "Sell":
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=Decimal(quote_amount),
                buy_asset=row_dict["Quote_Asset"],
                buy_value=quote_value,
                sell_quantity=Decimal(row_dict["Realized_Amount_For_Base_Asset"]),
                sell_asset=row_dict["Base_Asset"],
                sell_value=base_value,
                fee_quantity=Decimal(row_dict["Realized_Amount_For_Fee_Asset"]),
                fee_asset=row_dict["Fee_Asset"],
                fee_value=fee_value,
                wallet=WALLET,
            )
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("Operation"), "Operation", row_dict["Operation"]
            )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Category"), "Category", row_dict["Category"]
        )


DataParser(
    ParserType.EXCHANGE,
    "Binance.US",
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
    worksheet_name="Binance.US",
    row_handler=parse_binance_us,
)
