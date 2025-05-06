# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import copy
import re
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, List

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import DataFormatNotSupported, DataRowError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "KuCoin"


def parse_kucoin_trades_v5(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict

    if parser.args:
        timestamp_hdr = parser.args[0].group(1)
        utc_offset = parser.args[0].group(2)
        data_row.timestamp = DataParser.parse_timestamp(f"{row_dict[timestamp_hdr]} {utc_offset}")
    else:
        data_row.timestamp = DataParser.parse_timestamp(
            row_dict["Filled Time"], tz="Asia/Singapore"
        )

    if row_dict["Side"] == "BUY":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Filled Amount"]),
            buy_asset=row_dict["Symbol"].split("-")[0],
            sell_quantity=Decimal(row_dict["Filled Volume"]),
            sell_asset=row_dict["Symbol"].split("-")[1],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Fee Currency"],
            wallet=WALLET,
        )
    elif row_dict["Side"] == "SELL":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Filled Volume"]),
            buy_asset=row_dict["Symbol"].split("-")[1],
            sell_quantity=Decimal(row_dict["Filled Amount"]),
            sell_asset=row_dict["Symbol"].split("-")[0],
            fee_quantity=Decimal(row_dict["Fee"]),
            fee_asset=row_dict["Fee Currency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("Side"), "Side", row_dict["Side"])


def parse_kucoin_trades_v4(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["createdDate"], tz="Asia/Singapore")

    if row_dict["direction"].lower() == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount"]),
            buy_asset=row_dict["symbol"].split("-")[0],
            sell_quantity=Decimal(row_dict["dealValue"]),
            sell_asset=row_dict["symbol"].split("-")[1],
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=row_dict["symbol"].split("-")[1],
            wallet=WALLET,
        )
    elif row_dict["direction"].lower() == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["dealValue"]),
            buy_asset=row_dict["symbol"].split("-")[1],
            sell_quantity=Decimal(row_dict["amount"]),
            sell_asset=row_dict["symbol"].split("-")[0],
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=row_dict["symbol"].split("-")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("direction"), "direction", row_dict["direction"]
        )


def parse_kucoin_trades_v3(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["tradeCreatedAt"], tz="Asia/Singapore")

    if row_dict["side"] == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["size"]),
            buy_asset=row_dict["symbol"].split("-")[0],
            sell_quantity=Decimal(row_dict["funds"]),
            sell_asset=row_dict["symbol"].split("-")[1],
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=row_dict["feeCurrency"],
            wallet=WALLET,
        )
    elif row_dict["side"] == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["funds"]),
            buy_asset=row_dict["symbol"].split("-")[1],
            sell_quantity=Decimal(row_dict["size"]),
            sell_asset=row_dict["symbol"].split("-")[0],
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=row_dict["feeCurrency"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("side"), "side", row_dict["side"])


def parse_kucoin_trades_v2(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["created_at"], tz="Asia/Singapore")

    if row_dict["direction"].lower() == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount_coin"]),
            buy_asset=row_dict["symbol"].split("-")[0],
            sell_quantity=Decimal(row_dict["funds"]),
            sell_asset=row_dict["symbol"].split("-")[1],
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=row_dict["symbol"].split("-")[1],
            wallet=WALLET,
        )
    elif row_dict["direction"].lower() == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["funds"]),
            buy_asset=row_dict["symbol"].split("-")[1],
            sell_quantity=Decimal(row_dict["amount_coin"]),
            sell_asset=row_dict["symbol"].split("-")[0],
            fee_quantity=Decimal(row_dict["fee"]),
            fee_asset=row_dict["symbol"].split("-")[1],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("direction"), "direction", row_dict["direction"]
        )


def parse_kucoin_trades_v1(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["created_at"], tz="Asia/Singapore")

    if row_dict["direction"].lower() == "buy":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["amount"]),
            buy_asset=row_dict["symbol"].split("-")[0],
            sell_quantity=Decimal(row_dict["deal_value"]),
            sell_asset=row_dict["symbol"].split("-")[1],
            wallet=WALLET,
        )
    elif row_dict["direction"].lower() == "sell":
        data_row.t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["deal_value"]),
            buy_asset=row_dict["symbol"].split("-")[1],
            sell_quantity=Decimal(row_dict["amount"]),
            sell_asset=row_dict["symbol"].split("-")[0],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("direction"), "direction", row_dict["direction"]
        )


def parse_kucoin_fiat_trades(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict

    timestamp_hdr = parser.args[0].group(1)
    utc_offset = parser.args[0].group(2)
    data_row.timestamp = DataParser.parse_timestamp(f"{row_dict[timestamp_hdr]} {utc_offset}")

    if row_dict["Status"] != "DONE":
        return

    if row_dict["Fee Currency"]:
        fee_quantity = Decimal(row_dict["Fee"])
    else:
        fee_quantity = None

    data_row.t_record = TransactionOutRecord(
        TrType.TRADE,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Crypto Quantity,"]),
        buy_asset=row_dict["Currency (Crypto)"],
        sell_quantity=Decimal(row_dict["Fiat Amount"]),
        sell_asset=row_dict["Currency (Fiat)"],
        fee_quantity=fee_quantity,
        fee_asset=row_dict["Fee Currency"],
        wallet=WALLET,
    )


def parse_kucoin_fiat_trades_v2(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict

    timestamp_hdr = parser.args[0].group(1)
    utc_offset = parser.args[0].group(2)

    data_row.timestamp = DataParser.parse_timestamp(f"{row_dict[timestamp_hdr]} {utc_offset}")

    if row_dict["Status"] != "SUCCEEDED":
        return

    data_row.t_record = TransactionOutRecord(
        TrType.TRADE,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Crypto Quantity"]),
        buy_asset=row_dict["Currency (Crypto)"],
        sell_quantity=Decimal(row_dict["Fiat Amount"]),
        sell_asset=row_dict["Currency (Fiat)"],
        fee_quantity=Decimal(row_dict["Fee (Fiat)"]),
        fee_asset=row_dict["Fee Currency (Fiat)"],
        wallet=WALLET,
    )


def parse_kucoin_deposits_withdrawals_crypto_v1(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["created_at"], tz="Asia/Singapore")
    data_row.tx_raw = TxRawPos(parser.in_header.index("hash"))

    if row_dict["type"] == "DEPOSIT":
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["vol"]),
            buy_asset=row_dict["coin_type"],
            wallet=WALLET,
        )
    elif row_dict["type"] == "WITHDRAW":
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["vol"]),
            sell_asset=row_dict["coin_type"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def parse_kucoin_deposits_crypto(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"], tz="Asia/Singapore")

    data_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount"]),
        buy_asset=row_dict["Coin"],
        fee_quantity=Decimal(row_dict["Fee"]) if "Fee" in row_dict else None,
        fee_asset=row_dict["Coin"] if "Fee" in row_dict else "",
        wallet=WALLET,
    )


def parse_kucoin_withdrawals_crypto(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"], tz="Asia/Singapore")
    if "Wallet Address" in row_dict:
        data_row.tx_raw = TxRawPos(tx_dest_pos=parser.in_header.index("Wallet Address"))
    else:
        data_row.tx_raw = TxRawPos(tx_dest_pos=parser.in_header.index("Wallet Address/Account"))

    data_row.t_record = TransactionOutRecord(
        TrType.WITHDRAWAL,
        data_row.timestamp,
        sell_quantity=Decimal(row_dict["Amount"]),
        sell_asset=row_dict["Coin"],
        wallet=WALLET,
        note=row_dict["Remark"],
    )


def parse_kucoin_deposits_withdrawals_crypto_v2(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict

    if parser.args:
        timestamp_hdr = parser.args[0].group(1)
        utc_offset = parser.args[0].group(2)
        data_row.timestamp = DataParser.parse_timestamp(f"{row_dict[timestamp_hdr]} {utc_offset}")
    else:
        data_row.timestamp = DataParser.parse_timestamp(row_dict["Time"], tz="Asia/Singapore")

    if row_dict["Status"] != "SUCCESS":
        return

    tx_hash_pos = None
    if "Hash" in row_dict:
        tx_hash_pos = parser.in_header.index("Hash")

    if "Withdrawal Address/Account" in row_dict:
        data_row.tx_raw = TxRawPos(
            tx_hash_pos, tx_dest_pos=parser.in_header.index("Withdrawal Address/Account")
        )
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Amount"]),
            sell_asset=row_dict["Coin"],
            fee_quantity=Decimal(row_dict["Fee"]) if row_dict["Fee"] else Decimal(0),
            fee_asset=row_dict["Coin"],
            wallet=WALLET,
            note=row_dict["Remarks"],
        )
    else:
        tx_dest_pos = None
        if "Deposit Address" in row_dict:
            tx_dest_pos = parser.in_header.index("Deposit Address")

        data_row.tx_raw = TxRawPos(tx_hash_pos, tx_dest_pos=tx_dest_pos)
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Coin"],
            fee_quantity=Decimal(row_dict["Fee"]) if row_dict["Fee"] else Decimal(0),
            fee_asset=row_dict["Coin"],
            wallet=WALLET,
        )


def parse_kucoin_staking_income(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict

    timestamp_hdr = parser.args[0].group(1)
    utc_offset = parser.args[0].group(2)
    data_row.timestamp = DataParser.parse_timestamp(f"{row_dict[timestamp_hdr]} {utc_offset}")

    data_row.t_record = TransactionOutRecord(
        TrType.STAKING,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Amount"]),
        buy_asset=row_dict["Earnings Coin"],
        wallet=WALLET,
    )


def parse_kucoin_futures(
    data_rows: List["DataRow"], parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    for row_index, data_row in enumerate(data_rows):
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f"row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if data_row.parsed:
            continue

        try:
            _parse_kucoin_futures_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_kucoin_futures_row(
    data_rows: List["DataRow"],
    parser: DataParser,
    data_row: "DataRow",
    row_index: int,
) -> None:
    row_dict = data_row.row_dict
    timestamp_hdr = parser.args[1].group(1)
    utc_offset = parser.args[1].group(2)
    data_row.timestamp = DataParser.parse_timestamp(f"{row_dict[timestamp_hdr]} {utc_offset}")
    data_row.parsed = True
    asset = _get_asset_from_symbol(row_dict["Symbol"])
    total_fees = Decimal(row_dict["Total Funding Fees"]) - Decimal(row_dict["Total Trading Fees"])

    if Decimal(row_dict["Realized PNL"]) - total_fees > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_GAIN,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Realized PNL"]) - total_fees,
            buy_asset=asset,
            wallet=WALLET,
            note=row_dict["Symbol"],
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_LOSS,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Realized PNL"]) - total_fees),
            sell_asset=asset,
            wallet=WALLET,
            note=row_dict["Symbol"],
        )

    dup_data_row = copy.copy(data_row)
    dup_data_row.row = []

    if total_fees > 0:
        dup_data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE_REBATE,
            data_row.timestamp,
            buy_quantity=total_fees,
            buy_asset=asset,
            wallet=WALLET,
            note=row_dict["Symbol"],
        )
    else:
        dup_data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=abs(total_fees),
            sell_asset=asset,
            wallet=WALLET,
            note=row_dict["Symbol"],
        )

    data_rows.insert(row_index + 1, dup_data_row)


def _get_asset_from_symbol(symbol: str) -> str:
    if symbol.endswith("USDTM"):
        asset = "USDT"
    elif symbol.endswith("USDCM"):
        asset = "USDC"
    elif symbol.endswith("USDM"):
        asset = symbol[:-4]
    elif symbol.startswith("XBT"):
        # Special case for symbols such as XBTMM23, XBTMU24
        asset = "XBT"
    else:
        raise RuntimeError(f"Unexpected symbol: {symbol}")

    if asset == "XBT":
        return "BTC"
    return asset


# This parser is only used for Airdrops, everything else is duplicates
def parse_kucoin_account_history_funding(
    data_row: "DataRow", parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    if "History_Funding" not in kwargs["filename"]:
        # Only the Funding Account can contain airdrops
        raise DataFormatNotSupported(kwargs["filename"])

    row_dict = data_row.row_dict

    timestamp_hdr = parser.args[0].group(1)
    utc_offset = parser.args[0].group(2)
    data_row.timestamp = DataParser.parse_timestamp(f"{row_dict[timestamp_hdr]} {utc_offset}")

    if "Distribution" in row_dict["Remark"]:
        data_row.t_record = TransactionOutRecord(
            TrType.AIRDROP,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Amount"]),
            buy_asset=row_dict["Currency"],
            wallet=WALLET,
        )


def parse_kucoin_deposits_fiat(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict

    if row_dict["Status"] != "SUCCEEDED":
        return

    timestamp_hdr = parser.args[0].group(1)
    utc_offset = parser.args[0].group(2)
    data_row.timestamp = DataParser.parse_timestamp(f"{row_dict[timestamp_hdr]} {utc_offset}")

    data_row.t_record = TransactionOutRecord(
        TrType.DEPOSIT,
        data_row.timestamp,
        buy_quantity=Decimal(row_dict["Fiat Amount"]),
        buy_asset=row_dict["Currency (Fiat)"],
        fee_quantity=Decimal(row_dict["Fee"]),
        fee_asset=row_dict["Currency (Fiat)"],
        wallet=WALLET,
    )


DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "oid",
        "symbol",
        "dealPrice",
        "dealValue",
        "amount",
        "fee",
        "direction",
        "createdDate",
        "",
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v4,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "tradeCreatedAt",
        "orderId",
        "symbol",
        "side",
        "price",
        "size",
        "funds",
        "fee",
        "liquidity",
        "feeCurrency",
        "orderType",
        "",
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v3,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "tradeCreatedAt",
        "orderId",
        "symbol",
        "side",
        "price",
        "size",
        "funds",
        "fee",
        "liquidity",
        "feeCurrency",
        "orderType",
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v3,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "uid",
        "symbol",
        "order_type",
        "price",
        "amount_coin",
        "direction",
        "funds",
        "fee",
        "created_at",
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    ["uid", "symbol", "direction", "deal_price", "amount", "deal_value", "created_at"],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Deposits",
    ["Time", "Coin", "Network", "Amount", "Type", "Remark", "Fee"],
    worksheet_name="KuCoin D",
    row_handler=parse_kucoin_deposits_crypto,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Deposits",
    ["Time", "Coin", "Amount", "Type", "Remark"],
    worksheet_name="KuCoin D",
    row_handler=parse_kucoin_deposits_crypto,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Withdrawals",
    ["Time", "Coin", "Network", "Amount", "Type", "Wallet Address/Account", "Remark"],
    worksheet_name="KuCoin W",
    row_handler=parse_kucoin_withdrawals_crypto,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Withdrawals",
    ["Time", "Coin", "Amount", "Type", "Wallet Address", "Remark"],
    worksheet_name="KuCoin W",
    row_handler=parse_kucoin_withdrawals_crypto,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Deposits/Withdrawals",
    ["coin_type", "type", "add", "hash", "vol", "created_at"],
    worksheet_name="KuCoin D,W",
    row_handler=parse_kucoin_deposits_withdrawals_crypto_v1,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Deposits",
    [
        "UID",
        "Account Type",
        lambda c: re.match(r"(^Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Coin",
        "Amount",
        "Fee",
        "Transfer Network",
        "Status",
        "Remarks",
    ],
    worksheet_name="KuCoin D,W",
    row_handler=parse_kucoin_deposits_withdrawals_crypto_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Deposits",
    [
        "UID",
        "Account Type",
        lambda c: re.match(r"(^Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Coin",
        "Amount",
        "Fee",
        "Hash",
        "Deposit Address",
        "Transfer Network",
        "Status",
        "Remarks",
    ],
    worksheet_name="KuCoin D,W",
    row_handler=parse_kucoin_deposits_withdrawals_crypto_v2,
)

# Deposit_Withdrawal History_Deposit History (Bundle)
DataParser(
    ParserType.EXCHANGE,
    "KuCoin Deposits",
    [
        "UID",
        "Account Type",
        lambda c: re.match(r"(^Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Remarks",
        "Status",
        "Fee",
        "Amount",
        "Coin",
        "Transfer Network",
    ],
    worksheet_name="KuCoin D,W",
    row_handler=parse_kucoin_deposits_withdrawals_crypto_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Withdrawals",
    [
        "UID",
        "Account Type",
        lambda c: re.match(r"(^Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Coin",
        "Amount",
        "Fee",
        "Withdrawal Address/Account",
        "Transfer Network",
        "Status",
        "Remarks",
    ],
    worksheet_name="KuCoin D,W",
    row_handler=parse_kucoin_deposits_withdrawals_crypto_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Withdrawals",
    [
        "UID",
        "Account Type",
        lambda c: re.match(r"(^Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Coin",
        "Amount",
        "Fee",
        "Hash",
        "Withdrawal Address/Account",
        "Transfer Network",
        "Status",
        "Remarks",
    ],
    worksheet_name="KuCoin D,W",
    row_handler=parse_kucoin_deposits_withdrawals_crypto_v2,
)

# Deposit_Withdrawal History_Withdrawal Record (Bundle)
DataParser(
    ParserType.EXCHANGE,
    "KuCoin Withdrawals",
    [
        "UID",
        "Account Type",
        "Time",
        "Coin",
        "Amount",
        "Fee",
        "Withdrawal Address/Account",
        "Transfer Network",
        "Status",
        "Remarks",
    ],
    worksheet_name="KuCoin D,W",
    row_handler=parse_kucoin_deposits_withdrawals_crypto_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Withdrawals",
    [
        "UID",
        "Account Type",
        lambda c: re.match(r"(^Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Remarks",
        "Status",
        "Fee",
        "Amount",
        "Coin",
        "Transfer Network",
        "Withdrawal Address/Account",
    ],
    worksheet_name="KuCoin D,W",
    row_handler=parse_kucoin_deposits_withdrawals_crypto_v2,
)

# Earn Orders_Profit History (Bundle)
DataParser(
    ParserType.EXCHANGE,
    "KuCoin Staking",
    [
        "UID",
        "Account Type",
        "Order ID",
        lambda c: re.match(r"(^Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Staked Coin",
        "Product Type",
        "Product Name",
        "Earnings Coin",
        "Earnings Type",
        "Remarks",
        "Amount",
        "Amount（USDT）",
        "Fee",
    ],
    worksheet_name="KuCoin S",
    row_handler=parse_kucoin_staking_income,
)

# Futures Orders_Realized PNL (Bundle)
DataParser(
    ParserType.EXCHANGE,
    "KuCoin Bundle Futures Orders Realized PNL",
    [
        "UID",
        "Account Type",
        "Symbol",
        "Close Type",
        "Realized PNL",
        "Total Realized PNL",
        "Total Funding Fees",
        "Total Trading Fees",
        lambda c: re.match(r"(^Position Opening Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        lambda c: re.match(r"(^,?Position Closing Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
    ],
    worksheet_name="Kucoin F",
    all_handler=parse_kucoin_futures,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Account History",
    [
        "UID",
        "Account Type",
        "Currency",
        "Side",
        "Amount",
        "Fee",
        lambda c: re.match(r"(^Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Remark",
        "Type",  # New field
    ],
    worksheet_name="KuCoin A",
    row_handler=parse_kucoin_account_history_funding,
)

# Account History_Funding Account (Bundle)
DataParser(
    ParserType.EXCHANGE,
    "KuCoin Account History",
    [
        "UID",
        "Account Type",
        "Currency",
        "Side",
        "Amount",
        "Fee",
        lambda c: re.match(r"(^Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Remark",
    ],
    worksheet_name="KuCoin A",
    row_handler=parse_kucoin_account_history_funding,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "UID",
        "Account Type",
        "Order ID",
        "Symbol",
        "Side",
        "Order Type",
        "Avg. Filled Price",
        "Filled Amount",
        "Filled Volume",
        "Filled Volume (USDT)",
        lambda c: re.match(r"(^Filled Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Fee",
        "Tax",
        "Maker/Taker",
        "Fee Currency",
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v5,
)

# Spot Orders_Filled Orders (Bundle)
DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "UID",
        "Account Type",
        "Order ID",
        "Symbol",
        "Side",
        "Order Type",
        "Avg. Filled Price",
        "Filled Amount",
        "Filled Volume",
        "Filled Volume (USDT)",
        "Filled Time",
        "Fee",
        "Tax",
        "Maker/Taker",
        "Fee Currency",
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v5,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "UID",
        "Account Type",
        "Order ID",
        lambda c: re.match(r"(^Order Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Symbol",
        "Side",
        "Order Type",
        "Order Price",
        "Order Amount",
        "Avg. Filled Price",
        "Filled Amount",
        "Filled Volume",
        "Filled Volume (USDT)",
        lambda c: re.match(r"(^Filled Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Fee",
        "Fee Currency",
        "Tax",  # New field
        "Status",
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v5,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "UID",
        "Account Type",
        "Order ID",
        lambda c: re.match(r"(^Order Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Symbol",
        "Side",
        "Order Type",
        "Order Price",
        "Order Amount",
        "Avg. Filled Price",
        "Filled Amount",
        "Filled Volume",
        "Filled Volume (USDT)",
        lambda c: re.match(r"(^Filled Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
        "Fee",
        "Fee Currency",
        "Status",
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_trades_v5,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "Order ID",
        "Order Type",
        "Currency (Crypto)",
        "Crypto Quantity,",
        "Price",
        "Currency (Fiat)",
        "Fiat Amount",
        "Fee Currency",
        "Fee",
        "Status",
        lambda c: re.match(r"(^Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_fiat_trades,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Trades",
    [
        "Order ID",
        "Currency (Crypto)",
        "Crypto Quantity",
        "Currency (Fiat)",
        "Fiat Amount",
        "Fee Currency (Fiat)",
        "Fee (Fiat)",
        "Fee Currency (Crypto)",
        "Fee (Crypto)",
        "Payment Method",
        "Status",
        lambda c: re.match(r"(^Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
    ],
    worksheet_name="KuCoin T",
    row_handler=parse_kucoin_fiat_trades_v2,
)

DataParser(
    ParserType.EXCHANGE,
    "KuCoin Deposits",
    [
        "Order ID",
        "Currency (Fiat)",
        "Fiat Amount",
        "Fee",
        "Deposit Method",
        "Status",
        lambda c: re.match(r"(^Time\((UTC|UTC[-+]\d{2}:\d{2})\))", c),
    ],
    worksheet_name="KuCoin D",
    row_handler=parse_kucoin_deposits_fiat,
)
