# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..out_record import TransactionOutRecord
from .etherscan import _get_note

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Huobi Eco Chain"
WORKSHEET_NAME = "HecoInfo"


def parse_hecoinfo(data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))

    if row_dict["Status"] != "":
        # Failed transactions should not have a Value_OUT
        row_dict["Value_OUT(HT)"] = "0"

    if Decimal(row_dict["Value_IN(HT)"]) > 0:
        if row_dict["Status"] == "":
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Value_IN(HT)"]),
                buy_asset="HT",
                wallet=_get_wallet(row_dict["To"]),
                note=_get_note(row_dict),
            )
    elif Decimal(row_dict["Value_OUT(HT)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(HT)"]),
            sell_asset="HT",
            fee_quantity=Decimal(row_dict["TxnFee(HT)"]),
            fee_asset="HT",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(HT)"]),
            sell_asset="HT",
            fee_quantity=Decimal(row_dict["TxnFee(HT)"]),
            fee_asset="HT",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )


def _get_wallet(address: str) -> str:
    return f"{WALLET}-{address.lower()[0 : TransactionOutRecord.WALLET_ADDR_LEN]}"


def parse_hecoinfo_internal(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))

    # Failed internal transaction
    if row_dict["Status"] != "0":
        return

    if Decimal(row_dict["Value_IN(HT)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Value_IN(HT)"]),
            buy_asset="HT",
            wallet=_get_wallet(row_dict["TxTo"]),
        )
    elif Decimal(row_dict["Value_OUT(HT)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(HT)"]),
            sell_asset="HT",
            wallet=_get_wallet(row_dict["From"]),
        )


# Token and NFT transactions have the same header as Etherscan
heco_txns = DataParser(
    ParserType.EXPLORER,
    "HecoInfo (HECO Transactions)",
    [
        lambda c: c in ("Txhash", "Transaction Hash"),  # Renamed
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),  # Renamed
        "From",
        "To",
        "ContractAddress",
        "Value_IN(HT)",
        "Value_OUT(HT)",
        None,
        "TxnFee(HT)",
        "TxnFee(USD)",
        "Historical $Price/HT",
        "Status",
        "ErrCode",
        "Method",  # New field
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_hecoinfo,
)

DataParser(
    ParserType.EXPLORER,
    "HecoInfo (HECO Transactions)",
    [
        lambda c: c in ("Txhash", "Transaction Hash"),  # Renamed
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),  # Renamed
        "From",
        "To",
        "ContractAddress",
        "Value_IN(HT)",
        "Value_OUT(HT)",
        None,
        "TxnFee(HT)",
        "TxnFee(USD)",
        "Historical $Price/HT",
        "Status",
        "ErrCode",
        "Method",  # New field
        "PrivateNote",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_hecoinfo,
)

DataParser(
    ParserType.EXPLORER,
    "HecoInfo (HECO Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime",
        "From",
        "To",
        "ContractAddress",
        "Value_IN(HT)",
        "Value_OUT(HT)",
        None,
        "TxnFee(HT)",
        "TxnFee(USD)",
        "Historical $Price/HT",
        "Status",
        "ErrCode",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_hecoinfo,
)

DataParser(
    ParserType.EXPLORER,
    "HecoInfo (HECO Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime",
        "From",
        "To",
        "ContractAddress",
        "Value_IN(HT)",
        "Value_OUT(HT)",
        None,
        "TxnFee(HT)",
        "TxnFee(USD)",
        "Historical $Price/HT",
        "Status",
        "ErrCode",
        "PrivateNote",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_hecoinfo,
)

heco_int = DataParser(
    ParserType.EXPLORER,
    "HecoInfo (HECO Internal Transactions)",
    [
        lambda c: c in ("Txhash", "Transaction Hash"),  # Renamed
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),  # Renamed
        "ParentTxFrom",
        "ParentTxTo",
        "ParentTxETH_Value",
        "From",
        "TxTo",
        "ContractAddress",
        "Value_IN(HT)",
        "Value_OUT(HT)",
        None,
        "Historical $Price/HT",
        "Status",
        "ErrCode",
        "Type",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_hecoinfo_internal,
)

DataParser(
    ParserType.EXPLORER,
    "HecoInfo (HECO Internal Transactions)",
    [
        lambda c: c in ("Txhash", "Transaction Hash"),  # Renamed
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),  # Renamed
        "ParentTxFrom",
        "ParentTxTo",
        "ParentTxETH_Value",
        "From",
        "TxTo",
        "ContractAddress",
        "Value_IN(HT)",
        "Value_OUT(HT)",
        None,
        "Historical $Price/HT",
        "Status",
        "ErrCode",
        "Type",
        "PrivateNote",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_hecoinfo_internal,
)
