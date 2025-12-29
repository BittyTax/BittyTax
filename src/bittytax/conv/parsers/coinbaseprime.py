# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2025

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Coinbase Prime"


def parse_coinbase_prime_staking(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Date/Time of Reward"])

    amount_ccy = DataParser.convert_currency(
        row_dict["Amount of Reward (notional USD)"],
        "USD",
        data_row.timestamp,
    )

    data_row.t_record = TransactionOutRecord(
        TrType.STAKING_REWARD,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount of Reward"]),
        buy_asset=row_dict["Reward Currency"],
        buy_value=amount_ccy,
        wallet=WALLET,
    )


DataParser(
    ParserType.EXCHANGE,
    "Coinbase Prime Staking",
    [
        "Portfolio",
        "Portfolio ID",
        "Entity Name",
        "Entity ID",
        "Wallet Name",
        "Wallet ID",
        "Wallet Address",
        "Reward Address",
        "Wallet Type",
        "Staked Asset",
        "Reward Currency",
        "Date/Time of Reward",
        "Type of Reward",
        "Transaction ID",
        "Blockchain Explorer Link",
        "Amount of Reward",
        "Validator Address",
        "Validator Type",
        "Amount of Reward (notional USD)",
    ],
    worksheet_name="Coinbase Prime S",
    row_handler=parse_coinbase_prime_staking,
)
