# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

WALLET = "Coinfloor"


def parse_coinfloor_trades(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date & Time"])

    base_asset = row_dict["Base Asset"].replace("XBT", "BTC")
    counter_asset = row_dict["Counter Asset"].replace("XBT", "BTC")

    if row_dict["Order Type"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=row_dict["Amount"],
            buy_asset=base_asset,
            sell_quantity=row_dict["Total"],
            sell_asset=counter_asset,
            fee_quantity=row_dict["Fee"],
            fee_asset=counter_asset,
            wallet=WALLET,
        )
    elif row_dict["Order Type"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=row_dict["Total"],
            buy_asset=counter_asset,
            sell_quantity=row_dict["Amount"],
            sell_asset=base_asset,
            fee_quantity=row_dict["Fee"],
            fee_asset=counter_asset,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Order Type"), "Order Type", row_dict["Order Type"]
        )


def parse_coinfloor_deposits_withdrawals(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date & Time"])

    if row_dict["Type"] == "Deposit":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["Amount"],
            buy_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=row_dict["Amount"],
            sell_asset=row_dict["Asset"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    DataParser.TYPE_EXCHANGE,
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
    DataParser.TYPE_EXCHANGE,
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
    DataParser.TYPE_EXCHANGE,
    "Coinfloor Deposits/Withdrawals",
    ["Date & Time", "Amount", "Asset", "Type"],
    worksheet_name="Coinfloor D,W",
    row_handler=parse_coinfloor_deposits_withdrawals,
)

DataParser(
    DataParser.TYPE_EXCHANGE,
    "Coinfloor Deposits/Withdrawals",
    ["Date & Time", "Amount", "Asset", "Type", "Address", "Transaction Hash"],
    worksheet_name="Coinfloor D,W",
    row_handler=parse_coinfloor_deposits_withdrawals,
)
