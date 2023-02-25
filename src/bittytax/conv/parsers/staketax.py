# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

import json
from decimal import Decimal

from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord
from ..output_csv import OutputBase

STAKETAX_MAPPING = {
    "STAKING": TransactionOutRecord.TYPE_STAKING,
    "AIRDROP": TransactionOutRecord.TYPE_AIRDROP,
    "TRADE": TransactionOutRecord.TYPE_TRADE,
    "TRANSFER": "_TRANSFER",
    "SPEND": TransactionOutRecord.TYPE_SPEND,
    "INCOME": TransactionOutRecord.TYPE_INCOME,
    "BORROW": "_BORROW",
    "REPAY": "_REPAY",
    "LP_DEPOSIT": TransactionOutRecord.TYPE_TRADE,
    "LP_WITHDRAW": TransactionOutRecord.TYPE_TRADE,
    "MARGIN_TRADE_FEE": "_MARGIN_TRADE_FEE",
}


def parse_staketax_default(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    if row_dict["timestamp"]:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["timestamp"])

    t_type = STAKETAX_MAPPING.get(row_dict["tx_type"], row_dict["tx_type"])

    if row_dict["received_amount"]:
        buy_quantity = row_dict["received_amount"]
    else:
        buy_quantity = None

    if row_dict["sent_amount"]:
        sell_quantity = row_dict["sent_amount"]
    else:
        sell_quantity = None

    if row_dict["fee"]:
        fee_quantity = row_dict["fee"]
    else:
        fee_quantity = None

    if row_dict["tx_type"] == "TRANSFER":
        if buy_quantity and not sell_quantity:
            t_type = TransactionOutRecord.TYPE_DEPOSIT
        elif sell_quantity and not buy_quantity:
            t_type = TransactionOutRecord.TYPE_WITHDRAWAL
        else:
            raise UnexpectedTypeError(
                parser.in_header.index("tx_type"), "tx_type", row_dict["tx_type"]
            )

    # Add a dummy sell_quantity if fee is on it's own
    if fee_quantity and (not buy_quantity and not sell_quantity):
        sell_quantity = Decimal(0)
        sell_asset = row_dict["fee_currency"]
    else:
        sell_asset = row_dict["sent_currency"]

    data_row.t_record = TransactionOutRecord(
        t_type,
        data_row.timestamp,
        buy_quantity=buy_quantity,
        buy_asset=row_dict["received_currency"],
        sell_quantity=sell_quantity,
        sell_asset=sell_asset,
        fee_quantity=fee_quantity,
        fee_asset=row_dict["fee_currency"],
        wallet=_get_wallet(row_dict["exchange"], row_dict["wallet_address"]),
        note=row_dict["comment"],
    )

    parser.worksheet_name = (
        "StakeTax " + row_dict["exchange"].replace("_blockchain", "").capitalize()
    )


def _get_wallet(exchange, wallet_address):
    return "%s-%s" % (
        exchange.replace("_blockchain", "").capitalize(),
        wallet_address[0:16],
    )


def parse_staketax_bittytax(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    if row_dict["Timestamp"]:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["Timestamp"])

    if row_dict["Buy Quantity"]:
        buy_quantity = row_dict["Buy Quantity"]
    else:
        buy_quantity = None

    if row_dict["Sell Quantity"]:
        sell_quantity = row_dict["Sell Quantity"]
    else:
        sell_quantity = None

    if row_dict["Fee Quantity"]:
        fee_quantity = row_dict["Fee Quantity"]
    else:
        fee_quantity = None

    data_row.t_record = TransactionOutRecord(
        row_dict["Type"],
        data_row.timestamp,
        buy_quantity=buy_quantity,
        buy_asset=row_dict["Buy Asset"],
        sell_quantity=sell_quantity,
        sell_asset=row_dict["Sell Asset"],
        fee_quantity=fee_quantity,
        fee_asset=row_dict["Fee Asset"],
        wallet=row_dict["Wallet"],
        note=row_dict["Note"],
    )

    # Remove TR headers and data
    if len(parser.in_header) > len(OutputBase.BITTYTAX_OUT_HEADER):
        del parser.in_header[0 : len(OutputBase.BITTYTAX_OUT_HEADER)]
    del data_row.row[0 : len(OutputBase.BITTYTAX_OUT_HEADER)]

    raw = json.loads(row_dict["Raw Data"])
    parser.worksheet_name = "StakeTax " + raw["exchange"].replace("_blockchain", "").capitalize()


DataParser(
    DataParser.TYPE_ACCOUNTING,
    "StakeTax",
    [
        "timestamp",
        "tx_type",
        "received_amount",
        "received_currency",
        "sent_amount",
        "sent_currency",
        "fee",
        "fee_currency",
        "comment",
        "txid",
        "url",
        "exchange",
        "wallet_address",
    ],
    worksheet_name="StakeTax",
    row_handler=parse_staketax_default,
)

DataParser(
    DataParser.TYPE_GENERIC,
    "StakeTax",
    [
        "Type",
        "Buy Quantity",
        "Buy Asset",
        "Buy Value",
        "Sell Quantity",
        "Sell Asset",
        "Sell Value",
        "Fee Quantity",
        "Fee Asset",
        "Fee Value",
        "Wallet",
        "Timestamp",
        "Note",
        "Tx ID",
        "URL",
        "Raw Data",
    ],
    worksheet_name="StakeTax",
    row_handler=parse_staketax_bittytax,
)
