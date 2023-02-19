# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from .etherscan import do_merge_etherscan, TXNS, TOKENS, NFTS, INTERNAL_TXNS
from ..datamerge import DataMerge
from ..out_record import TransactionOutRecord
from ..parsers.hecoinfo import HECO_TXNS, HECO_INT, WALLET, WORKSHEET_NAME
from ..parsers.etherscan import ETHERSCAN_TOKENS, ETHERSCAN_NFTS

STAKE_ADDRESSES = ['0x5fad6fbba4bba686ba9b8052cf0bd51699f38b93']  # MakiSwap

def merge_hecoinfo(data_files):
    # Do same merge as Etherscan
    merge = do_merge_etherscan(data_files, STAKE_ADDRESSES)

    if merge:
        # Change Etherscan parsers to HECO
        if TOKENS in data_files:
            data_files[TOKENS].parser.worksheet_name = WORKSHEET_NAME
            for data_row in data_files[TOKENS].data_rows:
                if data_row.t_record:
                    address = data_row.t_record.wallet[- abs(TransactionOutRecord.WALLET_ADDR_LEN):]
                    data_row.t_record.wallet = "%s-%s" % (WALLET, address)

        if NFTS in data_files:
            data_files[NFTS].parser.worksheet_name = WORKSHEET_NAME
            for data_row in data_files[NFTS].data_rows:
                if data_row.t_record:
                    address = data_row.t_record.wallet[- abs(TransactionOutRecord.WALLET_ADDR_LEN):]
                    data_row.t_record.wallet = "%s-%s" % (WALLET, address)

    return merge

DataMerge("HecoInfo fees & multi-token transactions",
          {TXNS: {'req': DataMerge.MAN, 'obj': HECO_TXNS},
           TOKENS: {'req': DataMerge.OPT, 'obj': ETHERSCAN_TOKENS},
           NFTS: {'req': DataMerge.OPT, 'obj': ETHERSCAN_NFTS},
           INTERNAL_TXNS: {'req': DataMerge.OPT, 'obj': HECO_INT}},
          merge_hecoinfo)
