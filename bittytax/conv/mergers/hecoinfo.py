# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from .etherscan import merge_etherscan
from ..datamerge import DataMerge
from ..parsers.hecoinfo import heco_txns, WALLET
from ..parsers.etherscan import etherscan_tokens

def merge_hecoinfo(data_files):
    # Do same merge as Etherscan
    merge = merge_etherscan(data_files)

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
