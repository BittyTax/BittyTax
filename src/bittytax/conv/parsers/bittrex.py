# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
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

WALLET = "Bittrex"


def parse_bittrex_trades_v4(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["Side"] == "BUY":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]),
            buy_asset=re.split(r"/|-->", row_dict["Market"])[0],
            sell_quantity=Decimal(row_dict["Total"]),
            sell_asset=re.split(r"/|-->", row_dict["Market"])[1],
            wallet=WALLET,
        )
    elif row_dict["Side"] == "SELL":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Total"]),
            buy_asset=re.split(r"/|-->", row_dict["Market"])[1],
            sell_quantity=Decimal(row_dict["Quantity"]),
            sell_asset=re.split(r"/|-->", row_dict["Market"])[0],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


def parse_bittrex_trades_v3(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Opened (UTC)"])

    if row_dict["Type"] in ("LIMIT_BUY", "MARKET_BUY"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]) - Decimal(row_dict["Remaining"]),
            buy_asset=row_dict["Exchange"].split("-")[1],
            sell_quantity=Decimal(row_dict["Price"]),
            sell_asset=row_dict["Exchange"].split("-")[0],
            wallet=WALLET,
        )
    elif row_dict["Type"] in ("LIMIT_SELL", "MARKET_SELL"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Price"]),
            buy_asset=row_dict["Exchange"].split("-")[0],
            sell_quantity=Decimal(row_dict["Quantity"]) - Decimal(row_dict["Remaining"]),
            sell_asset=row_dict["Exchange"].split("-")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def parse_bittrex_trades_v2(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["TimeStamp"])

    if row_dict["OrderType"] in ("LIMIT_BUY", "MARKET_BUY"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]) - Decimal(row_dict["QuantityRemaining"]),
            buy_asset=row_dict["Exchange"].split("-")[1],
            sell_quantity=Decimal(row_dict["Price"]),
            sell_asset=row_dict["Exchange"].split("-")[0],
            fee_quantity=Decimal(row_dict["Commission"]),
            fee_asset=row_dict["Exchange"].split("-")[0],
            wallet=WALLET,
        )
    elif row_dict["OrderType"] in ("LIMIT_SELL", "MARKET_SELL"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Price"]),
            buy_asset=row_dict["Exchange"].split("-")[0],
            sell_quantity=Decimal(row_dict["Quantity"]) - Decimal(row_dict["QuantityRemaining"]),
            sell_asset=row_dict["Exchange"].split("-")[1],
            fee_quantity=Decimal(row_dict["Commission"]),
            fee_asset=row_dict["Exchange"].split("-")[0],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("OrderType"), "OrderType", row_dict["OrderType"]
        )


def parse_bittrex_trades_v1(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Opened"])

    if row_dict["Type"] in ("LIMIT_BUY", "MARKET_BUY"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]),
            buy_asset=row_dict["Exchange"].split("-")[1],
            sell_quantity=Decimal(row_dict["Price"]),
            sell_asset=row_dict["Exchange"].split("-")[0],
            fee_quantity=Decimal(row_dict["CommissionPaid"]),
            fee_asset=row_dict["Exchange"].split("-")[0],
            wallet=WALLET,
        )
    elif row_dict["Type"] in ("LIMIT_SELL", "MARKET_SELL"):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Price"]),
            buy_asset=row_dict["Exchange"].split("-")[0],
            sell_quantity=Decimal(row_dict["Quantity"]),
            sell_asset=row_dict["Exchange"].split("-")[1],
            fee_quantity=Decimal(row_dict["CommissionPaid"]),
            fee_asset=row_dict["Exchange"].split("-")[0],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def parse_bittrex_deposits_withdrawals(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TxId"), tx_dest_pos=parser.in_header.index("Address")
    )

    if row_dict["Type"] == "DEPOSIT":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "WITHDRAWAL":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=row_dict["Currency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def parse_bittrex_deposits_v2(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["LastUpdatedDate"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TxId"), tx_dest_pos=parser.in_header.index("CryptoAddress")
    )

    if "State" in row_dict and row_dict["State"] != "CONFIRMED":
        return

    data_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount"]),
        buy_asset=row_dict["Currency"],
        wallet=WALLET,
    )


def parse_bittrex_deposits_v1(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["LastUpdated"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TxId"), tx_dest_pos=parser.in_header.index("CryptoAddress")
    )

    data_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount"]),
        buy_asset=row_dict["Currency"],
        wallet=WALLET,
    )


def parse_bittrex_withdrawals(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TxId"), tx_dest_pos=parser.in_header.index("Address")
    )

    if "Opened" in row_dict:
        row_dict["OpenedDate"] = row_dict["Opened"]
        row_dict["TxFee"] = row_dict["TxCost"]

    data_row.timestamp = DataParser.parse_timestamp(row_dict["OpenedDate"])

    if row_dict["Authorized"].lower() == "true" and row_dict["Canceled"].lower() == "false":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Currency"],
            fee_quantity=Decimal(row_dict["TxFee"]),
            fee_asset=row_dict["Currency"],
            wallet=WALLET,
        )


DataParser(
    ParserType.EXCHANGE,
    "Bittrex Trades",
    ["Date", "Market", "Side", "Type", "Price", "Quantity", "Total"],
    worksheet_name="Bittrex T",
    row_handler=parse_bittrex_trades_v4,
)

DataParser(
    ParserType.EXCHANGE,
    "Bittrex Trades",
    [
        "Uuid",
        "Exchange",
        "Closed (UTC)",
        "Opened (UTC)",
        "Type",
        "Time In Force",
        "Bid/Ask",
        "Quantity",
        "Remaining",
        "Price",
        "Avg. Price per Share",
    ],
    worksheet_name="Bittrex T",
    row_handler=parse_bittrex_trades_v3,
)

DataParser(
    ParserType.EXCHANGE,
    "Bittrex Trades",
    [
        "Uuid",
        "Exchange",
        "TimeStamp",
        "OrderType",
        "Limit",
        "Quantity",
        "QuantityRemaining",
        "Commission",
        "Price",
        "PricePerUnit",
        "IsConditional",
        "Condition",
        "ConditionTarget",
        "ImmediateOrCancel",
        "Closed",
        "TimeInForceTypeId",
        "TimeInForce",
    ],
    worksheet_name="Bittrex T",
    row_handler=parse_bittrex_trades_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "Bittrex Trades",
    [
        "Uuid",
        "Exchange",
        "TimeStamp",
        "OrderType",
        "Limit",
        "Quantity",
        "QuantityRemaining",
        "Commission",
        "Price",
        "PricePerUnit",
        "IsConditional",
        "Condition",
        "ConditionTarget",
        "ImmediateOrCancel",
        "Closed",
    ],
    worksheet_name="Bittrex T",
    row_handler=parse_bittrex_trades_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "Bittrex Trades",
    [
        "OrderUuid",
        "Exchange",
        "Type",
        "Quantity",
        "Limit",
        "CommissionPaid",
        "Price",
        "Opened",
        "Closed",
    ],
    worksheet_name="Bittrex T",
    row_handler=parse_bittrex_trades_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "Bittrex Deposits/Withdrawals",
    ["Date", "Currency", "Type", "Address", "Memo/Tag", "TxId", "Amount"],
    worksheet_name="Bittrex D,W",
    row_handler=parse_bittrex_deposits_withdrawals,
)

DataParser(
    ParserType.EXCHANGE,
    "Bittrex Deposits",
    [
        "Id",
        "Currency",
        "Amount",
        "Confirmations",
        "LastUpdatedDate",
        "TxId",
        "CryptoAddress",
        "Source",
        "PropertyBagError",
        "BankInfo",
        "DepositUuid",
        "State",
    ],
    worksheet_name="Bittrex D",
    row_handler=parse_bittrex_deposits_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "Bittrex Deposits",
    [
        "Id",
        "Currency",
        "Amount",
        "Confirmations",
        "LastUpdatedDate",
        "TxId",
        "CryptoAddress",
        "Source",
    ],
    worksheet_name="Bittrex D",
    row_handler=parse_bittrex_deposits_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "Bittrex Deposits",
    [
        "Id",
        "Currency",
        "Amount",
        "Confirmations",
        "LastUpdatedDate",
        "TxId",
        "CryptoAddress",
    ],
    worksheet_name="Bittrex D",
    row_handler=parse_bittrex_deposits_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "Bittrex Deposits",
    [
        "Id",
        "Amount",
        "Currency",
        "Confirmations",
        "LastUpdated",
        "TxId",
        "CryptoAddress",
    ],
    worksheet_name="Bittrex D",
    row_handler=parse_bittrex_deposits_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "Bittrex Withdrawals",
    [
        "PaymentUuid",
        "Currency",
        "Amount",
        "Address",
        "OpenedDate",
        "Authorized",
        "Pending",
        "TxId",
        "TxFee",
        "Target",
        "BankInfo",
        "Canceled",
    ],
    worksheet_name="Bittrex W",
    row_handler=parse_bittrex_withdrawals,
)

DataParser(
    ParserType.EXCHANGE,
    "Bittrex Withdrawals",
    [
        "PaymentUuid",
        "Currency",
        "Amount",
        "Address",
        "OpenedDate",
        "Authorized",
        "Pending",
        "TxFee",
        "Canceled",
        "TxId",
    ],
    worksheet_name="Bittrex W",
    row_handler=parse_bittrex_withdrawals,
)

DataParser(
    ParserType.EXCHANGE,
    "Bittrex Withdrawals",
    [
        "PaymentUuid",
        "Currency",
        "Amount",
        "Address",
        "Opened",
        "Authorized",
        "PendingPayment",
        "TxCost",
        "TxId",
        "Canceled",
        "InvalidAddress",
    ],
    worksheet_name="Bittrex W",
    row_handler=parse_bittrex_withdrawals,
)
