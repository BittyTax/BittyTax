# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

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

PRECISION = Decimal("0." + "0" * 8)

WALLET = "TradeOgre"


def parse_tradeogre_deposits(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])
    data_row.tx_raw = TxRawPos(parser.in_header.index("TXID"))

    data_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount"]),
        buy_asset=row_dict["Coin"],
        wallet=WALLET,
    )


def parse_tradeogre_withdrawals(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("TXID"), tx_dest_pos=parser.in_header.index("Address")
    )

    data_row.t_record = TransactionOutRecord(
        TrType.WITHDRAWAL,
        data_row.timestamp,
        sell_quantity=Decimal(row_dict["Amount"]) - Decimal(row_dict["Fee"]),
        sell_asset=row_dict["Coin"],
        fee_quantity=Decimal(row_dict["Fee"]),
        fee_asset=row_dict["Coin"],
        wallet=WALLET,
    )


def parse_tradeogre_trades(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["Type"] == "BUY":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Exchange"].split("-")[1],
            sell_quantity=(Decimal(row_dict["Amount"]) * Decimal(row_dict["Price"])).quantize(
                PRECISION, rounding="ROUND_DOWN"
            ),
            sell_asset=row_dict["Exchange"].split("-")[0],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Exchange"].split("-")[0],
            wallet=WALLET,
        )
    elif row_dict["Type"] == "SELL":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=(Decimal(row_dict["Amount"]) * Decimal(row_dict["Price"])).quantize(
                PRECISION, rounding="ROUND_DOWN"
            ),
            buy_asset=row_dict["Exchange"].split("-")[0],
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Exchange"].split("-")[1],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Exchange"].split("-")[0],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


DataParser(
    ParserType.EXCHANGE,
    "TradeOgre Deposits",
    ["Date", "Coin", "TXID", "Amount"],
    worksheet_name="TradeOgre D",
    row_handler=parse_tradeogre_deposits,
)

DataParser(
    ParserType.EXCHANGE,
    "TradeOgre Withdrawals",
    ["Date", "Coin", "TXID", "Amount", "Fee", "Address", "Payment ID"],
    worksheet_name="TradeOgre W",
    row_handler=parse_tradeogre_withdrawals,
)

DataParser(
    ParserType.EXCHANGE,
    "TradeOgre Trades",
    ["Type", "Exchange", "Date", "Amount", "Price", "Fee"],
    worksheet_name="TradeOgre T",
    row_handler=parse_tradeogre_trades,
)
