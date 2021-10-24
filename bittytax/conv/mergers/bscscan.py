# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from .etherscan import do_merge_etherscan
from ..datamerge import DataMerge
from ..parsers.bscscan import bsc_txns, WALLET
from ..parsers.etherscan import etherscan_tokens

STAKE_ADDRESSES = ['0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82', #PancakeSwap
                  ]

def merge_bscscan(data_files):
    # Do same merge as Etherscan
    merge = do_merge_etherscan(data_files, STAKE_ADDRESSES)

    if merge:
        # Change Etherscan to BscScan
        data_files['tokens'].parser.worksheet_name = "BscScan"
        for data_row in data_files['tokens'].data_rows:
            if data_row.t_record:
                data_row.t_record.wallet = WALLET

    return merge

DataMerge("BscScan fees & multi-token transactions",
          {'txns': bsc_txns, 'tokens': etherscan_tokens},
          merge_bscscan)
