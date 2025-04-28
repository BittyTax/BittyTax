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
    return _do_merge_etherscan(data_files, STAKE_ADDRESSES)


DataMerge(
    "Snowtrace fees & multi-token transactions",
    {
        TXNS: {"req": ParserRequired.MANDATORY, "obj": avax_txns},
        TOKENS: {"req": ParserRequired.MANDATORY, "obj": avax_tokens},
    },
    merge_snowtrace,
)
