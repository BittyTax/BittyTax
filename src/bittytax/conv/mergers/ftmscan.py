# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

from typing import TYPE_CHECKING, Dict, List

from ...bt_types import FileId
from ..datamerge import DataMerge, ParserRequired
from ..out_record import TransactionOutRecord
from ..parsers.etherscan import etherscan_nfts, etherscan_tokens
from ..parsers.ftmscan import WALLET, WORKSHEET_NAME, ftm_int, ftm_txns
from .etherscan import INTERNAL_TXNS, NFTS, TOKENS, TXNS, _do_merge_etherscan

STAKE_ADDRESSES: List[str] = []

if TYPE_CHECKING:
    from ..datafile import DataFile


def merge_ftmscan(data_files: Dict[FileId, "DataFile"]) -> bool:
    # Do same merge as Etherscan
    merge = _do_merge_etherscan(data_files, STAKE_ADDRESSES)

    if merge:
        # Change Etherscan parsers to FTMScan
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
    "FTMScan fees & multi-token transactions",
    {
        TXNS: {"req": ParserRequired.MANDATORY, "obj": ftm_txns},
        TOKENS: {"req": ParserRequired.OPTIONAL, "obj": etherscan_tokens},
        NFTS: {"req": ParserRequired.OPTIONAL, "obj": etherscan_nfts},
        INTERNAL_TXNS: {"req": ParserRequired.OPTIONAL, "obj": ftm_int},
    },
    merge_ftmscan,
)
