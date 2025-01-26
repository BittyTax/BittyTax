# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import re
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Tuple

from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import UnexpectedContentError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "CoinCorner"


def parse_coincorner_v2(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(
        row_dict["Date & Time"], dayfirst=config.date_is_day_first, tz=config.local_timezone
    )

    if row_dict["Fee"]:
        fee_quantity = Decimal(row_dict["Fee"])
        fee_asset = row_dict["Fee Currency"]
    else:
        fee_quantity = None
        fee_asset = ""

    if row_dict["Type"] == "Receive":
        data_row.tx_raw = TxRawPos(
            parser.in_header.index("Tx ID"), tx_dest_pos=parser.in_header.index("Detail")
        )
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Gross"]),
            buy_asset=row_dict["Gross Currency"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Bank deposit":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Gross"]),
            buy_asset=row_dict["Gross Currency"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Send":
        data_row.tx_raw = TxRawPos(
            parser.in_header.index("Tx ID"), tx_dest_pos=parser.in_header.index("Detail")
        )
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Net"])),
            sell_asset=row_dict["Net Currency"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Bank withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Net"])),
            sell_asset=row_dict["Net Currency"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    elif row_dict["Type"] == "Trade":
        if row_dict["Gross Currency"] not in ("GBP", "EUR"):
            # Use only fiat transactions for trades as these contain fees
            return

        quantity, asset = _get_crypto(row_dict["Detail"])
        if quantity is None:
            raise UnexpectedContentError(
                parser.in_header.index("Detail"), "Detail", row_dict["Detail"]
            )

        if Decimal(row_dict["Gross"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Gross"]),
                buy_asset=row_dict["Gross Currency"],
                sell_quantity=quantity,
                sell_asset=asset,
                fee_quantity=fee_quantity,
                fee_asset=fee_asset,
                wallet=WALLET,
            )
        elif Decimal(row_dict["Gross"]) < 0:
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=quantity,
                buy_asset=asset,
                sell_quantity=abs(Decimal(row_dict["Net"])),
                sell_asset=row_dict["Net Currency"],
                fee_quantity=fee_quantity,
                fee_asset=fee_asset,
                wallet=WALLET,
            )
    elif row_dict["Type"] == "FPS":
        # This looks like a CoinCorner bug, everything is FPS
        quantity, asset = _get_crypto(row_dict["Detail"])
        if quantity is not None:
            # Must be a trade
            if Decimal(row_dict["Gross"]) > 0:
                data_row.t_record = TransactionOutRecord(
                    TrType.TRADE,
                    data_row.timestamp,
                    buy_quantity=Decimal(row_dict["Gross"]),
                    buy_asset=row_dict["Gross Currency"],
                    sell_quantity=quantity,
                    sell_asset=asset,
                    fee_quantity=fee_quantity,
                    fee_asset=fee_asset,
                    wallet=WALLET,
                )
            elif Decimal(row_dict["Gross"]) < 0:
                data_row.t_record = TransactionOutRecord(
                    TrType.TRADE,
                    data_row.timestamp,
                    buy_quantity=quantity,
                    buy_asset=asset,
                    sell_quantity=abs(Decimal(row_dict["Net"])),
                    sell_asset=row_dict["Net Currency"],
                    fee_quantity=fee_quantity,
                    fee_asset=fee_asset,
                    wallet=WALLET,
                )
        else:
            # Otherwise it is a Bank transfer
            if Decimal(row_dict["Gross"]) > 0:
                data_row.t_record = TransactionOutRecord(
                    TrType.DEPOSIT,
                    data_row.timestamp,
                    buy_quantity=Decimal(row_dict["Gross"]),
                    buy_asset=row_dict["Gross Currency"],
                    fee_quantity=fee_quantity,
                    fee_asset=fee_asset,
                    wallet=WALLET,
                )
            elif Decimal(row_dict["Gross"]) < 0:
                data_row.t_record = TransactionOutRecord(
                    TrType.WITHDRAWAL,
                    data_row.timestamp,
                    sell_quantity=abs(Decimal(row_dict["Net"])),
                    sell_asset=row_dict["Net Currency"],
                    fee_quantity=fee_quantity,
                    fee_asset=fee_asset,
                    wallet=WALLET,
                )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _get_crypto(detail: str) -> Tuple[Optional[Decimal], str]:
    match = re.match(r".*(?:Bought|Sold) ([\d|,]+\.\d+|[\d|,]+) (\w+)$", detail)

    if match:
        return Decimal(match.group(1)), match.group(2)
    return None, ""


def parse_coincorner_v1(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(
        row_dict["Date"], dayfirst=config.date_is_day_first, tz=config.local_timezone
    )

    t_type = row_dict["Transaction Type"].strip()

    if t_type in ("Bank Deposit", "Coinfloor Balance Transfer"):
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"],
            wallet=WALLET,
        )
    elif t_type == "Bank Withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Currency"],
            wallet=WALLET,
        )
    elif t_type == "Bought Bitcoin":
        if row_dict["Currency"] == "BTC":
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount"]),
                buy_asset=row_dict["Currency"],
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["Amount"]),
                sell_asset=row_dict["Currency"],
                wallet=WALLET,
            )
    elif t_type == "Sold Bitcoin":
        if row_dict["Currency"] == "BTC":
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                sell_quantity=Decimal(row_dict["Amount"]),
                sell_asset=row_dict["Currency"],
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount"]),
                buy_asset=row_dict["Currency"],
                wallet=WALLET,
            )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Transaction Type"),
            "Transaction Type",
            t_type,
        )


DataParser(
    ParserType.EXCHANGE,
    "CoinCorner",
    [
        "Date & Time",
        "Store/Website",
        "Detail",
        "Type",
        "Tx ID",
        "Price",
        "Price Currency",
        "Gross",
        "Gross Currency",
        "Fee",
        "Fee Currency",
        "Net",
        "Net Currency",
        "Balance",
        "Balance Currency",
    ],
    worksheet_name="CoinCorner",
    row_handler=parse_coincorner_v2,
)


coincorner = DataParser(
    ParserType.EXCHANGE,
    "CoinCorner",
    ["Date", "Currency", "Transaction Type", "Amount", "Balance"],
    worksheet_name="CoinCorner",
    row_handler=parse_coincorner_v1,
)
