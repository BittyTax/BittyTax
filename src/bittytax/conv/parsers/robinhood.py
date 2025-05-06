# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Robinhood"


def parse_robinhood_trades(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict

    if "Time Entered" in row_dict:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["Time Entered"])
    else:
        return

    if row_dict["State"] != "Filled":
        return

    if row_dict["Side"] == "Buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Quantity"]),
            buy_asset=row_dict["Symbol"],
            sell_quantity=Decimal(row_dict["Notional"].strip(" ($)").replace(",", "")),
            sell_asset="USD",
            wallet=WALLET,
        )
    elif row_dict["Side"] == "Sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Notional"].strip(" ($)").replace(",", "")),
            buy_asset="USD",
            sell_quantity=Decimal(row_dict["Quantity"]),
            sell_asset=row_dict["Symbol"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


def parse_robinhood_deposits_withdrawals(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict

    if "created_at" in row_dict:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["created_at"])
    else:
        return

    if row_dict["state"] != "succeeded":
        return

    data_row.tx_raw = TxRawPos(
        parser.in_header.index("blockchain_txn_id"),
        tx_dest_pos=parser.in_header.index("to_address"),
    )

    if row_dict["transfer_type"] == "withdrawal":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["amount"]),
            sell_asset=row_dict["currency_code"],
            fee_quantity=Decimal(row_dict["network_fee"]),
            fee_asset=row_dict["currency_code"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("transfer_type"), "transfer_type", row_dict["transfer_type"]
        )


DataParser(
    ParserType.EXCHANGE,
    "Robinhood Trades",
    [
        "UUID",
        "Time Entered",
        "Symbol",
        "Side",
        "Quantity",
        "State",
        "Order Type",
        "Leaves Quantity",
        "Entered Price",
        "Average Price",
        "Notional",
    ],
    worksheet_name="Robinhood T",
    row_handler=parse_robinhood_trades,
)

DataParser(
    ParserType.EXCHANGE,
    "Robinhood Deposits/Withdrawals",
    [
        "id",
        "created_at",
        "withdrawal_submitted_timestamp",
        "currency_code",
        "transfer_type",
        "amount",
        "network",
        "network_fee",
        "native_network_fee",
        "usd_amount_at_request",
        "fiat_amount_at_request",
        "state",
        "to_address",
        "address_tag",
        "blockchain_txn_id",
        "blockchain_txn_state",
    ],
    worksheet_name="Robinhood D,W",
    row_handler=parse_robinhood_deposits_withdrawals,
)
