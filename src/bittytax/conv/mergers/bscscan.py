# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from ..datamerge import DataMerge
from ..out_record import TransactionOutRecord
from ..parsers.bscscan import BSC_INT, BSC_TXNS, WALLET, WORKSHEET_NAME
from ..parsers.etherscan import ETHERSCAN_NFTS, ETHERSCAN_TOKENS
from .etherscan import INTERNAL_TXNS, NFTS, TOKENS, TXNS, _do_merge_etherscan

STAKE_ADDRESSES = ["0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82"]  # PancakeSwap


def merge_bscscan(data_files):
    # Do same merge as Etherscan
    merge = _do_merge_etherscan(data_files, STAKE_ADDRESSES)

    if merge:
        # Change Etherscan parsers to BscScan
        if TOKENS in data_files:
            data_files[TOKENS].parser.worksheet_name = WORKSHEET_NAME
            for data_row in data_files[TOKENS].data_rows:
                if data_row.t_record:
                    address = data_row.t_record.wallet[-abs(TransactionOutRecord.WALLET_ADDR_LEN) :]
                    data_row.t_record.wallet = f"{WALLET}-{address}"

        if NFTS in data_files:
            data_files[NFTS].parser.worksheet_name = WORKSHEET_NAME
            for data_row in data_files[NFTS].data_rows:
                if data_row.t_record:
                    address = data_row.t_record.wallet[-abs(TransactionOutRecord.WALLET_ADDR_LEN) :]
                    data_row.t_record.wallet = f"{WALLET}-{address}"

    return merge


DataMerge(
    "BscScan fees & multi-token transactions",
    {
        TXNS: {"req": DataMerge.MAN, "obj": BSC_TXNS},
        TOKENS: {"req": DataMerge.OPT, "obj": ETHERSCAN_TOKENS},
        NFTS: {"req": DataMerge.OPT, "obj": ETHERSCAN_NFTS},
        INTERNAL_TXNS: {"req": DataMerge.OPT, "obj": BSC_INT},
    },
    merge_bscscan,
)
