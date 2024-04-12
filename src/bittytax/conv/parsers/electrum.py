# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnknownCryptoassetError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Electrum"


def parse_electrum_v3(
    data_row: "DataRow", _parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["timestamp"], tz=config.local_timezone)

    if not kwargs["cryptoasset"]:
        raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet", ""))

    value = Decimal(row_dict["value"].replace(",", ""))
    if value > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=value,
            buy_asset=kwargs["cryptoasset"],
            wallet=WALLET,
            note=row_dict["label"],
        )
    else:
        if row_dict["fee"]:
            sell_quantity = abs(value) - Decimal(row_dict["fee"])
            fee_quantity = Decimal(row_dict["fee"])
            fee_asset = kwargs["cryptoasset"]
        else:
            sell_quantity = abs(value)
            fee_quantity = None
            fee_asset = ""

        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=sell_quantity,
            sell_asset=kwargs["cryptoasset"],
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
            note=row_dict["label"],
        )


def parse_electrum_v2(
    data_row: "DataRow", _parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    parse_electrum_v1(data_row, _parser, **kwargs)


def parse_electrum_v1(
    data_row: "DataRow", _parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["timestamp"], tz=config.local_timezone)

    if not kwargs["cryptoasset"]:
        raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet", ""))

    value = Decimal(row_dict["value"].replace(",", ""))
    if value > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=value,
            buy_asset=kwargs["cryptoasset"],
            wallet=WALLET,
            note=row_dict["label"],
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(value),
            sell_asset=kwargs["cryptoasset"],
            wallet=WALLET,
            note=row_dict["label"],
        )


DataParser(
    ParserType.WALLET,
    "Electrum",
    [
        "transaction_hash",
        "label",
        "confirmations",
        "value",
        "fiat_value",
        "fee",
        "fiat_fee",
        "timestamp",
    ],
    worksheet_name="Electrum",
    row_handler=parse_electrum_v3,
)

DataParser(
    ParserType.WALLET,
    "Electrum",
    ["transaction_hash", "label", "value", "timestamp"],
    worksheet_name="Electrum",
    # Different handler name used to prevent data file consolidation
    row_handler=parse_electrum_v2,
)

DataParser(
    ParserType.WALLET,
    "Electrum",
    ["transaction_hash", "label", "confirmations", "value", "timestamp"],
    worksheet_name="Electrum",
    row_handler=parse_electrum_v1,
)
