# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from .etherscan import merge_etherscan
from ..datamerge import DataMerge
from ..parsers.bscscan import bsc_txns, WALLET
from ..parsers.etherscan import etherscan_tokens

def merge_bscscan(data_files):
    # Do same merge as Etherscan
    merge = merge_etherscan(data_files)

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
