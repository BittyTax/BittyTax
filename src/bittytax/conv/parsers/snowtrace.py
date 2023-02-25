# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal

from ..dataparser import DataParser
from ..out_record import TransactionOutRecord
from .etherscan import _get_note

WALLET = "Avalanche chain"
WORKSHEET_NAME = "SnowTrace"


def parse_snowtrace(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))

    if row_dict["Status"] != "":
        # Failed transactions should not have a Value_OUT
        row_dict["Value_OUT(AVAX)"] = 0

    if Decimal(row_dict["Value_IN(AVAX)"]) > 0:
        if row_dict["Status"] == "":
            data_row.t_record = TransactionOutRecord(
                TransactionOutRecord.TYPE_DEPOSIT,
                data_row.timestamp,
                buy_quantity=row_dict["Value_IN(AVAX)"],
                buy_asset="AVAX",
                wallet=_get_wallet(row_dict["To"]),
                note=_get_note(row_dict),
            )
    elif Decimal(row_dict["Value_OUT(AVAX)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=row_dict["Value_OUT(AVAX)"],
            sell_asset="AVAX",
            fee_quantity=row_dict["TxnFee(AVAX)"],
            fee_asset="AVAX",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_SPEND,
            data_row.timestamp,
            sell_quantity=row_dict["Value_OUT(AVAX)"],
            sell_asset="AVAX",
            fee_quantity=row_dict["TxnFee(AVAX)"],
            fee_asset="AVAX",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )


def _get_wallet(address):
    return "%s-%s" % (WALLET, address.lower()[0 : TransactionOutRecord.WALLET_ADDR_LEN])


def parse_snowtrace_internal(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))

    # Failed internal transaction
    if row_dict["Status"] != "0":
        return

    if Decimal(row_dict["Value_IN(AVAX)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["Value_IN(AVAX)"],
            buy_asset="AVAX",
            wallet=_get_wallet(row_dict["TxTo"]),
        )
    elif Decimal(row_dict["Value_OUT(AVAX)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=row_dict["Value_OUT(AVAX)"],
            sell_asset="AVAX",
            wallet=_get_wallet(row_dict["From"]),
        )


# Tokens and internal transactions have the same header as Etherscan
AVAX_TXNS = DataParser(
    DataParser.TYPE_EXPLORER,
    "SnowTrace (AVAX Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime",
        "From",
        "To",
        "ContractAddress",
        "Value_IN(AVAX)",
        "Value_OUT(AVAX)",
        None,
        "TxnFee(AVAX)",
        "TxnFee(USD)",
        "Historical $Price/AVAX",
        "Status",
        "ErrCode",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_snowtrace,
)

DataParser(
    DataParser.TYPE_EXPLORER,
    "SnowTrace (AVAX Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime",
        "From",
        "To",
        "ContractAddress",
        "Value_IN(AVAX)",
        "Value_OUT(AVAX)",
        None,
        "TxnFee(AVAX)",
        "TxnFee(USD)",
        "Historical $Price/AVAX",
        "Status",
        "ErrCode",
        "PrivateNote",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_snowtrace,
)

AVAX_INT = DataParser(
    DataParser.TYPE_EXPLORER,
    "SnowTrace (AVAX Internal Transactions)",
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
        "Value_IN(AVAX)",
        "Value_OUT(AVAX)",
        None,
        "Historical $Price/AVAX",
        "Status",
        "ErrCode",
        "Type",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_snowtrace_internal,
)

DataParser(
    DataParser.TYPE_EXPLORER,
    "SnowTrace (AVAX Internal Transactions)",
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
        "Value_IN(AVAX)",
        "Value_OUT(AVAX)",
        None,
        "Historical $Price/AVAX",
        "Status",
        "ErrCode",
        "Type",
        "PrivateNote",
    ],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_snowtrace_internal,
)
