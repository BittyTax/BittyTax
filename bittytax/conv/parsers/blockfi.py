# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import sys
from decimal import Decimal

from colorama import Fore, Back

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "BlockFi"


def parse_blockfi_wallet(data_row, parser, _filename):
    in_row = data_row.in_row

    if in_row[3] == "" and not config.args.unconfirmed:
        sys.stderr.write("%srow[%s] %s\n" % (
            Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
        sys.stderr.write("%sWARNING%s Skipping unconfirmed transaction, "
                         "use the [-uc] option to include it\n" % (
                             Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW))
        return

    data_row.timestamp = DataParser.parse_timestamp(in_row[3])

    symbol = in_row[0]
    quantity = Decimal(in_row[1])
    transaction_type = in_row[2]

    if "Deposit" in transaction_type:
        # "Deposit" for crypto deposits
        # "Wire Deposit" for wire transfers
        # "ACH Deposit" for ACH transfers
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=quantity,
                                                 buy_asset=symbol,
                                                 wallet=WALLET)

    elif transaction_type == "Interest Payment":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                 data_row.timestamp,
                                                 buy_quantity=quantity,
                                                 buy_asset=symbol,
                                                 wallet=WALLET)

    elif transaction_type == "Bonus Payment":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=quantity,
                                                 buy_asset=symbol,
                                                 wallet=WALLET)

    elif transaction_type == "Withdrawal Fee":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(quantity),
                                                 sell_asset=symbol,
                                                 wallet=WALLET)

    elif "Withdrawal" in transaction_type:
        # "Withdrawal" for crypto withdrawals
        # "Wire Withdrawal" for wire transfers
        # "ACH Withdrawal" for ACH transfers
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(quantity),
                                                 sell_asset=symbol,
                                                 wallet=WALLET)

    elif transaction_type == "Trade":
        # BlockFi reports trades with more detail in a separate export
        sys.stderr.write("%srow[%s] %s\n" % (
            Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
        sys.stderr.write("%sWARNING%s Skipping trade transaction, "
                         "make sure you also import your BlockFi trading report\n" % (
                             Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW))

    else:
        raise UnexpectedTypeError(2, parser.in_header[2], transaction_type)


def parse_blockfi_trades(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[1])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                             data_row.timestamp,
                                             buy_quantity=Decimal(in_row[2]),
                                             buy_asset=in_row[3],
                                             sell_quantity=abs(
                                                 Decimal(in_row[4])),
                                             sell_asset=in_row[5],
                                             wallet=WALLET)


DataParser(DataParser.TYPE_WALLET,
           "BlockFi",
           ['Cryptocurrency', 'Amount', 'Transaction Type', 'Confirmed At'],
           worksheet_name="BlockFi",
           row_handler=parse_blockfi_wallet)

DataParser(DataParser.TYPE_EXCHANGE,
           "BlockFi Trades",
           ['Trade ID', 'Date', 'Buy Quantity', 'Buy Currency', 'Sold Quantity',
            'Sold Currency', 'Rate Amount', 'Rate Currency', 'Type'],
           worksheet_name="BlockFi T",
           row_handler=parse_blockfi_trades)
