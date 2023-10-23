# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

import copy
import datetime
from typing import TYPE_CHECKING, Dict

from ...bt_types import FileId, TrType
from ...config import config
from ...constants import TZ_UTC
from ..datamerge import DataMerge, ParserRequired
from ..out_record import TransactionOutRecord
from ..parsers.coinbase import WALLET, coinbase_v2
from ..parsers.coinbasepro import coinbase_pro_account_v2

if TYPE_CHECKING:
    from ..datafile import DataFile
    from ..datarow import DataRow

CB = FileId("coinbase")
CB_PRO = FileId("coinbasepro")

# This is a guestimate of when Coinbase Pro crypto transfer relays stopped 
RELAY_TIMESTAMP = datetime.datetime(2022, 1, 1, tzinfo=TZ_UTC)


def merge_coinbase(data_files: Dict[FileId, "DataFile"]) -> bool:
    merge = False

    for dr in data_files[CB_PRO].data_rows:
        if not dr.row_dict["transfer id"]:
            continue

        if not dr.t_record:
            continue

        if dr.t_record.t_type is TrType.DEPOSIT:
            if dr.t_record.buy_asset in config.fiat_list:
                dr.t_record.note = "from Coinbase"

                # We need to add both a Coinbase Deposit, and a Withdrawal to Coinbase Pro
                dup_data_row = copy.copy(dr)
                dup_data_row.row = []
                dup_data_row.t_record = TransactionOutRecord(
                    TrType.DEPOSIT,
                    dr.timestamp,
                    buy_quantity=dr.t_record.buy_quantity,
                    buy_asset=dr.t_record.buy_asset,
                    wallet=WALLET,
                )
                data_files[CB].data_rows.append(dup_data_row)

                dup_data_row = copy.copy(dr)
                dup_data_row.row = []
                dup_data_row.t_record = TransactionOutRecord(
                    TrType.WITHDRAWAL,
                    dr.timestamp,
                    sell_quantity=dr.t_record.buy_quantity,
                    sell_asset=dr.t_record.buy_asset,
                    wallet=WALLET,
                    note=f'to Coinbase Pro ({dr.row_dict["transfer id"]})',
                )
                data_files[CB].data_rows.append(dup_data_row)
                merge = True
            else:
                # Crypto deposits stopped being relayed after a specific date
                if dr.t_record.timestamp < RELAY_TIMESTAMP:
                    dr.t_record.note = "from Coinbase"

                    # We just need to add a Withdrawal to Coinbase Pro
                    dup_data_row = copy.copy(dr)
                    dup_data_row.row = []
                    dup_data_row.t_record = TransactionOutRecord(
                        TrType.WITHDRAWAL,
                        dr.timestamp,
                        sell_quantity=dr.t_record.buy_quantity,
                        sell_asset=dr.t_record.buy_asset,
                        wallet=WALLET,
                        note=f'to Coinbase Pro ({dr.row_dict["transfer id"]})',
                    )
                    data_files[CB].data_rows.append(dup_data_row)
                    merge = True
        elif dr.t_record.t_type is TrType.WITHDRAWAL:
            if dr.t_record.sell_asset in config.fiat_list:
                dr.t_record.note = "to Coinbase"

                # We need to add both a Coinbase Withdrawal, and a Deposit from Coinbase Pro
                dup_data_row = copy.copy(dr)
                dup_data_row.row = []
                dup_data_row.t_record = TransactionOutRecord(
                    TrType.WITHDRAWAL,
                    dr.timestamp,
                    sell_quantity=dr.t_record.sell_quantity,
                    sell_asset=dr.t_record.sell_asset,
                    wallet=WALLET,
                )
                data_files[CB].data_rows.append(dup_data_row)

                dup_data_row = copy.copy(dr)
                dup_data_row.row = []
                dup_data_row.t_record = TransactionOutRecord(
                    TrType.DEPOSIT,
                    dr.timestamp,
                    buy_quantity=dr.t_record.sell_quantity,
                    buy_asset=dr.t_record.sell_asset,
                    wallet=WALLET,
                    note=f'from Coinbase Pro ({dr.row_dict["transfer id"]})',
                )
                data_files[CB].data_rows.append(dup_data_row)
                merge = True
            else:
                # Crypto withdrawals stopped being relayed after a specific date
                if dr.t_record.timestamp < RELAY_TIMESTAMP:
                    dr.t_record.note = "to Coinbase"

                    # We just need to add a Deposit to Coinbase Pro
                    dup_data_row = copy.copy(dr)
                    dup_data_row.row = []
                    dup_data_row.t_record = TransactionOutRecord(
                        TrType.DEPOSIT,
                        dr.timestamp,
                        buy_quantity=dr.t_record.sell_quantity,
                        buy_asset=dr.t_record.sell_asset,
                        wallet=WALLET,
                        note=f'from Coinbase Pro ({dr.row_dict["transfer id"]})',
                    )
                    data_files[CB].data_rows.append(dup_data_row)
                    merge = True

    return merge


DataMerge(
    "Coinbase add transfers to/from Coinbase Pro",
    {
        CB: {"req": ParserRequired.MANDATORY, "obj": coinbase_v2},
        CB_PRO: {"req": ParserRequired.MANDATORY, "obj": coinbase_pro_account_v2},
    },
    merge_coinbase,
)
