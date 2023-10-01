# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from typing import TYPE_CHECKING, Dict

from ...types import FileId
from ..datamerge import DataMerge, ParserRequired
from ..out_record import TransactionOutRecord
from ..parsers.etherscan import etherscan_nfts, etherscan_tokens
from ..parsers.hecoinfo import WALLET, WORKSHEET_NAME, heco_int, heco_txns
from .etherscan import INTERNAL_TXNS, NFTS, TOKENS, TXNS, _do_merge_etherscan

STAKE_ADDRESSES = ["0x5fad6fbba4bba686ba9b8052cf0bd51699f38b93"]  # MakiSwap

if TYPE_CHECKING:
    from ..datafile import DataFile


def merge_hecoinfo(data_files: Dict[FileId, "DataFile"]) -> bool:
    # Do same merge as Etherscan
    merge = _do_merge_etherscan(data_files, STAKE_ADDRESSES)

    if merge:
        # Change Etherscan parsers to HECO
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
    "HecoInfo fees & multi-token transactions",
    {
        TXNS: {"req": ParserRequired.MANDATORY, "obj": heco_txns},
        TOKENS: {"req": ParserRequired.OPTIONAL, "obj": etherscan_tokens},
        NFTS: {"req": ParserRequired.OPTIONAL, "obj": etherscan_nfts},
        INTERNAL_TXNS: {"req": ParserRequired.OPTIONAL, "obj": heco_int},
    },
    merge_hecoinfo,
)
