# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

import copy
import json
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ..dataparser import DataParser, ParserArgs, ParserType
from ..exceptions import DataRowError, UnexpectedContentError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

PRECISION = Decimal("0." + "0" * 18)

WALLET = "Ethereum"


def parse_zerion(
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
            _parse_zerion_row(data_rows, parser, data_row, row_index)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_zerion_row(
    data_rows: List["DataRow"], parser: DataParser, data_row: "DataRow", row_index: int
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(
        row_dict["Date"] + " " + row_dict["Time"], tz=config.local_timezone
    )
    data_row.parsed = True

    fee_quantity, fee_asset, fee_value = _get_data(
        data_row, "Fee Amount", "Fee Currency", "Fee Fiat Amount", "Fee Fiat Currency"
    )

    if row_dict["Status"] != "Confirmed":
        data_row.t_record = TransactionOutRecord(
            TrType.SPEND,
            data_row.timestamp,
            sell_quantity=Decimal(0),
            sell_asset=fee_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            fee_value=fee_value,
            wallet=WALLET,
        )
        return

    changes = json.loads(row_dict["Changes JSON"])
    t_ins = [t for t in changes if t["type"] == "in"]
    t_outs = [t for t in changes if t["type"] == "out"]

    if row_dict["Accounting Type"] == "Income":
        if len(t_ins) > 1:
            _do_zerion_multi_deposit(data_row, data_rows, row_index, t_ins)
        else:
            buy_quantity, buy_asset, buy_value = _get_data(
                data_row,
                "Buy Amount",
                "Buy Currency",
                "Buy Fiat Amount",
                "Buy Fiat Currency",
                t_ins,
            )

            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=buy_quantity,
                buy_asset=buy_asset,
                buy_value=buy_value,
                fee_quantity=fee_quantity,
                fee_asset=fee_asset,
                fee_value=fee_value,
                wallet=WALLET,
            )
    elif row_dict["Accounting Type"] == "Spend":
        if len(t_outs) > 1:
            _do_zerion_multi_withdrawal(data_row, data_rows, row_index, t_outs)
        else:
            sell_quantity, sell_asset, sell_value = _get_data(
                data_row,
                "Sell Amount",
                "Sell Currency",
                "Sell Fiat Amount",
                "Sell Fiat Currency",
                t_outs,
            )

            if sell_quantity is None and fee_quantity is None:
                return

            # If a Spend only contains fees, we must include a sell of zero
            if sell_quantity is None:
                sell_quantity = Decimal(0)
                sell_asset = fee_asset

            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=sell_quantity,
                sell_asset=sell_asset,
                sell_value=sell_value,
                fee_quantity=fee_quantity,
                fee_asset=fee_asset,
                fee_value=fee_value,
                wallet=WALLET,
            )
    elif row_dict["Accounting Type"] == "Trade":
        if len(t_ins) == 1:
            # Multi-sell or normal Trade
            _do_zerion_multi_sell(data_row, data_rows, row_index, t_ins, t_outs)
        elif len(t_outs) == 1:
            # Multi-buy
            _do_zerion_multi_buy(data_row, data_rows, row_index, t_ins, t_outs)
        else:
            # Multi-sell to Multi-buy trade not supported
            raise UnexpectedContentError(
                parser.in_header.index("Changes JSON"),
                "Changes JSON",
                row_dict["Changes JSON"],
            )
    else:
        raise UnexpectedTypeError(
            parser.in_header.index("Accounting Type"),
            "Accounting Type",
            row_dict["Accounting Type"],
        )


def _do_zerion_multi_deposit(
    data_row: "DataRow", data_rows: List["DataRow"], row_index: int, t_ins: List[Any]
) -> None:
    for cnt, t_in in enumerate(t_ins):
        buy_quantity, buy_asset, buy_value = _get_data_json(data_row, t_in)
        t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=buy_value,
            wallet=WALLET,
        )

        if not data_row.t_record:
            data_row.t_record = t_record
        else:
            dup_data_row = copy.copy(data_row)
            dup_data_row.row = []
            dup_data_row.t_record = t_record
            data_rows.insert(row_index + cnt, dup_data_row)


def _do_zerion_multi_withdrawal(
    data_row: "DataRow", data_rows: List["DataRow"], row_index: int, t_outs: List[Any]
) -> None:
    fee_quantity, fee_asset, fee_value = _get_data(
        data_row, "Fee Amount", "Fee Currency", "Fee Fiat Amount", "Fee Fiat Currency"
    )
    tot_fee_quantity = Decimal(0)

    for cnt, t_out in enumerate(t_outs):
        sell_quantity, sell_asset, sell_value = _get_data_json(data_row, t_out)

        if fee_quantity:
            split_fee_value = fee_value / len(t_outs) if fee_value else None

            if cnt < len(t_outs) - 1:
                split_fee_quantity = Decimal(fee_quantity / len(t_outs)).quantize(PRECISION)
                tot_fee_quantity += split_fee_quantity
            else:
                # Last t_out, use up remainder
                split_fee_quantity = fee_quantity - tot_fee_quantity
        else:
            split_fee_quantity = None
            split_fee_value = None
            fee_asset = ""

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: "
                f"split_fee_quantity={split_fee_quantity} split_fee_value={split_fee_value}\n"
            )

        t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            sell_value=sell_value,
            fee_quantity=split_fee_quantity,
            fee_asset=fee_asset,
            fee_value=split_fee_value,
            wallet=WALLET,
        )

        if not data_row.t_record:
            data_row.t_record = t_record
        else:
            dup_data_row = copy.copy(data_row)
            dup_data_row.row = []
            dup_data_row.t_record = t_record
            data_rows.insert(row_index + cnt, dup_data_row)


def _do_zerion_multi_sell(
    data_row: "DataRow",
    data_rows: List["DataRow"],
    row_index: int,
    t_ins: List[Any],
    t_outs: List[Any],
) -> None:
    fee_quantity, fee_asset, fee_value = _get_data(
        data_row, "Fee Amount", "Fee Currency", "Fee Fiat Amount", "Fee Fiat Currency"
    )
    tot_buy_quantity = Decimal(0)
    tot_fee_quantity = Decimal(0)

    buy_quantity, buy_asset, buy_value = _get_data_json(data_row, t_ins[0])

    if config.debug:
        sys.stderr.write(
            f"{Fore.GREEN}conv: "
            f"buy_quantity={buy_quantity} buy_asset={buy_asset} buy_value={buy_value}\n"
        )
        sys.stderr.write(
            f"{Fore.GREEN}conv: "
            f"fee_quantity={fee_quantity} fee_asset={fee_asset} fee_value={fee_value}\n"
        )

    for cnt, t_out in enumerate(t_outs):
        split_buy_value = buy_value / len(t_outs) if buy_value else None

        if cnt < len(t_outs) - 1:
            split_buy_quantity = Decimal(buy_quantity / len(t_outs)).quantize(PRECISION)
            tot_buy_quantity += split_buy_quantity
        else:
            # Last t_out, use up remainder
            split_buy_quantity = buy_quantity - tot_buy_quantity

        if fee_quantity:
            split_fee_value = fee_value / len(t_outs) if fee_value else None

            if cnt < len(t_outs) - 1:
                split_fee_quantity = Decimal(fee_quantity / len(t_outs)).quantize(PRECISION)
                tot_fee_quantity += split_fee_quantity
            else:
                # Last t_out, use up remainder
                split_fee_quantity = fee_quantity - tot_fee_quantity
        else:
            split_fee_quantity = None
            split_fee_value = None
            fee_asset = ""

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: "
                f"split_buy_quantity={split_buy_quantity} split_buy_value={split_buy_value}\n"
            )
            sys.stderr.write(
                f"{Fore.GREEN}conv: "
                f"split_fee_quantity={split_fee_quantity} split_fee_value={split_fee_value}\n"
            )

        sell_quantity, sell_asset, sell_value = _get_data_json(data_row, t_out)
        t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=split_buy_quantity,
            buy_asset=buy_asset,
            buy_value=split_buy_value,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            sell_value=sell_value,
            fee_quantity=split_fee_quantity,
            fee_asset=fee_asset,
            fee_value=split_fee_value,
            wallet=WALLET,
        )

        if not data_row.t_record:
            data_row.t_record = t_record
        else:
            dup_data_row = copy.copy(data_row)
            dup_data_row.row = []
            dup_data_row.t_record = t_record
            data_rows.insert(row_index + cnt, dup_data_row)


def _do_zerion_multi_buy(
    data_row: "DataRow",
    data_rows: List["DataRow"],
    row_index: int,
    t_ins: List[Any],
    t_outs: List[Any],
) -> None:
    fee_quantity, fee_asset, fee_value = _get_data(
        data_row, "Fee Amount", "Fee Currency", "Fee Fiat Amount", "Fee Fiat Currency"
    )
    tot_sell_quantity = Decimal(0)
    tot_fee_quantity = Decimal(0)

    sell_quantity, sell_asset, sell_value = _get_data_json(data_row, t_outs[0])
    if config.debug:
        sys.stderr.write(
            f"{Fore.GREEN}conv: "
            f"sell_quantity={sell_quantity} sell_asset={sell_asset} sell_value={sell_value}\n"
        )
        sys.stderr.write(
            f"{Fore.GREEN}conv: "
            f"fee_quantity={fee_quantity} fee_asset={fee_asset} fee_value={fee_value}\n"
        )

    for cnt, t_in in enumerate(t_ins):
        split_sell_value = sell_value / len(t_ins) if sell_value else None

        if cnt < len(t_ins) - 1:
            split_sell_quantity = Decimal(sell_quantity / len(t_ins)).quantize(PRECISION)
            tot_sell_quantity += split_sell_quantity
        else:
            # Last t_in, use up remainder
            split_sell_quantity = sell_quantity - tot_sell_quantity

        if fee_quantity:
            split_fee_value = fee_value / len(t_ins) if fee_value else None

            if cnt < len(t_ins) - 1:
                split_fee_quantity = Decimal(fee_quantity / len(t_ins)).quantize(PRECISION)
                tot_fee_quantity += split_fee_quantity
            else:
                # Last t_in, use up remainder
                split_fee_quantity = fee_quantity - tot_fee_quantity
        else:
            split_fee_quantity = None
            split_fee_value = None
            fee_asset = ""

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: "
                f"split_sell_quantity={split_sell_quantity} split_sell_value={split_sell_value}\n"
            )
            sys.stderr.write(
                f"{Fore.GREEN}conv: "
                f"split_fee_quantity={split_fee_quantity} split_fee_value={split_fee_value}\n"
            )

        buy_quantity, buy_asset, buy_value = _get_data_json(data_row, t_in)
        t_record = TransactionOutRecord(
            TrType.TRADE,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            buy_value=buy_value,
            sell_quantity=split_sell_quantity,
            sell_asset=sell_asset,
            sell_value=split_sell_value,
            fee_quantity=split_fee_quantity,
            fee_asset=fee_asset,
            fee_value=split_fee_value,
            wallet=WALLET,
        )

        if not data_row.t_record:
            data_row.t_record = t_record
        else:
            dup_data_row = copy.copy(data_row)
            dup_data_row.row = []
            dup_data_row.t_record = t_record
            data_rows.insert(row_index + cnt, dup_data_row)


def _get_data(
    data_row: "DataRow",
    quantity_hdr: str,
    asset_hdr: str,
    value_hdr: str,
    value_currency_hdr: str,
    changes: Optional[List[Any]] = None,
) -> Tuple[Optional[Decimal], str, Optional[Decimal]]:
    if changes:
        # Use values from json if available for better precision
        quantity, asset, value = _get_data_json(data_row, changes[0])
    elif data_row.row_dict[quantity_hdr]:
        # We have to strip carriage returns from fields, this is a bug in the Zerion exporter
        quantity = Decimal(data_row.row_dict[quantity_hdr].split("\n")[0])
        asset = data_row.row_dict[asset_hdr].split("\n")[0]
        value = DataParser.convert_currency(
            data_row.row_dict[value_hdr].split("\n")[0],
            data_row.row_dict[value_currency_hdr].split("\n")[0],
            data_row.timestamp,
        )
    else:
        quantity = None
        asset = ""
        value = None

    return quantity, asset, value


def _get_data_json(
    data_row: "DataRow", changes: Dict[str, Any]
) -> Tuple[Decimal, str, Optional[Decimal]]:
    quantity = Decimal(changes["amount"])
    asset = changes["symbol"]
    value = DataParser.convert_currency(
        changes["fiat_amount"], changes["fiat_currency"], data_row.timestamp
    )
    return quantity, asset, value


DataParser(
    ParserType.EXPLORER,
    "Zerion (ETH Transactions)",
    [
        "Date",
        "Time",
        "Transaction Type",
        "Status",
        "Application",
        "Accounting Type",
        "Buy Amount",
        "Buy Currency",
        "Buy Currency Address",
        "Buy Fiat Amount",
        "Buy Fiat Currency",
        "Sell Amount",
        "Sell Currency",
        "Sell Currency Address",
        "Sell Fiat Amount",
        "Sell Fiat Currency",
        "Fee Amount",
        "Fee Currency",
        "Fee Fiat Amount",
        "Fee Fiat Currency",
        "Sender",
        "Receiver",
        "Tx Hash",
        "Link",
        "Timestamp",
        "Changes JSON",
    ],
    worksheet_name="Zerion",
    all_handler=parse_zerion,
)
