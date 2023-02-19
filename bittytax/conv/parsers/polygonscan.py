# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal

from .etherscan import get_note
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Polygon chain"
WORKSHEET_NAME = "PolygonScan"

def parse_polygonscan(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    if row_dict['Status'] != '':
        # Failed transactions should not have a Value_OUT
        row_dict['Value_OUT(MATIC)'] = 0

    if Decimal(row_dict['Value_IN(MATIC)']) > 0:
        if row_dict['Status'] == '':
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Value_IN(MATIC)'],
                                                     buy_asset="MATIC",
                                                     wallet=get_wallet(row_dict['To']),
                                                     note=get_note(row_dict))
    elif Decimal(row_dict['Value_OUT(MATIC)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(MATIC)'],
                                                 sell_asset="MATIC",
                                                 fee_quantity=row_dict['TxnFee(MATIC)'],
                                                 fee_asset="MATIC",
                                                 wallet=get_wallet(row_dict['From']),
                                                 note=get_note(row_dict))
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(MATIC)'],
                                                 sell_asset="MATIC",
                                                 fee_quantity=row_dict['TxnFee(MATIC)'],
                                                 fee_asset="MATIC",
                                                 wallet=get_wallet(row_dict['From']),
                                                 note=get_note(row_dict))

def get_wallet(address):
    return "%s-%s" % (WALLET, address.lower()[0:TransactionOutRecord.WALLET_ADDR_LEN])

def parse_polygonscan_internal(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    # Failed internal transaction
    if row_dict['Status'] != '0':
        return

    if Decimal(row_dict['Value_IN(MATIC)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Value_IN(MATIC)'],
                                                 buy_asset="MATIC",
                                                 wallet=get_wallet(row_dict['TxTo']))
    elif Decimal(row_dict['Value_OUT(MATIC)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(MATIC)'],
                                                 sell_asset="MATIC",
                                                 wallet=get_wallet(row_dict['From']))

MATIC_TXNS = DataParser(
    DataParser.TYPE_EXPLORER,
    "PolygonScan (MATIC Transactions)",
    ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
     'Value_IN(MATIC)', 'Value_OUT(MATIC)', None, 'TxnFee(MATIC)', 'TxnFee(USD)',
     'Historical $Price/MATIC', 'Status', 'ErrCode', 'Method'],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_polygonscan)

DataParser(DataParser.TYPE_EXPLORER,
           "PolygonScan (MATIC Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(MATIC)', 'Value_OUT(MATIC)', None, 'TxnFee(MATIC)', 'TxnFee(USD)',
            'Historical $Price/MATIC', 'Status', 'ErrCode', 'Method', 'PrivateNote'],
           worksheet_name=WORKSHEET_NAME,
           row_handler=parse_polygonscan)

MATIC_INT = DataParser(
    DataParser.TYPE_EXPLORER,
    "PolygonScan (MATIC Internal Transactions)",
    ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'ParentTxFrom', 'ParentTxTo',
     'ParentTxETH_Value', 'From', 'TxTo', 'ContractAddress', 'Value_IN(MATIC)',
     'Value_OUT(MATIC)', None, 'Historical $Price/MATIC', 'Status', 'ErrCode', 'Type'],
    worksheet_name=WORKSHEET_NAME,
    row_handler=parse_polygonscan_internal)

DataParser(DataParser.TYPE_EXPLORER,
           "PolygonScan (MATIC Internal Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'ParentTxFrom', 'ParentTxTo',
            'ParentTxETH_Value', 'From', 'TxTo', 'ContractAddress', 'Value_IN(MATIC)',
            'Value_OUT(MATIC)', None, 'Historical $Price/MATIC', 'Status', 'ErrCode', 'Type',
            'PrivateNote'],
           worksheet_name=WORKSHEET_NAME,
           row_handler=parse_polygonscan_internal)

# Same header as Etherscan
# DataParser(DataParser.TYPE_EXPLORER,
#            "PolygonScan (ERC-20 Tokens)",
#            ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'Value', 'ContractAddress',
#             'TokenName', 'TokenSymbol'],
#            worksheet_name=WORKSHEET_NAME,
#            row_handler=parse_polygonscan_tokens)

# Same header as Etherscan
# DataParser(DataParser.TYPE_EXPLORER,
#            "PolygonScan (ERC-721 NFTs)",
#            ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress', 'TokenId',
#             'TokenName', 'TokenSymbol'],
#            worksheet_name=WORKSHEET_NAME,
#            row_handler=parse_polygonscan_nfts)
