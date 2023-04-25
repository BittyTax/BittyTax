# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal

from ..dataparser import DataParser
from ..out_record import TransactionOutRecord
from .etherscan import _get_note

WALLET = "Huobi Eco Chain"
WORKSHEET_NAME = "HecoInfo"


def parse_hecoinfo(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))

    if row_dict["Status"] != "":
        # Failed transactions should not have a Value_OUT
        row_dict["Value_OUT(HT)"] = 0

    if Decimal(row_dict["Value_IN(HT)"]) > 0:
        if row_dict["Status"] == "":
            data_row.t_record = TransactionOutRecord(
                TransactionOutRecord.TYPE_DEPOSIT,
                data_row.timestamp,
                buy_quantity=row_dict["Value_IN(HT)"],
                buy_asset="HT",
                wallet=_get_wallet(row_dict["To"]),
                note=_get_note(row_dict),
            )
    elif Decimal(row_dict["Value_OUT(HT)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=row_dict["Value_OUT(HT)"],
            sell_asset="HT",
            fee_quantity=row_dict["TxnFee(HT)"],
            fee_asset="HT",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_SPEND,
            data_row.timestamp,
            sell_quantity=row_dict["Value_OUT(HT)"],
            sell_asset="HT",
            fee_quantity=row_dict["TxnFee(HT)"],
            fee_asset="HT",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )


def _get_wallet(address):
    return f"{WALLET}-{address.lower()[0 : TransactionOutRecord.WALLET_ADDR_LEN]}"


def parse_hecoinfo_internal(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))

    # Failed internal transaction
    if row_dict["Status"] != "0":
        return

    if Decimal(row_dict["Value_IN(HT)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["Value_IN(HT)"],
            buy_asset="HT",
            wallet=_get_wallet(row_dict["TxTo"]),
        )
    elif Decimal(row_dict["Value_OUT(HT)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=row_dict["Value_OUT(HT)"],
            sell_asset="HT",
            wallet=_get_wallet(row_dict["From"]),
        )


# Tokens and internal transactions have the same header as Etherscan
HECO_TXNS = DataParser(
    DataParser.TYPE_EXPLORER,
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
    DataParser.TYPE_EXPLORER,
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

DataParser(
    DataParser.TYPE_EXPLORER,
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
        "Method",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_hecoinfo,
)

DataParser(
    DataParser.TYPE_EXPLORER,
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
        "Method",
        "PrivateNote",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_hecoinfo,
)

HECO_INT = DataParser(
    DataParser.TYPE_EXPLORER,
    "HecoInfo (HECO Internal Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime",
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
    DataParser.TYPE_EXPLORER,
    "HecoInfo (HECO Internal Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime",
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
