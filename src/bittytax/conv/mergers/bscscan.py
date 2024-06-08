# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from typing import TYPE_CHECKING, Dict

from ...bt_types import FileId
from ..datamerge import DataMerge, ParserRequired
from ..out_record import TransactionOutRecord
from ..parsers.bscscan import WALLET, WORKSHEET_NAME, bsc_int, bsc_txns
from ..parsers.etherscan import etherscan_nfts, etherscan_tokens
from .etherscan import INTERNAL_TXNS, NFTS, TOKENS, TXNS, _do_merge_etherscan

STAKE_ADDRESSES = ["0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82"]  # PancakeSwap

if TYPE_CHECKING:
    from ..datafile import DataFile


def merge_bscscan(data_files: Dict[FileId, "DataFile"]) -> bool:
    # Do same merge as Etherscan
    merge = _do_merge_etherscan(data_files, STAKE_ADDRESSES)

    if merge:
        # Change Etherscan wallet/worksheet name to BscScan
        if TOKENS in data_files:
            data_files[TOKENS].parser.worksheet_name = WORKSHEET_NAME
            for data_row in data_files[TOKENS].data_rows:
                if data_row.t_record:
                    address = data_row.t_record.wallet[-abs(TransactionOutRecord.WALLET_ADDR_LEN) :]
                    data_row.t_record.wallet = f"{WALLET}-{address}"

                data_row.worksheet_name = WORKSHEET_NAME

        if NFTS in data_files:
            data_files[NFTS].parser.worksheet_name = WORKSHEET_NAME
            for data_row in data_files[NFTS].data_rows:
                if data_row.t_record:
                    address = data_row.t_record.wallet[-abs(TransactionOutRecord.WALLET_ADDR_LEN) :]
                    data_row.t_record.wallet = f"{WALLET}-{address}"

                data_row.worksheet_name = WORKSHEET_NAME

    return merge


DataMerge(
    "BscScan fees & multi-token transactions",
    {
        TXNS: {"req": ParserRequired.MANDATORY, "obj": bsc_txns},
        TOKENS: {"req": ParserRequired.OPTIONAL, "obj": etherscan_tokens},
        NFTS: {"req": ParserRequired.OPTIONAL, "obj": etherscan_nfts},
        INTERNAL_TXNS: {"req": ParserRequired.OPTIONAL, "obj": bsc_int},
    },
    merge_bscscan,
)
