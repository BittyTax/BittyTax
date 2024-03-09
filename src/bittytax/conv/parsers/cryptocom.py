# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal
from typing import TYPE_CHECKING

from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Crypto.com"


def parse_crypto_com(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Timestamp (UTC)"])

    if row_dict["Currency"] != config.ccy:
        value = DataParser.convert_currency(
            abs(Decimal(row_dict["Native Amount"])),
            row_dict["Native Currency"],
            data_row.timestamp,
        )
    else:
        value = None

    if row_dict["Transaction Kind"] == "crypto_transfer":
        if Decimal(row_dict["Amount"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.GIFT_RECEIVED,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount"]),
                buy_asset=row_dict["Currency"],
                buy_value=value,
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.GIFT_SENT,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Amount"])),
                sell_asset=row_dict["Currency"],
                sell_value=value,
                wallet=WALLET,
            )
    elif row_dict["Transaction Kind"] in (
        "crypto_earn_interest_paid",
        "mco_stake_reward",
        "crypto_earn_extra_interest_paid",
        "supercharger_reward_to_app_credited",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.INTEREST,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"],
            buy_value=value,
            wallet=WALLET,
        )
    elif row_dict["Transaction Kind"] == "rewards_platform_deposit_credited":
        data_row.t_record = TransactionOutRecord(
            TrType.INCOME,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"],
            buy_value=value,
            wallet=WALLET,
        )
    elif row_dict["Transaction Kind"] in (
        "viban_purchase",
        "van_purchase",
        "crypto_viban_exchange",
        "crypto_exchange",
        "crypto_to_van_sell_order",
        "trading.limit_order.fiat_wallet.sell_commit",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["To Amount"]),
            buy_asset=row_dict["To Currency"],
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=row_dict["Currency"],
            sell_value=value,
            wallet=WALLET,
        )
    elif row_dict["Transaction Kind"] in (
        "crypto_purchase",
        "dust_conversion_debited",
        "dust_conversion_credited",
    ):
        if Decimal(row_dict["Amount"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount"]),
                buy_asset=row_dict["Currency"],
                sell_quantity=Decimal(row_dict["Native Amount"]),
                sell_asset=row_dict["Native Currency"],
                wallet=WALLET,
            )
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.TRADE,
                data_row.timestamp,
                buy_quantity=abs(Decimal(row_dict["Native Amount"])),
                buy_asset=row_dict["Native Currency"],
                sell_quantity=abs(Decimal(row_dict["Amount"])),
                sell_asset=row_dict["Currency"],
                wallet=WALLET,
            )
    elif row_dict["Transaction Kind"] in ("referral_bonus", "referral_gift"):
        data_row.t_record = TransactionOutRecord(
            TrType.REFERRAL,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"],
            buy_value=value,
            wallet=WALLET,
        )
    elif row_dict["Transaction Kind"] in ("referral_card_cashback", "transfer_cashback"):
        data_row.t_record = TransactionOutRecord(
            TrType.CASHBACK,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"],
            buy_value=value,
            wallet=WALLET,
        )
    elif row_dict["Transaction Kind"] in (
        "reimbursement",
        "gift_card_reward",
        "admin_wallet_credited",
        "campaign_reward",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.AIRDROP,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"],
            buy_value=value,
            wallet=WALLET,
        )
    elif row_dict["Transaction Kind"] in (
        "crypto_payment",
        "card_top_up",
        "card_cashback_reverted",
        "reimbursement_reverted",
    ):
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=row_dict["Currency"],
            sell_value=value,
            wallet=WALLET,
        )
    elif row_dict["Transaction Kind"] in ("crypto_withdrawal", "crypto_to_exchange_transfer"):
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Amount"])),
            sell_asset=row_dict["Currency"],
            sell_value=value,
            wallet=WALLET,
        )
    elif row_dict["Transaction Kind"] in ("crypto_deposit", "exchange_to_crypto_transfer"):
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"],
            buy_value=value,
            wallet=WALLET,
        )
    elif row_dict["Transaction Kind"] in (
        "crypto_earn_program_created",
        "crypto_earn_program_withdrawn",
        "lockup_lock",
        "lockup_unlock",
        "lockup_upgrade",
        "lockup_swap_credited",
        "lockup_swap_debited",
        "dynamic_coin_swap_credited",
        "dynamic_coin_swap_debited",
        "dynamic_coin_swap_bonus_exchange_deposit",
        "interest_swap_credited",
        "interest_swap_debited",
        "crypto_wallet_swap_credited",
        "crypto_wallet_swap_debited",
        "supercharger_deposit",
        "supercharger_withdrawal",
        "council_node_deposit_created",
        "trading.limit_order.fiat_wallet.purchase_lock",
        "trading.limit_order.fiat_wallet.purchase_unlock",
        "trading.limit_order.fiat_wallet.sell_lock",
    ):
        return
    elif row_dict["Transaction Kind"] == "":
        # Could be a fiat transaction
        if "Deposit" in row_dict["Transaction Description"]:
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Amount"]),
                buy_asset=row_dict["Currency"],
                wallet=WALLET,
            )
        elif "Withdrawal" in row_dict["Transaction Description"]:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Amount"])),
                sell_asset=row_dict["Currency"],
                wallet=WALLET,
            )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Transaction Kind"),
            "Transaction Kind",
            row_dict["Transaction Kind"],
        )


DataParser(
    ParserType.EXCHANGE,
    "Crypto.com",
    [
        "Timestamp (UTC)",
        "Transaction Description",
        "Currency",
        "Amount",
        "To Currency",
        "To Amount",
        "Native Currency",
        "Native Amount",
        "Native Amount (in USD)",
        "Transaction Kind",
        "Transaction Hash",
    ],
    worksheet_name="Crypto.com",
    row_handler=parse_crypto_com,
)

DataParser(
    ParserType.EXCHANGE,
    "Crypto.com",
    [
        "Timestamp (UTC)",
        "Transaction Description",
        "Currency",
        "Amount",
        "To Currency",
        "To Amount",
        "Native Currency",
        "Native Amount",
        "Native Amount (in USD)",
        "Transaction Kind",
    ],
    worksheet_name="Crypto.com",
    row_handler=parse_crypto_com,
)
