# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..out_record import TransactionOutRecord
from .etherscan import _get_note

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Fantom Chain"
WORKSHEET_NAME = "FTMScan"


def parse_ftmscan(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("Txhash"),
        parser.in_header.index("From"),
        parser.in_header.index("To"),
    )

    if row_dict["Status"] != "":
        # Failed transactions should not have a Value_OUT
        row_dict["Value_OUT(FTM)"] = "0"

    if Decimal(row_dict["Value_IN(FTM)"]) > 0:
        if row_dict["Status"] == "":
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Value_IN(FTM)"]),
                buy_asset="FTM",
                wallet=_get_wallet(row_dict["To"]),
                note=_get_note(row_dict),
            )
    elif Decimal(row_dict["Value_OUT(FTM)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(FTM)"]),
            sell_asset="FTM",
            fee_quantity=Decimal(row_dict["TxnFee(FTM)"]),
            fee_asset="FTM",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(FTM)"]),
            sell_asset="FTM",
            fee_quantity=Decimal(row_dict["TxnFee(FTM)"]),
            fee_asset="FTM",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )


def _get_wallet(address: str) -> str:
    return f"{WALLET}-{address.lower()[0 : TransactionOutRecord.WALLET_ADDR_LEN]}"


def parse_ftmscan_internal(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("Txhash"),
        parser.in_header.index("From"),
        parser.in_header.index("TxTo"),
    )

    # Failed internal transaction
    if row_dict["Status"] != "0":
        return

    if Decimal(row_dict["Value_IN(FTM)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Value_IN(FTM)"]),
            buy_asset="FTM",
            wallet=_get_wallet(row_dict["TxTo"]),
        )
    elif Decimal(row_dict["Value_OUT(FTM)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(FTM)"]),
            sell_asset="FTM",
            wallet=_get_wallet(row_dict["From"]),
        )


# Token and NFT transactions have the same header as Etherscan
ftm_txns = DataParser(
    ParserType.EXPLORER,
    "FTMScan (FTM Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime (UTC)",
        "From",
        "To",
        "ContractAddress",
        "Value_IN(FTM)",
        "Value_OUT(FTM)",
        None,
        "TxnFee(FTM)",
        "TxnFee(USD)",
        "Historical $Price/FTM",
        "Status",
        "ErrCode",
        "Method",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_ftmscan,
)

DataParser(
    ParserType.EXPLORER,
    "FTMScan (FTM Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime (UTC)",
        "From",
        "To",
        "ContractAddress",
        "Value_IN(FTM)",
        "Value_OUT(FTM)",
        None,
        "TxnFee(FTM)",
        "TxnFee(USD)",
        "Historical $Price/FTM",
        "Status",
        "ErrCode",
        "Method",
        "PrivateNote",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_ftmscan,
)

ftm_int = DataParser(
    ParserType.EXPLORER,
    "FTMScan (FTM Internal Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime (UTC)",
        "ParentTxFrom",
        "ParentTxTo",
        "ParentTxFTM_Value",
        "From",
        "TxTo",
        "ContractAddress",
        "Value_IN(FTM)",
        "Value_OUT(FTM)",
        None,
        "Historical $Price/FTM",
        "Status",
        "ErrCode",
        "Type",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_ftmscan_internal,
)

DataParser(
    ParserType.EXPLORER,
    "FTMScan (FTM Internal Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime (UTC)",
        "ParentTxFrom",
        "ParentTxTo",
        "ParentTxFTM_Value",
        "From",
        "TxTo",
        "ContractAddress",
        "Value_IN(FTM)",
        "Value_OUT(FTM)",
        None,
        "Historical $Price/FTM",
        "Status",
        "ErrCode",
        "Type",
        "PrivateNote",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_ftmscan_internal,
)
