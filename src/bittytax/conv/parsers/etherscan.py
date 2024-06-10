# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ...constants import WARNING
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import DataFilenameError, DataRowError, UnknownCryptoassetError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow


def parse_etherscan(data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("Txhash"),
        parser.in_header.index("From"),
        parser.in_header.index("To"),
    )

    # Skip over any args which are not regex
    matches = [arg for arg in parser.args if isinstance(arg, re.Match)]

    value_in_hdr = matches[0].group(1)
    buy_asset = matches[0].group(2)
    value_out_hdr = matches[1].group(1)
    sell_asset = matches[1].group(2)
    txn_fee_hdr = matches[2].group(1)
    fee_asset = matches[2].group(2)

    if row_dict["Status"] != "":
        # Failed transactions should not have a Value_OUT
        row_dict[value_out_hdr] = "0"

    if Decimal(row_dict[value_in_hdr]) > 0:
        if row_dict["Status"] == "":
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict[value_in_hdr]),
                buy_asset=buy_asset,
                wallet=_get_wallet(fee_asset, row_dict["To"]),
                note=_get_note(row_dict),
            )
    elif Decimal(row_dict[value_out_hdr]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict[value_out_hdr]),
            sell_asset=sell_asset,
            fee_quantity=Decimal(row_dict[txn_fee_hdr]),
            fee_asset=fee_asset,
            wallet=_get_wallet(fee_asset, row_dict["From"]),
            note=_get_note(row_dict),
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict[value_out_hdr]),
            sell_asset=sell_asset,
            fee_quantity=Decimal(row_dict[txn_fee_hdr]),
            fee_asset=fee_asset,
            wallet=_get_wallet(fee_asset, row_dict["From"]),
            note=_get_note(row_dict),
        )


def _get_wallet(chain: str, address: str) -> str:
    return f"{chain}-{address.lower()[0 : TransactionOutRecord.WALLET_ADDR_LEN]}"


def _get_note(row_dict: Dict[str, str]) -> str:
    if row_dict["Status"] != "":
        if row_dict.get("Method"):
            return f'Failure ({row_dict["Method"]})'
        return "Failure"

    if row_dict.get("Method"):
        return row_dict["Method"]

    return row_dict.get("PrivateNote", "")


def parse_etherscan_internal(
    data_row: "DataRow", parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("Txhash"),
        parser.in_header.index("From"),
        parser.in_header.index("TxTo"),
    )

    # Skip over any args which are not matches
    matches = [arg for arg in parser.args if isinstance(arg, re.Match)]

    value_in_hdr = matches[1].group(1)
    buy_asset = matches[1].group(2)
    value_out_hdr = matches[2].group(1)
    sell_asset = matches[2].group(2)

    # Failed internal transaction
    if row_dict["Status"] != "0":
        return

    if Decimal(row_dict[value_in_hdr]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict[value_in_hdr]),
            buy_asset=buy_asset,
            wallet=_get_wallet(buy_asset, row_dict["TxTo"]),
        )
    elif Decimal(row_dict[value_out_hdr]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict[value_out_hdr]),
            sell_asset=sell_asset,
            wallet=_get_wallet(sell_asset, row_dict["From"]),
        )


def parse_etherscan_tokens(
    data_rows: List["DataRow"], parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    symbol = kwargs["cryptoasset"]
    if not symbol:
        sys.stderr.write(f"{WARNING} Native cryptoasset for this chain cannot be identified\n")
        sys.stderr.write(f"{Fore.RESET}Enter symbol: ")
        symbol = input()
        if not symbol:
            raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet", ""))

    for data_row in data_rows:
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f" row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if data_row.parsed:
            continue

        try:
            _parse_etherscan_tokens_row(data_row, parser, symbol, **kwargs)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_etherscan_tokens_row(
    data_row: "DataRow", _parser: DataParser, symbol: str, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("Txhash"),
        parser.in_header.index("From"),
        parser.in_header.index("To"),
    )

    if row_dict["TokenSymbol"].endswith("-LP"):
        asset = row_dict["TokenSymbol"] + "-" + row_dict["ContractAddress"][0:10]
    else:
        asset = row_dict["TokenSymbol"]

    if "Value" in row_dict:
        quantity = Decimal(row_dict["Value"].replace(",", ""))
    else:
        quantity = Decimal(row_dict["TokenValue"].replace(",", ""))

    if row_dict["To"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=quantity,
            buy_asset=asset,
            wallet=_get_wallet(symbol, row_dict["To"]),
        )
    elif row_dict["From"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=quantity,
            sell_asset=asset,
            wallet=_get_wallet(symbol, row_dict["From"]),
        )
    else:
        raise DataFilenameError(kwargs["filename"], "Ethereum address")


def parse_etherscan_nfts(
    data_rows: List["DataRow"], parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    symbol = kwargs["cryptoasset"]
    if not symbol:
        sys.stderr.write(f"{WARNING} Native cryptoasset for this chain cannot be identified\n")
        sys.stderr.write(f"{Fore.RESET}Enter symbol: ")
        symbol = input()
        if not symbol:
            raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet", ""))

    for data_row in data_rows:
        if config.debug:
            if parser.in_header_row_num is None:
                raise RuntimeError("Missing in_header_row_num")

            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f" row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if data_row.parsed:
            continue

        try:
            _parse_etherscan_nfts_row(data_row, parser, symbol, **kwargs)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_etherscan_nfts_row(
    data_row: "DataRow", _parser: DataParser, symbol: str, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))
    data_row.tx_raw = TxRawPos(
        parser.in_header.index("Txhash"),
        parser.in_header.index("From"),
        parser.in_header.index("To"),
    )

    if "TokenId" in row_dict:
        row_dict["Token ID"] = row_dict["TokenId"]

    if row_dict["To"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(1),
            buy_asset=f'{row_dict["TokenName"]} #{row_dict["Token ID"]}',
            wallet=_get_wallet(symbol, row_dict["To"]),
        )
    elif row_dict["From"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(1),
            sell_asset=f'{row_dict["TokenName"]} #{row_dict["Token ID"]}',
            wallet=_get_wallet(symbol, row_dict["From"]),
        )
    else:
        raise DataFilenameError(kwargs["filename"], "Ethereum address")


etherscan_txns = DataParser(
    ParserType.EXPLORER,
    "Etherscan (Transactions)",
    [
        lambda c: c in ("Txhash", "Transaction Hash"),  # Renamed
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),  # Renamed
        "From",
        "To",
        "ContractAddress",
        lambda c: re.match(r"(Value_IN\((\w+)\)?)", c),
        lambda c: re.match(r"(Value_OUT\((\w+)\)?)", c),
        None,
        lambda c: re.match(r"(TxnFee\((\w+)\)?)", c),
        "TxnFee(USD)",
        lambda c: re.match(r"Historical \$Price\/(\w+)", c),
        "Status",
        "ErrCode",
        "Method",  # New field
    ],
    worksheet_name="Etherscan",
    row_handler=parse_etherscan,
)

DataParser(
    ParserType.EXPLORER,
    "Etherscan (Transactions)",
    [
        lambda c: c in ("Txhash", "Transaction Hash"),  # Renamed
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),  # Renamed
        "From",
        "To",
        "ContractAddress",
        lambda c: re.match(r"(Value_IN\((\w+)\)?)", c),
        lambda c: re.match(r"(Value_OUT\((\w+)\)?)", c),
        None,
        lambda c: re.match(r"(TxnFee\((\w+)\)?)", c),
        "TxnFee(USD)",
        lambda c: re.match(r"Historical \$Price\/(\w+)", c),
        "Status",
        "ErrCode",
        "Method",  # New field
        "PrivateNote",
    ],
    worksheet_name="Etherscan",
    row_handler=parse_etherscan,
)

DataParser(
    ParserType.EXPLORER,
    "Etherscan (Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime",
        "From",
        "To",
        "ContractAddress",
        lambda c: re.match(r"(Value_IN\((\w+)\)?)", c),
        lambda c: re.match(r"(Value_OUT\((\w+)\)?)", c),
        None,
        lambda c: re.match(r"(TxnFee\((\w+)\)?)", c),
        "TxnFee(USD)",
        lambda c: re.match(r"Historical \$Price\/(\w+)", c),
        "Status",
        "ErrCode",
    ],
    worksheet_name="Etherscan",
    row_handler=parse_etherscan,
)

DataParser(
    ParserType.EXPLORER,
    "Etherscan (Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime",
        "From",
        "To",
        "ContractAddress",
        lambda c: re.match(r"(Value_IN\((\w+)\)?)", c),
        lambda c: re.match(r"(Value_OUT\((\w+)\)?)", c),
        None,
        lambda c: re.match(r"(TxnFee\((\w+)\)?)", c),
        "TxnFee(USD)",
        lambda c: re.match(r"Historical \$Price\/(\w+)", c),
        "Status",
        "ErrCode",
        "PrivateNote",
    ],
    worksheet_name="Etherscan",
    row_handler=parse_etherscan,
)

etherscan_int = DataParser(
    ParserType.EXPLORER,
    "Etherscan (Internal Transactions)",
    [
        lambda c: c in ("Txhash", "Transaction Hash"),  # Renamed
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),  # Renamed
        "ParentTxFrom",
        "ParentTxTo",
        lambda c: re.match(r"ParentTx(\w+)_Value", c),
        "From",
        "TxTo",
        "ContractAddress",
        lambda c: re.match(r"(Value_IN\((\w+)\)?)", c),
        lambda c: re.match(r"(Value_OUT\((\w+)\)?)", c),
        None,
        lambda c: re.match(r"Historical \$Price\/(\w+)", c),
        "Status",
        "ErrCode",
        "Type",
    ],
    worksheet_name="Etherscan",
    row_handler=parse_etherscan_internal,
)

DataParser(
    ParserType.EXPLORER,
    "Etherscan (Internal Transactions)",
    [
        lambda c: c in ("Txhash", "Transaction Hash"),  # Renamed
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),  # Renamed
        "ParentTxFrom",
        "ParentTxTo",
        lambda c: re.match(r"ParentTx(\w+)_Value", c),
        "From",
        "TxTo",
        "ContractAddress",
        lambda c: re.match(r"(Value_IN\((\w+)\)?)", c),
        lambda c: re.match(r"(Value_OUT\((\w+)\)?)", c),
        None,
        lambda c: re.match(r"Historical \$Price\/(\w+)", c),
        "Status",
        "ErrCode",
        "Type",
        "PrivateNote",
    ],
    worksheet_name="Etherscan",
    row_handler=parse_etherscan_internal,
)

etherscan_tokens = DataParser(
    ParserType.EXPLORER,
    "Etherscan (Token Transfers ERC-20)",
    [
        lambda c: c in ("Txhash", "Transaction Hash"),  # Renamed
        "Blockno",  # New field
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),  # Renamed
        "From",
        "To",
        "TokenValue",  # Renamed
        "USDValueDayOfTx",  # New field
        "ContractAddress",  # New field
        "TokenName",
        "TokenSymbol",
    ],
    worksheet_name="Etherscan",
    all_handler=parse_etherscan_tokens,
)

DataParser(
    ParserType.EXPLORER,
    "Etherscan (Token Transfers ERC-20)",
    [
        "Txhash",
        "UnixTimestamp",
        "DateTime",
        "From",
        "To",
        "Value",
        "ContractAddress",
        "TokenName",
        "TokenSymbol",
    ],
    worksheet_name="Etherscan",
    all_handler=parse_etherscan_tokens,
)

etherscan_nfts = DataParser(
    ParserType.EXPLORER,
    "Etherscan (NFT Transfers ERC-721 & ERC-1155)",
    [
        lambda c: c in ("Txhash", "Transaction Hash"),  # Renamed
        "Blockno",
        "UnixTimestamp",
        "DateTime (UTC)",  # Renamed
        "From",
        "To",
        "ContractAddress",
        # "TokenId",
        "TokenName",
        "TokenSymbol",
        "Token ID",  # Moved/Renamed
        "Type",  # New field
        "Quantity",  # New field
    ],
    worksheet_name="Etherscan",
    all_handler=parse_etherscan_nfts,
)

DataParser(
    ParserType.EXPLORER,
    "Etherscan (NFT Transfers ERC-721 & ERC-1155)",
    [
        "Txhash",
        "Blockno",  # New field
        "UnixTimestamp",
        "DateTime",
        "From",
        "To",
        "ContractAddress",
        "TokenId",
        "TokenName",
        "TokenSymbol",
    ],
    worksheet_name="Etherscan",
    all_handler=parse_etherscan_nfts,
)

DataParser(
    ParserType.EXPLORER,
    "Etherscan (NFT Transfers ERC-721 & ERC-1155)",
    [
        "Txhash",
        "UnixTimestamp",
        "DateTime",
        "From",
        "To",
        "ContractAddress",
        "TokenId",
        "TokenName",
        "TokenSymbol",
    ],
    worksheet_name="Etherscan",
    all_handler=parse_etherscan_nfts,
)
