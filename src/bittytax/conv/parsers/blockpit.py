# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

from decimal import Decimal
from typing import TYPE_CHECKING, Union

from typing_extensions import Unpack

from ...bt_types import TrType, UnmappedType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

BLOCKPIT_D_MAPPING = {
    "Airdrop": TrType.AIRDROP,
    "Bounties": TrType.AIRDROP,  # Change to REFERRAL when merged
    "Deposit": TrType.DEPOSIT,
    "Lending": TrType.STAKING,
    "Margin_trading_profit": TrType.MARGIN_GAIN,
    "Staking": TrType.STAKING,
}

BLOCKPIT_W_MAPPING = {
    "Fee": TrType.SPEND,
    "Margin_trading_fee": TrType.MARGIN_FEE,
    "Margin_trading_loss": TrType.MARGIN_LOSS,
    "Withdrawal": TrType.WITHDRAWAL,
}


def parse_blockpit(data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Timestamp"])

    if row_dict["Fee Asset"]:
        fee_quantity = Decimal(row_dict["Fee Amount"])
        fee_asset = row_dict["Fee Asset"]
    else:
        fee_quantity = None
        fee_asset = ""

    if row_dict["Incoming Asset"] and row_dict["Outgoing Asset"]:
        if row_dict["Transaction Type"] == "Trade":
            t_type: Union[TrType, UnmappedType] = TrType.TRADE
        else:
            t_type = UnmappedType(f'_{row_dict["Transaction Type"]}')

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Incoming Amount"]),
            buy_asset=row_dict["Incoming Asset"],
            sell_quantity=Decimal(row_dict["Outgoing Amount"]),
            sell_asset=row_dict["Outgoing Asset"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=row_dict["Source Name"],
            note=row_dict["Note"],
        )
    elif row_dict["Incoming Asset"]:
        if row_dict["Transaction Type"] in BLOCKPIT_D_MAPPING:
            t_type = BLOCKPIT_D_MAPPING[row_dict["Transaction Type"]]
        else:
            t_type = UnmappedType(f'_{row_dict["Transaction Type"]}')

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Incoming Amount"]),
            buy_asset=row_dict["Incoming Asset"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=row_dict["Source Name"],
            note=row_dict["Note"],
        )
    elif row_dict["Outgoing Asset"]:
        if row_dict["Transaction Type"] in BLOCKPIT_W_MAPPING:
            t_type = BLOCKPIT_W_MAPPING[row_dict["Transaction Type"]]
        else:
            t_type = UnmappedType(f'_{row_dict["Transaction Type"]}')

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Outgoing Amount"]),
            sell_asset=row_dict["Outgoing Asset"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=row_dict["Source Name"],
            note=row_dict["Note"],
        )


DataParser(
    ParserType.ACCOUNTING,
    "Blockpit",
    [
        "Blockpit ID",
        "Timestamp",
        "Source Type",
        "Source Name",
        "Integration",
        "Transaction Type",
        "Outgoing Asset",
        "Outgoing Amount",
        "Incoming Asset",
        "Incoming Amount",
        "Fee Asset",
        "Fee Amount",
        "Transaction ID",
        "Note",
        "Merge ID",
    ],
    worksheet_name="Blockpit",
    row_handler=parse_blockpit,
)
