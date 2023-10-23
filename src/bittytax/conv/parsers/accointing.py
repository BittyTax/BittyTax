# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from decimal import Decimal
from typing import TYPE_CHECKING, Union

from typing_extensions import Unpack

from ...bt_types import TrType, UnmappedType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

ACCOINTING_D_MAPPING = {
    "": TrType.DEPOSIT,  # Default
    "add_funds": TrType.DEPOSIT,
    "airdrop": TrType.AIRDROP,
    "bounty": TrType.INCOME,
    "gambling_income": TrType.GIFT_RECEIVED,
    "gift_received": TrType.GIFT_RECEIVED,
    "hard_fork": TrType.GIFT_RECEIVED,
    "income": TrType.INCOME,
    "internal": TrType.DEPOSIT,
    "lending_income": TrType.INTEREST,
    "liquidity_pool": TrType.STAKING,
    "master_node": TrType.STAKING,
    "mined": TrType.MINING,
    "staked": TrType.STAKING,
}

ACCOINTING_W_MAPPING = {
    "": TrType.WITHDRAWAL,  # Default
    "remove_funds": TrType.WITHDRAWAL,
    "fee": TrType.SPEND,
    "gambling_used": TrType.SPEND,
    "gift_sent": TrType.GIFT_SENT,
    "interest_paid": TrType.SPEND,
    "internal": TrType.WITHDRAWAL,
    "lost": TrType.LOST,
    "payment": TrType.SPEND,
}


def parse_accointing(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["timeExecuted"])

    if row_dict["feeCurrency"]:
        fee_quantity = Decimal(row_dict["feeQuantity"])
    else:
        fee_quantity = None

    if row_dict["boughtQuantity"] and row_dict["soldQuantity"]:
        # Trade
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["boughtQuantity"]),
            buy_asset=row_dict["boughtCurrency"],
            sell_quantity=Decimal(row_dict["soldQuantity"]),
            sell_asset=row_dict["soldCurrency"],
            fee_quantity=fee_quantity,
            fee_asset=row_dict["feeCurrency"],
            wallet=row_dict["walletName"],
        )
    elif row_dict["boughtQuantity"]:
        # Deposit
        if row_dict["classification"] == "ignored":
            # Skip
            return

        if row_dict["classification"] in ACCOINTING_D_MAPPING:
            t_type: Union[TrType, UnmappedType] = ACCOINTING_D_MAPPING[row_dict["classification"]]
        else:
            t_type = UnmappedType(f'_{row_dict["classification"]}')

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["boughtQuantity"]),
            buy_asset=row_dict["boughtCurrency"],
            fee_quantity=fee_quantity,
            fee_asset=row_dict["feeCurrency"],
            wallet=row_dict["walletName"],
        )
    elif row_dict["soldQuantity"]:
        # Withdrawal
        if row_dict["classification"] == "ignored":
            # Skip
            return

        if row_dict["classification"] in ACCOINTING_W_MAPPING:
            t_type = ACCOINTING_W_MAPPING[row_dict["classification"]]
        else:
            t_type = UnmappedType(f'_{row_dict["classification"]}')

        data_row.t_record = TransactionOutRecord(
            t_type,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["soldQuantity"]),
            sell_asset=row_dict["soldCurrency"],
            fee_quantity=fee_quantity,
            fee_asset=row_dict["feeCurrency"],
            wallet=row_dict["walletName"],
        )


DataParser(
    ParserType.ACCOUNTING,
    "Accointing",
    [
        "timeExecuted",
        "type",
        "boughtQuantity",
        "boughtCurrency",
        "boughtCurrencyId",
        "soldQuantity",
        "soldCurrency",
        "soldCurrencyId",
        "feeQuantity",
        "feeCurrency",
        "feeCurrencyId",
        "classification",
        "walletName",
        "walletProvider",
        "providerId",  # New field
        "txId",
        "primaryAddress",
        "otherAddress",
        "temporaryCurrencyName",
        "temporaryFeeCurrencyName",
        "temporaryBoughtCurrencyTicker",
        "temporarySoldCurrencyTicker",
        "temporaryFeeCurrencyTicker",
        "id",
        "associatedTransferId",
        "comments",
        "fiatValueOverwrite",  # New field
        "feeFiatValueOverwrite",  # New field
    ],
    worksheet_name="Accointing",
    row_handler=parse_accointing,
)

DataParser(
    ParserType.ACCOUNTING,
    "Accointing",
    [
        "timeExecuted",
        "type",
        "boughtQuantity",
        "boughtCurrency",
        "boughtCurrencyId",
        "soldQuantity",
        "soldCurrency",
        "soldCurrencyId",
        "feeQuantity",
        "feeCurrency",
        "feeCurrencyId",
        "classification",
        "walletName",
        "walletProvider",
        "txId",
        "primaryAddress",
        "otherAddress",
        "temporaryCurrencyName",
        "temporaryFeeCurrencyName",
        "temporaryBoughtCurrencyTicker",
        "temporarySoldCurrencyTicker",
        "temporaryFeeCurrencyTicker",
        "id",
        "associatedTransferId",
        "comments",
    ],
    worksheet_name="Accointing",
    row_handler=parse_accointing,
)
