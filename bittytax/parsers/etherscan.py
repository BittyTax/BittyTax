# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019
# $Id: etherscan.py,v 1.6 2019/05/16 20:26:52 scottgreen Exp $

from decimal import Decimal

from ..record import TransactionRecord
from ..parser import DataParser

WALLET = "Ethereum"

def parse_etherscan(in_row):
    if Decimal(in_row[7]) > 0:
        return TransactionRecord(TransactionRecord.TYPE_DEPOSIT,
                                 DataParser.parse_timestamp(int(in_row[2])),
                                 buy_quantity=in_row[7],
                                 buy_asset="ETH",
                                 wallet=WALLET)
    elif Decimal(in_row[8]) > 0:
        return TransactionRecord(TransactionRecord.TYPE_WITHDRAWAL,
                                 DataParser.parse_timestamp(int(in_row[2])),
                                 sell_quantity=in_row[8],
                                 sell_asset="ETH",
                                 fee_quantity=in_row[10],
                                 fee_asset="ETH",
                                 wallet=WALLET)
    else:
        return TransactionRecord(TransactionRecord.TYPE_SPEND,
                                 DataParser.parse_timestamp(int(in_row[2])),
                                 sell_quantity=in_row[8],
                                 sell_asset="ETH",
                                 fee_quantity=in_row[10],
                                 fee_asset="ETH",
                                 wallet=WALLET)

DataParser(DataParser.TYPE_EXPLORER,
           "Etherscan (Ethereum)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(ETH)', 'Value_OUT(ETH)', None, 'TxnFee(ETH)', 'TxnFee(USD)',
            'Historical $Price/Eth', 'Status', 'ErrCode'],
           row_handler=parse_etherscan)
