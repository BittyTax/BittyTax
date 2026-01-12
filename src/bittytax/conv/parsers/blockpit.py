# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

from decimal import Decimal
from typing import TYPE_CHECKING, Union

from typing_extensions import Unpack

from ...bt_types import TrType, UnmappedType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

BLOCKPIT_D_MAPPING = {
    "Airdrop": TrType.AIRDROP,
    "Bounties": TrType.REFERRAL,
    "Deposit": TrType.DEPOSIT,
    "Lending": TrType.STAKING_REWARD,
    "Margin_trading_profit": TrType.MARGIN_GAIN,
    "Staking": TrType.STAKING_REWARD,
}

BLOCKPIT_W_MAPPING = {
    "Fee": TrType.SPEND,
    "Margin_trading_fee": TrType.MARGIN_FEE,
    "Margin_trading_loss": TrType.MARGIN_LOSS,
    "Withdrawal": TrType.WITHDRAWAL,
}


def parse_blockpit(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    if "Timestamp" in row_dict:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["Timestamp"])
        if row_dict["Transaction ID"]:
            data_row.tx_raw = TxRawPos(parser.in_header.index("Transaction ID"))

        row_dict["Fee Asset (optional)"] = row_dict["Fee Asset"]
        row_dict["Fee Amount (optional)"] = row_dict["Fee Amount"]
        row_dict["Comment (optional)"] = row_dict["Note"]
        row_dict["Label"] = row_dict["Transaction Type"]
    else:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["Date (UTC)"])
        if row_dict["Trx. ID (optional)"]:
            data_row.tx_raw = TxRawPos(parser.in_header.index("Trx. ID (optional)"))

    if row_dict["Fee Asset (optional)"]:
        fee_quantity = Decimal(row_dict["Fee Amount (optional)"])
        fee_asset = row_dict["Fee Asset (optional)"]
    else:
        fee_quantity = None
        fee_asset = ""

    if row_dict["Incoming Asset"] and row_dict["Outgoing Asset"]:
        if row_dict["Label"] == "Trade":
            t_type: Union[TrType, UnmappedType] = TrType.TRADE
        else:
            t_type = UnmappedType(f'_{row_dict["Label"]}')

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
            note=row_dict["Comment (optional)"],
        )
    elif row_dict["Incoming Asset"]:
        if row_dict["Label"] in BLOCKPIT_D_MAPPING:
            t_type = BLOCKPIT_D_MAPPING[row_dict["Label"]]
        else:
            t_type = UnmappedType(f'_{row_dict["Label"]}')

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Incoming Amount"]),
            buy_asset=row_dict["Incoming Asset"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=row_dict["Source Name"],
            note=row_dict["Comment (optional)"],
        )
    elif row_dict["Outgoing Asset"]:
        if row_dict["Label"] in BLOCKPIT_W_MAPPING:
            t_type = BLOCKPIT_W_MAPPING[row_dict["Label"]]
        else:
            t_type = UnmappedType(f'_{row_dict["Label"]}')

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Outgoing Amount"]),
            sell_asset=row_dict["Outgoing Asset"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=row_dict["Source Name"],
            note=row_dict["Comment (optional)"],
        )


DataParser(
    ParserType.ACCOUNTING,
    "Blockpit",
    [
        "Date (UTC)",
        "Integration Name",
        "Label",
        "Outgoing Asset",
        "Outgoing Amount",
        "Incoming Asset",
        "Incoming Amount",
        "Fee Asset (optional)",
        "Fee Amount (optional)",
        "Comment (optional)",
        "Trx. ID (optional)",
        "Source Type",
        "Source Name",
    ],
    worksheet_name="Blockpit",
    row_handler=parse_blockpit,
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
