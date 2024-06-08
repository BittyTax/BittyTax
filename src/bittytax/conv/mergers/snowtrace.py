# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from typing import TYPE_CHECKING, Dict, List

from ...bt_types import FileId
from ..datamerge import DataMerge, ParserRequired
from ..parsers.snowtrace import avax_tokens, avax_txns
from .etherscan import TOKENS, TXNS, _do_merge_etherscan

STAKE_ADDRESSES: List[str] = []

if TYPE_CHECKING:
    from ..datafile import DataFile


def merge_snowtrace(data_files: Dict[FileId, "DataFile"]) -> bool:
    # Do same merge as Etherscan
    merge = _do_merge_etherscan(data_files, STAKE_ADDRESSES)

    if merge:
        # Change Etherscan wallet/worksheet name to SnowTrace
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
    "Snowtrace fees & multi-token transactions",
    {
        TXNS: {"req": ParserRequired.MANDATORY, "obj": avax_txns},
        TOKENS: {"req": ParserRequired.MANDATORY, "obj": avax_tokens},
    },
    merge_snowtrace,
)
