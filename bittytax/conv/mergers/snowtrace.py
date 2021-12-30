# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from .etherscan import do_merge_etherscan, TXNS, TOKENS, NFTS, INTERNAL_TXNS
from ..datamerge import DataMerge
from ..parsers.snowtrace import avax_txns, avax_int, WALLET
from ..parsers.etherscan import etherscan_tokens, etherscan_nfts

STAKE_ADDRESSES = []

def merge_snowtrace(data_files):
    # Do same merge as Etherscan
    merge = do_merge_etherscan(data_files, STAKE_ADDRESSES)

    if merge:
        # Change Etherscan parsers to SnowTrace
        if TOKENS in data_files:
            data_files[TOKENS].parser.worksheet_name = "SnowTrace"
            for data_row in data_files[TOKENS].data_rows:
                if data_row.t_record:
                    data_row.t_record.wallet = WALLET

        if NFTS in data_files:
            data_files[NFTS].parser.worksheet_name = "SnowTrace"
            for data_row in data_files[NFTS].data_rows:
                if data_row.t_record:
                    data_row.t_record.wallet = WALLET

    return merge

DataMerge("SnowTrace fees & multi-token transactions",
          {TXNS: {'req': DataMerge.MAN, 'obj': avax_txns},
           TOKENS: {'req': DataMerge.OPT, 'obj': etherscan_tokens},
           NFTS: {'req': DataMerge.OPT, 'obj': etherscan_nfts},
           INTERNAL_TXNS: {'req': DataMerge.OPT, 'obj': avax_int}},
          merge_snowtrace)
