# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataFilenameError

WALLET = "Ethereum"

def parse_etherscan(data_row, _parser, _filename):
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

def parse_etherscan_internal(data_row, _parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(int(in_row[2]))

    if Decimal(in_row[10]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[10],
                                                 buy_asset="ETH",
                                                 wallet=WALLET)
    elif Decimal(in_row[11]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[11],
                                                 sell_asset="ETH",
                                                 wallet=WALLET)

def parse_etherscan_tokens(data_row, _parser, filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(int(in_row[1]))

    if in_row[4].lower() in filename.lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5].replace(',', ''),
                                                 buy_asset=in_row[8],
                                                 wallet=WALLET)
    elif in_row[3].lower() in filename.lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[5].replace(',', ''),
                                                 sell_asset=in_row[8],
                                                 wallet=WALLET)
    else:
        raise DataFilenameError(filename, "Ethereum address")

def parse_etherscan_nfts(data_row, _parser, filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(int(in_row[1]))

    if in_row[4].lower() in filename.lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=1,
                                                 buy_asset=in_row[8],
                                                 wallet=WALLET)
    elif in_row[3].lower() in filename.lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=1,
                                                 sell_asset=in_row[8],
                                                 wallet=WALLET)
    else:
        raise DataFilenameError(filename, "Ethereum address")

DataParser(DataParser.TYPE_EXPLORER,
           "Etherscan (Ethereum Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(ETH)', 'Value_OUT(ETH)', None, 'TxnFee(ETH)', 'TxnFee(USD)',
            'Historical $Price/Eth', 'Status', 'ErrCode'],
           worksheet_name="Etherscan",
           row_handler=parse_etherscan)

DataParser(DataParser.TYPE_EXPLORER,
           "Etherscan (Ethereum Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(ETH)', 'Value_OUT(ETH)', None, 'TxnFee(ETH)', 'TxnFee(USD)',
            'Historical $Price/Eth', 'Status', 'ErrCode', 'PrivateNote'],
           worksheet_name="Etherscan",
           row_handler=parse_etherscan)

DataParser(DataParser.TYPE_EXPLORER,
           "Etherscan (Internal Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'ParentTxFrom', 'ParentTxTo',
            'ParentTxETH_Value', 'From', 'TxTo', 'ContractAddress', 'Value_IN(ETH)',
            'Value_OUT(ETH)', None, 'Historical $Price/Eth', 'Status', 'ErrCode', 'Type'],
           worksheet_name="Etherscan",
           row_handler=parse_etherscan_internal)

DataParser(DataParser.TYPE_EXPLORER,
           "Etherscan (ERC-20 Tokens)",
           ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'Value', 'ContractAddress',
            'TokenName', 'TokenSymbol'],
           worksheet_name="Etherscan",
           row_handler=parse_etherscan_tokens)

DataParser(DataParser.TYPE_EXPLORER,
           "Etherscan (ERC-721 NFTs)",
           ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress', 'TokenId',
            'TokenName', 'TokenSymbol'],
           worksheet_name="Etherscan",
           row_handler=parse_etherscan_nfts)
