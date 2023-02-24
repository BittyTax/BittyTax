# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from ..datamerge import DataMerge
from ..out_record import TransactionOutRecord
from ..parsers.etherscan import ETHERSCAN_NFTS, ETHERSCAN_TOKENS
from ..parsers.snowtrace import AVAX_INT, AVAX_TXNS, WALLET, WORKSHEET_NAME
from .etherscan import INTERNAL_TXNS, NFTS, TOKENS, TXNS, do_merge_etherscan

STAKE_ADDRESSES = []


def merge_snowtrace(data_files):
    # Do same merge as Etherscan
    merge = do_merge_etherscan(data_files, STAKE_ADDRESSES)

    if merge:
        # Change Etherscan parsers to SnowTrace
        if TOKENS in data_files:
            data_files[TOKENS].parser.worksheet_name = WORKSHEET_NAME
            for data_row in data_files[TOKENS].data_rows:
                if data_row.t_record:
                    address = data_row.t_record.wallet[-abs(TransactionOutRecord.WALLET_ADDR_LEN) :]
                    data_row.t_record.wallet = "%s-%s" % (WALLET, address)

        if NFTS in data_files:
            data_files[NFTS].parser.worksheet_name = WORKSHEET_NAME
            for data_row in data_files[NFTS].data_rows:
                if data_row.t_record:
                    address = data_row.t_record.wallet[-abs(TransactionOutRecord.WALLET_ADDR_LEN) :]
                    data_row.t_record.wallet = "%s-%s" % (WALLET, address)

    return merge


DataMerge(
    "SnowTrace fees & multi-token transactions",
    {
        TXNS: {"req": DataMerge.MAN, "obj": AVAX_TXNS},
        TOKENS: {"req": DataMerge.OPT, "obj": ETHERSCAN_TOKENS},
        NFTS: {"req": DataMerge.OPT, "obj": ETHERSCAN_NFTS},
        INTERNAL_TXNS: {"req": DataMerge.OPT, "obj": AVAX_INT},
    },
    merge_snowtrace,
)
