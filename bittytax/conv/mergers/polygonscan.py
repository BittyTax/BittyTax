# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from .etherscan import do_merge_etherscan, TXNS, TOKENS, NFTS, INTERNAL_TXNS
from ..datamerge import DataMerge
from ..parsers.polygonscan import matic_txns, matic_int, WALLET
from ..parsers.etherscan import etherscan_tokens, etherscan_nfts

STAKE_ADDRESSES = []

def merge_polygonscan(data_files):
    # Do same merge as Etherscan
    merge = do_merge_etherscan(data_files, STAKE_ADDRESSES)

    if merge:
        # Change Etherscan parsers to PolygonScan
        if TOKENS in data_files:
            data_files[TOKENS].parser.worksheet_name = "PolygonScan"
            for data_row in data_files[TOKENS].data_rows:
                if data_row.t_record:
                    data_row.t_record.wallet = WALLET

        if NFTS in data_files:
            data_files[NFTS].parser.worksheet_name = "PolygonScan"
            for data_row in data_files[NFTS].data_rows:
                if data_row.t_record:
                    data_row.t_record.wallet = WALLET

    return merge

DataMerge("PolygonScan fees & multi-token transactions",
          {TXNS: {'req': DataMerge.MAN, 'obj': matic_txns},
           TOKENS: {'req': DataMerge.OPT, 'obj': etherscan_tokens},
           NFTS: {'req': DataMerge.OPT, 'obj': etherscan_nfts},
           INTERNAL_TXNS: {'req': DataMerge.OPT, 'obj': matic_int}},
          merge_polygonscan)
