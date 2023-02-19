# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal

from .etherscan import get_note
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Binance Smart Chain"
WORKSHEET_NAME = "BscScan"

def parse_bscscan(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    if row_dict['Status'] != '':
        # Failed transactions should not have a Value_OUT
        row_dict['Value_OUT(BNB)'] = 0

    if Decimal(row_dict['Value_IN(BNB)']) > 0:
        if row_dict['Status'] == '':
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Value_IN(BNB)'],
                                                     buy_asset="BNB",
                                                     wallet=get_wallet(row_dict['To']),
                                                     note=get_note(row_dict))
    elif Decimal(row_dict['Value_OUT(BNB)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(BNB)'],
                                                 sell_asset="BNB",
                                                 fee_quantity=row_dict['TxnFee(BNB)'],
                                                 fee_asset="BNB",
                                                 wallet=get_wallet(row_dict['From']),
                                                 note=get_note(row_dict))
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(BNB)'],
                                                 sell_asset="BNB",
                                                 fee_quantity=row_dict['TxnFee(BNB)'],
                                                 fee_asset="BNB",
                                                 wallet=get_wallet(row_dict['From']),
                                                 note=get_note(row_dict))

def get_wallet(address):
    return "%s-%s" % (WALLET, address.lower()[0:TransactionOutRecord.WALLET_ADDR_LEN])

def parse_bscscan_internal(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    # Failed internal transaction
    if row_dict['Status'] != '0':
        return

    if Decimal(row_dict['Value_IN(BNB)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Value_IN(BNB)'],
                                                 buy_asset="BNB",
                                                 wallet=get_wallet(row_dict['TxTo']))
    elif Decimal(row_dict['Value_OUT(BNB)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(BNB)'],
                                                 sell_asset="BNB",
                                                 wallet=get_wallet(row_dict['From']))

BSC_TXNS = DataParser(
    DataParser.TYPE_EXPLORER,
    "BscScan (BSC Transactions)",
    ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
     'Value_IN(BNB)', 'Value_OUT(BNB)', None, 'TxnFee(BNB)', 'TxnFee(USD)',
     'Historical $Price/BNB', 'Status', 'ErrCode'],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_bscscan)

DataParser(DataParser.TYPE_EXPLORER,
           "BscScan (BSC Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(BNB)', 'Value_OUT(BNB)', None, 'TxnFee(BNB)', 'TxnFee(USD)',
            'Historical $Price/BNB', 'Status', 'ErrCode', 'PrivateNote'],
           worksheet_name=WORKSHEET_NAME,
           row_handler=parse_bscscan)

DataParser(DataParser.TYPE_EXPLORER,
           "BscScan (BSC Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(BNB)', 'Value_OUT(BNB)', None, 'TxnFee(BNB)', 'TxnFee(USD)',
            'Historical $Price/BNB', 'Status', 'ErrCode', 'Method'],
           worksheet_name=WORKSHEET_NAME,
           row_handler=parse_bscscan)

DataParser(DataParser.TYPE_EXPLORER,
           "BscScan (BSC Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(BNB)', 'Value_OUT(BNB)', None, 'TxnFee(BNB)', 'TxnFee(USD)',
            'Historical $Price/BNB', 'Status', 'ErrCode', 'Method', 'PrivateNote'],
           worksheet_name=WORKSHEET_NAME,
           row_handler=parse_bscscan)

BSC_INT = DataParser(
    DataParser.TYPE_EXPLORER,
    "BscScan (BSC Internal Transactions)",
    ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'ParentTxFrom', 'ParentTxTo',
     'ParentTxETH_Value', 'From', 'TxTo', 'ContractAddress', 'Value_IN(BNB)',
     'Value_OUT(BNB)', None, 'Historical $Price/BNB', 'Status', 'ErrCode', 'Type'],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_bscscan_internal)

DataParser(DataParser.TYPE_EXPLORER,
           "BscScan (BSC Internal Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'ParentTxFrom', 'ParentTxTo',
            'ParentTxETH_Value', 'From', 'TxTo', 'ContractAddress', 'Value_IN(BNB)',
            'Value_OUT(BNB)', None, 'Historical $Price/BNB', 'Status', 'ErrCode', 'Type',
            'PrivateNote'],
           worksheet_name=WORKSHEET_NAME,
           row_handler=parse_bscscan_internal)

# Same header as Etherscan
# DataParser(DataParser.TYPE_EXPLORER,
#            "BscScan (BEP-20 Tokens)",
#            ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'Value', 'ContractAddress',
#             'TokenName', 'TokenSymbol'],
#            worksheet_name=WORKSHEET_NAME,
#            row_handler=parse_bscscan_tokens)

# Same header as Etherscan
# DataParser(DataParser.TYPE_EXPLORER,
#            "Etherscan (BEP-721 NFTs)",
#            ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress', 'TokenId',
#             'TokenName', 'TokenSymbol'],
#            worksheet_name=WORKSHEET_NAME,
#            row_handler=parse_bscscan_nfts)
