# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import ROUND_DOWN, Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "TradeSatoshi"

PRECISION = Decimal("0.00000000")


def parse_tradesatoshi_deposits_v2(
    data_row: "DataRow", _parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    parse_tradesatoshi_deposits_v1(data_row, _parser, **kwargs)


def parse_tradesatoshi_deposits_v1(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["TimeStamp"])
    data_row.tx_raw = TxRawPos(parser.in_header.index("TxId"))

    data_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount"]),
        buy_asset=row_dict["Symbol"],
        wallet=WALLET,
    )


def parse_tradesatoshi_withdrawals_v2(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["TimeStamp"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TxId"), tx_dest_pos=parser.in_header.index("Address")
    )

    data_row.t_record = TransactionOutRecord(
        TrType.WITHDRAWAL,
        data_row.timestamp,
        sell_quantity=Decimal(row_dict["Amount"]),
        sell_asset=row_dict["Symbol"],
        wallet=WALLET,
    )


def parse_tradesatoshi_withdrawals_v1(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["TimeStamp"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TxId"), tx_dest_pos=parser.in_header.index("Address")
    )

    data_row.t_record = TransactionOutRecord(
        TrType.WITHDRAWAL,
        data_row.timestamp,
        sell_quantity=Decimal(row_dict["Amount"]) - Decimal(row_dict["Fee"]),
        sell_asset=row_dict["Symbol"],
        fee_quantity=Decimal(row_dict["Fee"]),
        fee_asset=row_dict["Symbol"],
        wallet=WALLET,
    )


def parse_tradesatoshi_trades(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(data_row.row[6])

    if data_row.row[2] == "Buy":
        sell_quantity = Decimal(row_dict["Amount"]) * Decimal(row_dict["Rate"])

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["TradePair"].split("/")[0],
            sell_quantity=sell_quantity.quantize(PRECISION, rounding=ROUND_DOWN),
            sell_asset=row_dict["TradePair"].split("/")[1],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["TradePair"].split("/")[1],
            wallet=WALLET,
        )
    elif data_row.row[2] == "Sell":
        buy_quantity = Decimal(row_dict["Amount"]) * Decimal(row_dict["Rate"])

        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=buy_quantity.quantize(PRECISION, rounding=ROUND_DOWN),
            buy_asset=row_dict["TradePair"].split("/")[1],
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["TradePair"].split("/")[0],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["TradePair"].split("/")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], data_row.row[2])


DataParser(
    ParserType.EXCHANGE,
    "TradeSatoshi Deposits",
    ["TimeStamp", "Currency", "Symbol", "Amount", "Confirmation", "TxId"],
    worksheet_name="TradeSatoshi D",
    row_handler=parse_tradesatoshi_deposits_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "TradeSatoshi Deposits",
    [
        "Id",
        "Currency",
        "Symbol",
        "Amount",
        "Status",
        "Confirmations",
        "TxId",
        "TimeStamp",
    ],
    worksheet_name="TradeSatoshi D",
    row_handler=parse_tradesatoshi_deposits_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "TradeSatoshi Withdrawals",
    [
        "TimeStamp",
        "Currency",
        "Symbol",
        "Amount",
        "Confirmation",
        "TxId",
        "Address",
        "PaymentId",
        "Status",
    ],
    worksheet_name="TradeSatoshi W",
    row_handler=parse_tradesatoshi_withdrawals_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "TradeSatoshi Withdrawals",
    [
        "Id",
        "User",
        "Symbol",
        "Amount",
        "Fee",
        "Net Amount",
        "Status",
        "Confirmations",
        "TxId",
        "Address",
        "TimeStamp",
    ],
    worksheet_name="TradeSatoshi W",
    row_handler=parse_tradesatoshi_withdrawals_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "TradeSatoshi Trades",
    [
        "Id",
        "TradePair",
        lambda c: c in ("TradeType", "TradeHistoryType"),
        "Amount",
        "Rate",
        "Fee",
        lambda c: c.lower() == "timestamp",
        "IsApi",
    ],
    worksheet_name="TradeSatoshi T",
    row_handler=parse_tradesatoshi_trades,
)
