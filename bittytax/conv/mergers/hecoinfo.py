# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from .etherscan import do_merge_etherscan
from ..datamerge import DataMerge
from ..parsers.hecoinfo import heco_txns, WALLET
from ..parsers.etherscan import etherscan_tokens

STAKE_ADDRESSES = ['0x5fad6fbba4bba686ba9b8052cf0bd51699f38b93', #MakiSwap
                  ]

def merge_hecoinfo(data_files):
    # Do same merge as Etherscan
    merge = do_merge_etherscan(data_files, STAKE_ADDRESSES)

    if merge:
        # Change Etherscan to HECO
        data_files['tokens'].parser.worksheet_name = "HecoInfo"
        for data_row in data_files['tokens'].data_rows:
            if data_row.t_record:
                data_row.t_record.wallet = WALLET

    return merge

DataMerge("HecoInfo fees & multi-token transactions",
          {'txns': heco_txns, 'tokens': etherscan_tokens},
          merge_hecoinfo)
