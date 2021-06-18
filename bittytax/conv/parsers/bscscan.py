# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownAddressError

WALLET = "BinanceSmartChain"

def parse_bscscan(data_row, _parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(int(in_row[2]))

    if Decimal(in_row[7]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[7],
                                                 buy_asset="BNB",
                                                 wallet=WALLET)
    elif Decimal(in_row[8]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[8],
                                                 sell_asset="BNB",
                                                 fee_quantity=in_row[10],
                                                 fee_asset="BNB",
                                                 wallet=WALLET)
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[8],
                                                 sell_asset="BNB",
                                                 fee_quantity=in_row[10],
                                                 fee_asset="BNB",
                                                 wallet=WALLET)

def parse_bscscan_tokens(data_row, _parser, filename):
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
        raise UnknownAddressError

def parse_bscscan_nfts(data_row, _parser, filename):
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
        raise UnknownAddressError

DataParser(DataParser.TYPE_EXPLORER,
           "Bscscan (BNB)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(BNB)', 'Value_OUT(BNB)', None, 'TxnFee(BNB)', 'TxnFee(USD)',
            'Historical $Price/BNB', 'Status', 'ErrCode'],
           worksheet_name="Bscscan",
           row_handler=parse_bscscan)

DataParser(DataParser.TYPE_EXPLORER,
           "Bscscan (BNB)",
           ['Txhash', 'Blockno', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress',
            'Value_IN(BNB)', 'Value_OUT(ETH)', None, 'TxnFee(BNB)', 'TxnFee(USD)',
            'Historical $Price/BNB', 'Status', 'ErrCode', 'PrivateNote'],
           worksheet_name="Bscscan",
           row_handler=parse_bscscan)

def parse_bscscan_internal(data_row, _parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(int(in_row[2]))

    if Decimal(in_row[10]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[10],
                                                 buy_asset="BNB",
                                                 wallet=WALLET)
    elif Decimal(in_row[11]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[11],
                                                 sell_asset="BNB",
                                                 wallet=WALLET)
    else:
        """
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[8],
                                                 sell_asset="BNB",
                                                 fee_quantity=in_row[10],
                                                 fee_asset="BNB",
                                                 wallet=WALLET)
        """

DataParser(DataParser.TYPE_EXPLORER,
           "Bscscan (BNB-20 Tokens)",
           ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'Value', 'ContractAddress',
            'TokenName', 'TokenSymbol'],
           worksheet_name="Bscscan_BNB20",
           row_handler=parse_bscscan_tokens)

DataParser(DataParser.TYPE_EXPLORER,
           "Bscscan (Erc-721 NFTs)",
           ['Txhash', 'UnixTimestamp', 'DateTime', 'From', 'To', 'ContractAddress', 'TokenId',
            'TokenName', 'TokenSymbol'],
           worksheet_name="Bscscan_Erc721",
           row_handler=parse_bscscan_nfts)

DataParser(DataParser.TYPE_EXPLORER,
           "Bscscan (BNB)",
           ['Txhash','Blockno','UnixTimestamp','DateTime','ParentTxFrom','ParentTxTo','ParentTxETH_Value','From','TxTo',
            'ContractAddress','Value_IN(BNB)','Value_OUT(BNB)',None,'Historical $Price/BNB',
            'Status','ErrCode','Type'],
           worksheet_name="Bscscan",
           row_handler=parse_bscscan_internal)
