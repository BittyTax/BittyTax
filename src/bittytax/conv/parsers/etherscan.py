# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal
from typing import TYPE_CHECKING, Dict

from typing_extensions import Unpack

from ...bt_types import TrType
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataFilenameError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

WALLET = "Ethereum"


def parse_etherscan(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))

    if row_dict["Status"] != "":
        # Failed transactions should not have a Value_OUT
        row_dict["Value_OUT(ETH)"] = "0"

    if Decimal(row_dict["Value_IN(ETH)"]) > 0:
        if row_dict["Status"] == "":
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Value_IN(ETH)"]),
                buy_asset="ETH",
                wallet=_get_wallet(row_dict["To"]),
                note=_get_note(row_dict),
            )
    elif Decimal(row_dict["Value_OUT(ETH)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(ETH)"]),
            sell_asset="ETH",
            fee_quantity=Decimal(row_dict["TxnFee(ETH)"]),
            fee_asset="ETH",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(ETH)"]),
            sell_asset="ETH",
            fee_quantity=Decimal(row_dict["TxnFee(ETH)"]),
            fee_asset="ETH",
            wallet=_get_wallet(row_dict["From"]),
            note=_get_note(row_dict),
        )


def _get_wallet(address: str) -> str:
    return f"{WALLET}-{address.lower()[0 : TransactionOutRecord.WALLET_ADDR_LEN]}"


def _get_note(row_dict: Dict[str, str]) -> str:
    if row_dict["Status"] != "":
        if row_dict.get("Method"):
            return f'Failure ({row_dict["Method"]})'
        return "Failure"

    if row_dict.get("Method"):
        return row_dict["Method"]

    return row_dict.get("PrivateNote", "")


def parse_etherscan_internal(
    data_row: "DataRow", _parser: DataParser, **_kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))

    # Failed internal transaction
    if row_dict["Status"] != "0":
        return

    if Decimal(row_dict["Value_IN(ETH)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Value_IN(ETH)"]),
            buy_asset="ETH",
            wallet=_get_wallet(row_dict["TxTo"]),
        )
    elif Decimal(row_dict["Value_OUT(ETH)"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(row_dict["Value_OUT(ETH)"]),
            sell_asset="ETH",
            wallet=_get_wallet(row_dict["From"]),
        )


def parse_etherscan_tokens(
    data_row: "DataRow", _parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))

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
            wallet=_get_wallet(row_dict["To"]),
        )
    elif row_dict["From"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=quantity,
            sell_asset=asset,
            wallet=_get_wallet(row_dict["From"]),
        )
    else:
        raise DataFilenameError(kwargs["filename"], "Ethereum address")


def parse_etherscan_nfts(
    data_row: "DataRow", _parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(int(row_dict["UnixTimestamp"]))

    if "TokenId" in row_dict:
        row_dict["Token ID"] = row_dict["TokenId"]

    if row_dict["To"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(1),
            buy_asset=f'{row_dict["TokenName"]} #{row_dict["Token ID"]}',
            wallet=_get_wallet(row_dict["To"]),
        )
    elif row_dict["From"].lower() in kwargs["filename"].lower():
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=Decimal(1),
            sell_asset=f'{row_dict["TokenName"]} #{row_dict["Token ID"]}',
            wallet=_get_wallet(row_dict["From"]),
        )
    else:
        raise DataFilenameError(kwargs["filename"], "Ethereum address")


etherscan_txns = DataParser(
    ParserType.EXPLORER,
    "Etherscan (ETH Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),
        "From",
        "To",
        "ContractAddress",
        "Value_IN(ETH)",
        "Value_OUT(ETH)",
        None,
        "TxnFee(ETH)",
        "TxnFee(USD)",
        "Historical $Price/Eth",
        "Status",
        "ErrCode",
        "Method",
    ],
    worksheet_name="Etherscan",
    row_handler=parse_etherscan,
)

DataParser(
    ParserType.EXPLORER,
    "Etherscan (ETH Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),
        "From",
        "To",
        "ContractAddress",
        "Value_IN(ETH)",
        "Value_OUT(ETH)",
        None,
        "TxnFee(ETH)",
        "TxnFee(USD)",
        "Historical $Price/Eth",
        "Status",
        "ErrCode",
        "Method",
        "PrivateNote",
    ],
    worksheet_name="Etherscan",
    row_handler=parse_etherscan,
)

DataParser(
    ParserType.EXPLORER,
    "Etherscan (ETH Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime",
        "From",
        "To",
        "ContractAddress",
        "Value_IN(ETH)",
        "Value_OUT(ETH)",
        None,
        "TxnFee(ETH)",
        "TxnFee(USD)",
        "Historical $Price/Eth",
        "Status",
        "ErrCode",
    ],
    worksheet_name="Etherscan",
    row_handler=parse_etherscan,
)

DataParser(
    ParserType.EXPLORER,
    "Etherscan (ETH Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        "DateTime",
        "From",
        "To",
        "ContractAddress",
        "Value_IN(ETH)",
        "Value_OUT(ETH)",
        None,
        "TxnFee(ETH)",
        "TxnFee(USD)",
        "Historical $Price/Eth",
        "Status",
        "ErrCode",
        "PrivateNote",
    ],
    worksheet_name="Etherscan",
    row_handler=parse_etherscan,
)

etherscan_int = DataParser(
    ParserType.EXPLORER,
    "Etherscan (ETH Internal Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),
        "ParentTxFrom",
        "ParentTxTo",
        "ParentTxETH_Value",
        "From",
        "TxTo",
        "ContractAddress",
        "Value_IN(ETH)",
        "Value_OUT(ETH)",
        None,
        "Historical $Price/Eth",
        "Status",
        "ErrCode",
        "Type",
    ],
    worksheet_name="Etherscan",
    row_handler=parse_etherscan_internal,
)

DataParser(
    ParserType.EXPLORER,
    "Etherscan (ETH Internal Transactions)",
    [
        "Txhash",
        "Blockno",
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),
        "ParentTxFrom",
        "ParentTxTo",
        "ParentTxETH_Value",
        "From",
        "TxTo",
        "ContractAddress",
        "Value_IN(ETH)",
        "Value_OUT(ETH)",
        None,
        "Historical $Price/Eth",
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
        "Txhash",
        "Blockno",  # New field
        "UnixTimestamp",
        lambda c: c in ("DateTime", "DateTime (UTC)"),
        "From",
        "To",
        "TokenValue",  # Renamed
        "USDValueDayOfTx",  # New field
        "ContractAddress",  # New field
        "TokenName",
        "TokenSymbol",
    ],
    worksheet_name="Etherscan",
    row_handler=parse_etherscan_tokens,
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
    row_handler=parse_etherscan_tokens,
)

etherscan_nfts = DataParser(
    ParserType.EXPLORER,
    "Etherscan (NFT Transfers ERC-721 & ERC-1155)",
    [
        "Txhash",
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
    row_handler=parse_etherscan_nfts,
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
    row_handler=parse_etherscan_nfts,
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
    row_handler=parse_etherscan_nfts,
)
