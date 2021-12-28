# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from .etherscan import do_merge_etherscan, TXNS, TOKENS, NFTS, INTERNAL_TXNS
from ..datamerge import DataMerge
from ..parsers.hecoinfo import heco_txns, heco_int, WALLET
from ..parsers.etherscan import etherscan_tokens, etherscan_nfts

STAKE_ADDRESSES = ['0x5fad6fbba4bba686ba9b8052cf0bd51699f38b93', #MakiSwap
                  ]

def merge_hecoinfo(data_files):
    # Do same merge as Etherscan
    merge = do_merge_etherscan(data_files, STAKE_ADDRESSES)

    if merge:
        # Change Etherscan parsers to HECO
        if TOKENS in data_files:
            data_files[TOKENS].parser.worksheet_name = "HecoInfo"
            for data_row in data_files[TOKENS].data_rows:
                if data_row.t_record:
                    data_row.t_record.wallet = WALLET

        if NFTS in data_files:
            data_files[NFTS].parser.worksheet_name = "HecoInfo"
            for data_row in data_files[NFTS].data_rows:
                if data_row.t_record:
                    data_row.t_record.wallet = WALLET

    return merge

DataMerge("HecoInfo fees & multi-token transactions",
          {TXNS: {'req': DataMerge.MAN, 'obj': heco_txns},
           TOKENS: {'req': DataMerge.OPT, 'obj': etherscan_tokens},
           NFTS: {'req': DataMerge.OPT, 'obj': etherscan_nfts},
           INTERNAL_TXNS: {'req': DataMerge.OPT, 'obj': heco_int}},
          merge_hecoinfo)
