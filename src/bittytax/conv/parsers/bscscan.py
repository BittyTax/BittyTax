# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

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

WALLET = "Binance Smart Chain"
WORKSHEET_NAME = "BscScan"


def parse_bscscan(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("Txhash"),
        parser.in_header.index("From"),
        parser.in_header.index("To"),
    )

    if row_dict["Status"] != "":
        # Failed transactions should not have a Value_OUT
        row_dict["Value_OUT(BNB)"] = "0"

    if Decimal(row_dict["Value_IN(BNB)"]) > 0:
        if row_dict["Status"] == "":
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Value_IN(BNB)"]),
                buy_asset="BNB",
                wallet=_get_wallet(row_dict["To"]),
                note=_get_note(row_dict),
            )
    elif Decimal(row_dict["Value_OUT(BNB)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(BNB)"]),
            sell_asset="BNB",
            fee_quantity=Decimal(row_dict["TxnFee(BNB)"]),
            fee_asset="BNB",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(BNB)"]),
            sell_asset="BNB",
            fee_quantity=Decimal(row_dict["TxnFee(BNB)"]),
            fee_asset="BNB",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )


def _get_wallet(address: str) -> str:
    return f"{WALLET}-{address.lower()[0 : TransactionOutRecord.WALLET_ADDR_LEN]}"


def parse_bscscan_internal(
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

    if Decimal(row_dict["Value_IN(BNB)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Value_IN(BNB)"]),
            buy_asset="BNB",
            wallet=_get_wallet(row_dict["TxTo"]),
        )
    elif Decimal(row_dict["Value_OUT(BNB)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(BNB)"]),
            sell_asset="BNB",
            wallet=_get_wallet(row_dict["From"]),
        )


# Tokens and NFT transactions have the same header as Etherscan
bsc_txns = DataParser(
    ParserType.EXPLORER,
    "BscScan (BSC Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),
        "From",
        "To",
        "ContractAddress",
        "Value_IN(BNB)",
        "Value_OUT(BNB)",
        None,
        "TxnFee(BNB)",
        "TxnFee(USD)",
        "Historical $Price/BNB",
        "Status",
        "ErrCode",
        "Method",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_bscscan,
)

DataParser(
    ParserType.EXPLORER,
    "BscScan (BSC Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),
        "From",
        "To",
        "ContractAddress",
        "Value_IN(BNB)",
        "Value_OUT(BNB)",
        None,
        "TxnFee(BNB)",
        "TxnFee(USD)",
        "Historical $Price/BNB",
        "Status",
        "ErrCode",
        "Method",
        "PrivateNote",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_bscscan,
)

DataParser(
    ParserType.EXPLORER,
    "BscScan (BSC Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime",
        "From",
        "To",
        "ContractAddress",
        "Value_IN(BNB)",
        "Value_OUT(BNB)",
        None,
        "TxnFee(BNB)",
        "TxnFee(USD)",
        "Historical $Price/BNB",
        "Status",
        "ErrCode",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_bscscan,
)

DataParser(
    ParserType.EXPLORER,
    "BscScan (BSC Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime",
        "From",
        "To",
        "ContractAddress",
        "Value_IN(BNB)",
        "Value_OUT(BNB)",
        None,
        "TxnFee(BNB)",
        "TxnFee(USD)",
        "Historical $Price/BNB",
        "Status",
        "ErrCode",
        "PrivateNote",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_bscscan,
)

bsc_int = DataParser(
    ParserType.EXPLORER,
    "BscScan (BSC Internal Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),
        "ParentTxFrom",
        "ParentTxTo",
        lambda c: c in ("ParentTxETH_Value", "ParentTxBNB_Value"),
        "From",
        "TxTo",
        "ContractAddress",
        "Value_IN(BNB)",
        "Value_OUT(BNB)",
        None,
        "Historical $Price/BNB",
        "Status",
        "ErrCode",
        "Type",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_bscscan_internal,
)

DataParser(
    ParserType.EXPLORER,
    "BscScan (BSC Internal Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),
        "ParentTxFrom",
        "ParentTxTo",
        lambda c: c in ("ParentTxETH_Value", "ParentTxBNB_Value"),
        "From",
        "TxTo",
        "ContractAddress",
        "Value_IN(BNB)",
        "Value_OUT(BNB)",
        None,
        "Historical $Price/BNB",
        "Status",
        "ErrCode",
        "Type",
        "PrivateNote",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_bscscan_internal,
)
