# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal

from ..dataparser import DataParser
from ..out_record import TransactionOutRecord

WALLET = "Blockchain.com"


def parse_blockchain(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["date"] + " " + row_dict["time"])

    symbol, value = row_dict["value_then"][0], row_dict["value_then"].strip("£€$ ").replace(",", "")
    if symbol == "£":
        value = abs(DataParser.convert_currency(value, "GBP", data_row.timestamp))
    elif symbol == "€":
        value = abs(DataParser.convert_currency(value, "EUR", data_row.timestamp))
    elif symbol == "$":
        value = abs(DataParser.convert_currency(value, "USD", data_row.timestamp))
    else:
        value = None

    if Decimal(row_dict["amount"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["amount"],
            buy_asset=row_dict["token"],
            buy_value=value,
            wallet=WALLET,
            note=row_dict["note"],
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["amount"])),
            sell_asset=row_dict["token"],
            sell_value=value,
            wallet=WALLET,
            note=row_dict["note"],
        )


def parse_blockchain_btc(data_row, parser, **kwargs):
    data_row.row_dict["token"] = "BTC"
    data_row.row_dict["amount"] = data_row.row_dict["amount_btc"]
    parse_blockchain(data_row, parser, **kwargs)


DataParser(
    DataParser.TYPE_WALLET,
    "Blockchain.com",
    [
        "date",
        "time",
        "token",
        "type",
        "amount",
        "value_then",
        "value_now",
        "exchange_rate_then",
        "tx",
        "note",
    ],
    worksheet_name="Blockchain.com",
    row_handler=parse_blockchain,
)

DataParser(
    DataParser.TYPE_WALLET,
    "Blockchain.com",
    [
        "date",
        "time",
        "type",
        "amount_btc",
        "value_then",
        "value_now",
        "exchange_rate_then",
        "tx",
        "note",
    ],
    worksheet_name="Blockchain.com",
    row_handler=parse_blockchain_btc,
)
