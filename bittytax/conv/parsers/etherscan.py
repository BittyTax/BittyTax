# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataFilenameError

WALLET = "Ethereum"

def parse_etherscan(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    if row_dict['Status'] != '':
        # Failed txns should not have a Value_OUT
        row_dict['Value_OUT(ETH)'] = 0

    if Decimal(row_dict['Value_IN(ETH)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Value_IN(ETH)'],
                                                 buy_asset="ETH",
                                                 wallet=WALLET,
                                                 note=get_note(row_dict))
    elif Decimal(row_dict['Value_OUT(ETH)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(ETH)'],
                                                 sell_asset="ETH",
                                                 fee_quantity=row_dict['TxnFee(ETH)'],
                                                 fee_asset="ETH",
                                                 wallet=WALLET,
                                                 note=get_note(row_dict))
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(ETH)'],
                                                 sell_asset="ETH",
                                                 fee_quantity=row_dict['TxnFee(ETH)'],
                                                 fee_asset="ETH",
                                                 wallet=WALLET,
                                                 note=get_note(row_dict))

def get_note(row_dict):
    if row_dict['Status'] != '':
        if row_dict.get('Method'):
            return "Failure (%s)" % row_dict['Method']
        return "Failure"

    if row_dict.get('Method'):
        return row_dict['Method']

    return row_dict.get('PrivateNote', '')

def parse_etherscan_internal(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    if Decimal(row_dict['Value_IN(ETH)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Value_IN(ETH)'],
                                                 buy_asset="ETH",
                                                 wallet=WALLET)
    elif Decimal(row_dict['Value_OUT(ETH)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(ETH)'],
                                                 sell_asset="ETH",
                                                 wallet=WALLET)

def parse_etherscan_tokens(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    if row_dict['TokenSymbol'].endswith('-LP'):
        asset = row_dict['TokenSymbol'] + '-' + row_dict['ContractAddress'][0:10]
    else:
        asset = row_dict['TokenSymbol']

    if row_dict['To'].lower() in kwargs['filename'].lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Value'].replace(',', ''),
                                                 buy_asset=asset,
                                                 wallet=WALLET)
    elif row_dict['From'].lower() in kwargs['filename'].lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value'].replace(',', ''),
                                                 sell_asset=asset,
                                                 wallet=WALLET)
    else:
        raise DataFilenameError(kwargs['filename'], "Ethereum address")

def parse_etherscan_nfts(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    if row_dict['To'].lower() in kwargs['filename'].lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=1,
                                                 buy_asset=row_dict['TokenSymbol'],
                                                 wallet=WALLET)
    elif row_dict['From'].lower() in kwargs['filename'].lower():
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=1,
                                                 sell_asset=row_dict['TokenSymbol'],
                                                 wallet=WALLET)
    else:
        raise DataFilenameError(kwargs['filename'], "Ethereum address")

etherscan_txns = DataParser(
        DataParser.TYPE_EXPLORER,
        "Etherscan (ETH Transactions)",
        ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
         'Value_IN(ETH)', 'Value_OUT(ETH)', None, 'TxnFee(ETH)', 'TxnFee(USD)',
         'Historical $Price/Eth', 'Status', 'ErrCode'],
        worksheet_name="Etherscan",
        row_handler=parse_etherscan)

DataParser(
        DataParser.TYPE_EXPLORER,
        "Etherscan (ETH Transactions)",
        ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
         'Value_IN(ETH)', 'Value_OUT(ETH)', None, 'TxnFee(ETH)', 'TxnFee(USD)',
         'Historical $Price/Eth', 'Status', 'ErrCode', 'PrivateNote'],
        worksheet_name="Etherscan",
        row_handler=parse_etherscan)

DataParser(DataParser.TYPE_EXPLORER,
           "Etherscan (ETH Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(ETH)', 'Value_OUT(ETH)', None, 'TxnFee(ETH)', 'TxnFee(USD)',
            'Historical $Price/Eth', 'Status', 'ErrCode', 'Method'],
           worksheet_name="Etherscan",
           row_handler=parse_etherscan)

DataParser(DataParser.TYPE_EXPLORER,
           "Etherscan (ETH Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(ETH)', 'Value_OUT(ETH)', None, 'TxnFee(ETH)', 'TxnFee(USD)',
            'Historical $Price/Eth', 'Status', 'ErrCode', 'Method', 'PrivateNote'],
           worksheet_name="Etherscan",
           row_handler=parse_etherscan)

etherscan_int = DataParser(
        DataParser.TYPE_EXPLORER,
        "Etherscan (ETH Internal Transactions)",
        ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'ParentTxFrom', 'ParentTxTo',
         'ParentTxETH_Value', 'From', 'TxTo', 'ContractAddress', 'Value_IN(ETH)',
         'Value_OUT(ETH)', None, 'Historical $Price/Eth', 'Status', 'ErrCode', 'Type'],
        worksheet_name="Etherscan",
        row_handler=parse_etherscan_internal)

DataParser(DataParser.TYPE_EXPLORER,
           "Etherscan (ETH Internal Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'ParentTxFrom', 'ParentTxTo',
            'ParentTxETH_Value', 'From', 'TxTo', 'ContractAddress', 'Value_IN(ETH)',
            'Value_OUT(ETH)', None, 'Historical $Price/Eth', 'Status', 'ErrCode', 'Type',
            'PrivateNote'],
           worksheet_name="Etherscan",
           row_handler=parse_etherscan_internal)

etherscan_tokens = DataParser(
        DataParser.TYPE_EXPLORER,
        "Etherscan (ERC-20 Tokens)",
        ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'Value', 'ContractAddress',
         'TokenName', 'TokenSymbol'],
        worksheet_name="Etherscan",
        row_handler=parse_etherscan_tokens)

etherscan_nfts = DataParser(
        DataParser.TYPE_EXPLORER,
        "Etherscan (ERC-721 NFTs)",
        ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress', 'TokenId',
         'TokenName', 'TokenSymbol'],
        worksheet_name="Etherscan",
        row_handler=parse_etherscan_nfts)
