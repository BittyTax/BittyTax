# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Huobi Eco Chain"

def parse_hecoinfo(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    if Decimal(row_dict['Value_IN(HT)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Value_IN(HT)'],
                                                 buy_asset="HT",
                                                 wallet=WALLET,
                                                 note=row_dict.get('PrivateNote', ''))
    elif Decimal(row_dict['Value_OUT(HT)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(HT)'],
                                                 sell_asset="HT",
                                                 fee_quantity=row_dict['TxnFee(HT)'],
                                                 fee_asset="HT",
                                                 wallet=WALLET,
                                                 note=row_dict.get('PrivateNote', ''))
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(HT)'],
                                                 sell_asset="HT",
                                                 fee_quantity=row_dict['TxnFee(HT)'],
                                                 fee_asset="HT",
                                                 wallet=WALLET,
                                                 note=row_dict.get('PrivateNote', ''))

def parse_hecoinfo_internal(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict['UnixTimestamp']))

    if Decimal(row_dict['Value_IN(HT)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Value_IN(HT)'],
                                                 buy_asset="HT",
                                                 wallet=WALLET)
    elif Decimal(row_dict['Value_OUT(HT)']) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['Value_OUT(HT)'],
                                                 sell_asset="HT",
                                                 wallet=WALLET)

heco1 = DataParser(DataParser.TYPE_EXPLORER,
           "HecoInfo (HECO Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(HT)', 'Value_OUT(HT)', None, 'TxnFee(HT)', 'TxnFee(USD)',
            'Historical $Price/HT', 'Status', 'ErrCode'],
           worksheet_name="HecoInfo",
           row_handler=parse_hecoinfo)

heco2 = DataParser(DataParser.TYPE_EXPLORER,
           "HecoInfo (HECO Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(HT)', 'Value_OUT(HT)', None, 'TxnFee(HT)', 'TxnFee(USD)',
            'Historical $Price/HT', 'Status', 'ErrCode', 'PrivateNote'],
           worksheet_name="HecoInfo",
           row_handler=parse_hecoinfo)

heco_internal = DataParser(DataParser.TYPE_EXPLORER,
           "HecoInfo (HECO Internal Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'ParentTxFrom', 'ParentTxTo',
            'ParentTxETH_Value', 'From', 'TxTo', 'ContractAddress', 'Value_IN(HT)', 'Value_OUT(HT)',
            None, 'Historical $Price/HT', 'Status', 'ErrCode', 'Type'],
           worksheet_name="HecoInfo",
           row_handler=parse_hecoinfo_internal)

heco_internal = DataParser(DataParser.TYPE_EXPLORER,
           "HecoInfo (HECO Internal Transactions)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'ParentTxFrom', 'ParentTxTo',
            'ParentTxETH_Value', 'From', 'TxTo', 'ContractAddress', 'Value_IN(HT)', 'Value_OUT(HT)',
            None, 'Historical $Price/HT', 'Status', 'ErrCode', 'Type', 'PrivateNote'],
           worksheet_name="HecoInfo",
           row_handler=parse_hecoinfo_internal)

def find_same_tx(data_file, tx_hash):
    for data_row in data_file.data_rows:
        if data_row.t_record and data_row.row_dict['Txhash'] == tx_hash:
            fee_quantity = data_row.t_record.fee_quantity
            fee_asset = data_row.t_record.fee_asset
            data_row.t_record = None
            return fee_quantity, fee_asset

    return None, ''

# Same header as Etherscan
#DataParser(DataParser.TYPE_EXPLORER,
#           "HecoInfo (HRC-20 Tokens)",
#           ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'Value', 'ContractAddress',
#            'TokenName', 'TokenSymbol'],
#           worksheet_name="HecoInfo",
#           row_handler=parse_hecoinfo_tokens)

# Same header as Etherscan
#DataParser(DataParser.TYPE_EXPLORER,
#           "HecoInfo (HRC-721 NFTs)",
#           ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress', 'TokenId',
#            'TokenName', 'TokenSymbol'],
#           worksheet_name="HecoInfo",
#           row_handler=parse_hecoinfo_nfts)
