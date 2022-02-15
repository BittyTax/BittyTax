# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal

from .etherscan import get_note
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Avalanche chain"

def parse_snowtrace(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    if row_dict['Status'] != '':
        # Failed txns should not have a Value_OUT
        row_dict['Value_OUT(AVAX)'] = 0

    if Decimal(row_dict['Value_IN(AVAX)']) > 0:
        if row_dict['Status'] == '':
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Value_IN(AVAX)'],
                                                     buy_asset="AVAX",
                                                     wallet=WALLET,
                                                     note=get_note(row_dict))
    elif Decimal(row_dict['Value_OUT(AVAX)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(AVAX)'],
                                                 sell_asset="AVAX",
                                                 fee_quantity=row_dict['TxnFee(AVAX)'],
                                                 fee_asset="AVAX",
                                                 wallet=WALLET,
                                                 note=get_note(row_dict))
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(AVAX)'],
                                                 sell_asset="AVAX",
                                                 fee_quantity=row_dict['TxnFee(AVAX)'],
                                                 fee_asset="AVAX",
                                                 wallet=WALLET,
                                                 note=get_note(row_dict))

def parse_snowtrace_internal(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    if Decimal(row_dict['Value_IN(AVAX)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Value_IN(AVAX)'],
                                                 buy_asset="AVAX",
                                                 wallet=WALLET)
    elif Decimal(row_dict['Value_OUT(AVAX)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(AVAX)'],
                                                 sell_asset="AVAX",
                                                 wallet=WALLET)

avax_txns = DataParser(
        DataParser.TYPE_EXPLORER,
        "SnowTrace (AVAX Transactions)",
        ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
         'Value_IN(AVAX)', 'Value_OUT(AVAX)', None, 'TxnFee(AVAX)', 'TxnFee(USD)',
         'Historical $Price/AVAX', 'Status', 'ErrCode'],
        worksheet_name="SnowTrace",
        row_handler=parse_snowtrace)

DataParser(DataParser.TYPE_EXPLORER,
           "SnowTrace (AVAX Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(AVAX)', 'Value_OUT(AVAX)', None, 'TxnFee(AVAX)', 'TxnFee(USD)',
            'Historical $Price/AVAX', 'Status', 'ErrCode', 'PrivateNote'],
           worksheet_name="SnowTrace",
           row_handler=parse_snowtrace)

avax_int = DataParser(
        DataParser.TYPE_EXPLORER,
        "SnowTrace (AVAX Internal Transactions)",
        ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'ParentTxFrom', 'ParentTxTo',
         'ParentTxETH_Value', 'From', 'TxTo', 'ContractAddress', 'Value_IN(AVAX)',
         'Value_OUT(AVAX)', None, 'Historical $Price/AVAX', 'Status', 'ErrCode', 'Type'],
        worksheet_name="SnowTrace",
        row_handler=parse_snowtrace_internal)

DataParser(DataParser.TYPE_EXPLORER,
           "SnowTrace (AVAX Internal Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'ParentTxFrom', 'ParentTxTo',
            'ParentTxETH_Value', 'From', 'TxTo', 'ContractAddress', 'Value_IN(AVAX)',
            'Value_OUT(AVAX)', None, 'Historical $Price/AVAX', 'Status', 'ErrCode', 'Type',
            'PrivateNote'],
           worksheet_name="SnowTrace",
           row_handler=parse_snowtrace_internal)

# Same header as Etherscan
#DataParser(DataParser.TYPE_EXPLORER,
#           "BscScan (ERC-20 Tokens)",
#           ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'Value', 'ContractAddress',
#            'TokenName', 'TokenSymbol'],
#           worksheet_name="SnowTrace",
#           row_handler=parse_snowtrace_tokens)

# Same header as Etherscan
#DataParser(DataParser.TYPE_EXPLORER,
#           "Etherscan (ERC-721 NFTs)",
#           ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress', 'TokenId',
#            'TokenName', 'TokenSymbol'],
#           worksheet_name="SnowTrace",
#           row_handler=parse_snowtrace_nfts)
