# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal

from .etherscan import get_note
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Huobi Eco Chain"
WORKSHEET_NAME = "HecoInfo"

def parse_hecoinfo(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    if row_dict['Status'] != '':
        # Failed txns should not have a Value_OUT
        row_dict['Value_OUT(HT)'] = 0

    if Decimal(row_dict['Value_IN(HT)']) > 0:
        if row_dict['Status'] == '':
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Value_IN(HT)'],
                                                     buy_asset="HT",
                                                     wallet=get_wallet(row_dict['To']),
                                                     note=get_note(row_dict))

    elif Decimal(row_dict['Value_OUT(HT)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(HT)'],
                                                 sell_asset="HT",
                                                 fee_quantity=row_dict['TxnFee(HT)'],
                                                 fee_asset="HT",
                                                 wallet=get_wallet(row_dict['From']),
                                                 note=get_note(row_dict))
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(HT)'],
                                                 sell_asset="HT",
                                                 fee_quantity=row_dict['TxnFee(HT)'],
                                                 fee_asset="HT",
                                                 wallet=get_wallet(row_dict['From']),
                                                 note=get_note(row_dict))

def get_wallet(address):
    return "%s-%s" % (WALLET, address.lower()[0:TransactionOutRecord.WALLET_ADDR_LEN])

def parse_hecoinfo_internal(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    # Failed internal txn
    if row_dict['Status'] != '0':
        return

    if Decimal(row_dict['Value_IN(HT)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Value_IN(HT)'],
                                                 buy_asset="HT",
                                                 wallet=get_wallet(row_dict['TxTo']))
    elif Decimal(row_dict['Value_OUT(HT)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(HT)'],
                                                 sell_asset="HT",
                                                 wallet=get_wallet(row_dict['From']))

heco_txns = DataParser(
        DataParser.TYPE_EXPLORER,
        "HecoInfo (HECO Transactions)",
        ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
         'Value_IN(HT)', 'Value_OUT(HT)', None, 'TxnFee(HT)', 'TxnFee(USD)',
         'Historical $Price/HT', 'Status', 'ErrCode'],
        worksheet_name=WORKSHEET_NAME,
        row_handler=parse_hecoinfo)

DataParser(DataParser.TYPE_EXPLORER,
           "HecoInfo (HECO Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(HT)', 'Value_OUT(HT)', None, 'TxnFee(HT)', 'TxnFee(USD)',
            'Historical $Price/HT', 'Status', 'ErrCode', 'PrivateNote'],
           worksheet_name=WORKSHEET_NAME,
           row_handler=parse_hecoinfo)

DataParser(DataParser.TYPE_EXPLORER,
           "HecoInfo (HECO Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(HT)', 'Value_OUT(HT)', None, 'TxnFee(HT)', 'TxnFee(USD)',
            'Historical $Price/HT', 'Status', 'ErrCode', 'Method'],
           worksheet_name=WORKSHEET_NAME,
           row_handler=parse_hecoinfo)

DataParser(DataParser.TYPE_EXPLORER,
           "HecoInfo (HECO Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(HT)', 'Value_OUT(HT)', None, 'TxnFee(HT)', 'TxnFee(USD)',
            'Historical $Price/HT', 'Status', 'ErrCode', 'Method', 'PrivateNote'],
           worksheet_name=WORKSHEET_NAME,
           row_handler=parse_hecoinfo)

heco_int = DataParser(
        DataParser.TYPE_EXPLORER,
        "HecoInfo (HECO Internal Transactions)",
        ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'ParentTxFrom', 'ParentTxTo',
         'ParentTxETH_Value', 'From', 'TxTo', 'ContractAddress', 'Value_IN(HT)', 'Value_OUT(HT)',
         None, 'Historical $Price/HT', 'Status', 'ErrCode', 'Type'],
        worksheet_name=WORKSHEET_NAME,
        row_handler=parse_hecoinfo_internal)

DataParser(DataParser.TYPE_EXPLORER,
           "HecoInfo (HECO Internal Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'ParentTxFrom', 'ParentTxTo',
            'ParentTxETH_Value', 'From', 'TxTo', 'ContractAddress', 'Value_IN(HT)', 'Value_OUT(HT)',
            None, 'Historical $Price/HT', 'Status', 'ErrCode', 'Type', 'PrivateNote'],
           worksheet_name=WORKSHEET_NAME,
           row_handler=parse_hecoinfo_internal)

# Same header as Etherscan
#DataParser(DataParser.TYPE_EXPLORER,
#           "HecoInfo (HRC-20 Tokens)",
#           ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'Value', 'ContractAddress',
#            'TokenName', 'TokenSymbol'],
#           worksheet_name=WORKSHEET_NAME,
#           row_handler=parse_hecoinfo_tokens)

# Same header as Etherscan
#DataParser(DataParser.TYPE_EXPLORER,
#           "HecoInfo (HRC-721 NFTs)",
#           ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress', 'TokenId',
#            'TokenName', 'TokenSymbol'],
#           worksheet_name=WORKSHEET_NAME,
#           row_handler=parse_hecoinfo_nfts)
