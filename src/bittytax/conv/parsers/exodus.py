# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import re
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Tuple

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Exodus"


def parse_exodus_stake(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date"])

    if row_dict["Type"] == "Staking":
        data_row.t_record = TransactionOutRecord(
            TrType.STAKING_REWARD,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Buy"]),
            buy_asset=row_dict["Cur."],
            wallet=WALLET,
            note=row_dict["Comment"],
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def parse_exodus_v2(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["DATE"], fuzzy=True)
    data_row.tx_raw = TxRawPos(parser.in_header.index("TXID"))

    fee_quantity, fee_asset = _split_asset(row_dict["FEE"])

    if row_dict["TYPE"] == "deposit":
        buy_quantity, buy_asset = _split_asset(row_dict["COINAMOUNT"])

        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
            note=row_dict["PERSONALNOTE"],
        )
    elif row_dict["TYPE"] == "deposit (failed)":
        # Skip failures
        return
    elif row_dict["TYPE"] == "withdrawal":
        sell_quantity, sell_asset = _split_asset(row_dict["COINAMOUNT"])

        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
            note=row_dict["PERSONALNOTE"],
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("TYPE"), "TYPE", row_dict["TYPE"])


def _split_asset(coinamount: str) -> Tuple[Optional[Decimal], str]:
    match = re.match(r"^[-]?(\d+|[\d|,]*\.\d+) (\w+)$", coinamount)
    if match:
        return Decimal(match.group(1)), match.group(2)
    return None, ""


def parse_exodus_v1(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["DATE"], fuzzy=True)

    if row_dict["FEECURRENCY"]:
        fee_quantity = abs(Decimal(row_dict["FEEAMOUNT"]))
        fee_asset = row_dict["FEECURRENCY"]
    else:
        fee_quantity = None
        fee_asset = ""

    if row_dict["TYPE"] == "deposit":
        data_row.tx_raw = TxRawPos(parser.in_header.index("INTXID"))
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["INAMOUNT"]),
            buy_asset=row_dict["INCURRENCY"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
            note=row_dict["PERSONALNOTE"],
        )
    elif row_dict["TYPE"] == "deposit (failed)":
        # Skip failures
        return
    elif row_dict["TYPE"] == "withdrawal":
        data_row.tx_raw = TxRawPos(
            parser.in_header.index("OUTTXID"), tx_dest_pos=parser.in_header.index("TOADDRESS")
        )
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["OUTAMOUNT"])),
            sell_asset=row_dict["OUTCURRENCY"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
            note=row_dict["PERSONALNOTE"],
        )
    elif row_dict["TYPE"] == "exchange":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["INAMOUNT"]),
            buy_asset=row_dict["INCURRENCY"],
            sell_quantity=abs(Decimal(row_dict["OUTAMOUNT"])),
            sell_asset=row_dict["OUTCURRENCY"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
            note=row_dict["PERSONALNOTE"],
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("TYPE"), "TYPE", row_dict["TYPE"])


DataParser(
    ParserType.WALLET,
    "Exodus Staking",
    ["Type", "Buy", "Cur.", "Exchange", "Group", "Comment", "Date"],
    worksheet_name="Exodus",
    row_handler=parse_exodus_stake,
)

DataParser(
    ParserType.WALLET,
    "Exodus",
    [
        "TXID",
        "TXURL",
        "DATE",
        "TYPE",
        "FROMPORTFOLIO",
        "TOPORTFOLIO",
        "COINAMOUNT",
        "FEE",
        "BALANCE",
        "EXCHANGE",
        "PERSONALNOTE",
    ],
    worksheet_name="Exodus",
    row_handler=parse_exodus_v2,
)

DataParser(
    ParserType.WALLET,
    "Exodus",
    [
        "DATE",
        "TYPE",
        "FROMPORTFOLIO",
        "TOPORTFOLIO",
        "OUTAMOUNT",
        "OUTCURRENCY",
        "FEEAMOUNT",
        "FEECURRENCY",
        "TOADDRESS",
        "OUTTXID",
        "OUTTXURL",
        "INAMOUNT",
        "INCURRENCY",
        "INTXID",
        "INTXURL",
        "ORDERID",
        "PERSONALNOTE",
    ],
    worksheet_name="Exodus",
    row_handler=parse_exodus_v1,
)

DataParser(
    ParserType.WALLET,
    "Exodus",
    [
        "DATE",
        "TYPE",
        "FROMPORTFOLIO",
        "TOPORTFOLIO",
        "OUTAMOUNT",
        "OUTCURRENCY",
        "FEEAMOUNT",
        "FEECURRENCY",
        "OUTTXID",
        "OUTTXURL",
        "INAMOUNT",
        "INCURRENCY",
        "INTXID",
        "INTXURL",
        "ORDERID",
        "PERSONALNOTE",
        "TOADDRESS",
    ],
    worksheet_name="Exodus",
    row_handler=parse_exodus_v1,
)
