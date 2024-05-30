# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

from datetime import datetime
from typing import TYPE_CHECKING, Dict

from ...bt_types import FileId, TrType
from ..datamerge import DataMerge, ParserRequired
from ..parsers.coincorner import coincorner

if TYPE_CHECKING:
    from ..datafile import DataFile
    from ..datarow import DataRow

CC = FileId("coincorner")


def merge_coincorner(data_files: Dict[FileId, "DataFile"]) -> bool:
    merge = False
    buys: Dict[datetime, DataRow] = {}
    sells: Dict[datetime, DataRow] = {}

    for dr in data_files[CC].data_rows:
        if not dr.t_record or dr.t_record and dr.t_record.t_type is not TrType.TRADE:
            continue

        if dr.t_record.buy_quantity is not None:
            buys[dr.timestamp] = dr

        if dr.t_record.sell_quantity is not None:
            sells[dr.timestamp] = dr

    for dr in data_files[CC].data_rows:
        if not dr.t_record or dr.t_record.t_type is not TrType.TRADE:
            continue

        if dr.t_record.buy_quantity is None:
            t_record = buys[dr.timestamp].t_record
            if t_record:
                dr.t_record.buy_quantity = t_record.buy_quantity
                dr.t_record.buy_asset = t_record.buy_asset
                buys[dr.timestamp].t_record = None
                merge = True
        elif dr.t_record.sell_quantity is None:
            t_record = sells[dr.timestamp].t_record
            if t_record:
                dr.t_record.sell_quantity = t_record.sell_quantity
                dr.t_record.sell_asset = t_record.sell_asset
                sells[dr.timestamp].t_record = None
                merge = True

    return merge


DataMerge(
    "CoinCorner trades",
    {
        CC: {"req": ParserRequired.MANDATORY, "obj": coincorner},
    },
    merge_coincorner,
)
