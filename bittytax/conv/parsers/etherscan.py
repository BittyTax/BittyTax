# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Ethereum"

def parse_etherscan(data_row, _):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(int(in_row[2]))

    if Decimal(in_row[7]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[7],
                                                 buy_asset="ETH",
                                                 wallet=WALLET)
    elif Decimal(in_row[8]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[8],
                                                 sell_asset="ETH",
                                                 fee_quantity=in_row[10],
                                                 fee_asset="ETH",
                                                 wallet=WALLET)
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
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
           worksheet_name="Etherscan",
           row_handler=parse_etherscan)

DataParser(DataParser.TYPE_EXPLORER,
           "Etherscan (Ethereum)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(ETH)', 'Value_OUT(ETH)', None, 'TxnFee(ETH)', 'TxnFee(USD)',
            'Historical $Price/Eth', 'Status', 'ErrCode', 'PrivateNote'],
           worksheet_name="Etherscan",
           row_handler=parse_etherscan)
