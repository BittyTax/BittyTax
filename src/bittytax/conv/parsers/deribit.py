# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2024

import copy
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, NewType, Tuple

from colorama import Fore
from typing_extensions import Unpack

from ...bt_types import TrType
from ...config import config
from ...constants import WARNING
from ..dataparser import DataParser, ParserArgs, ParserType
from ..datarow import TxRawPos
from ..exceptions import DataRowError, UnexpectedTypeError, UnknownCryptoassetError, UnexpectedTradingPairError
from ..out_record import TransactionOutRecord

if TYPE_CHECKING:
    from ..datarow import DataRow

PRECISION = Decimal("0." + "0" * 8)

WALLET = "Deribit"

Uid = NewType("Uid", str)
Instrument = NewType("Instrument", str)

balance: Dict[Uid, Decimal] = {}

spot_trades = []


@dataclass
class Position:
    unrealised_pnl: Decimal = Decimal(0)
    trading_fees: Decimal = Decimal(0)
    funding_fees: Decimal = Decimal(0)


def parse_deribit(
        data_rows: List["DataRow"], parser: DataParser, **kwargs: Unpack[ParserArgs]
) -> None:
    positions: Dict[Uid, Dict[Instrument, Position]] = {}
    uid, asset = _get_uid_and_asset(kwargs["filename"])
    balance[uid] = Decimal(0)

    if not asset:
        if kwargs["cryptoasset"]:
            asset = kwargs["cryptoasset"]
        else:
            sys.stderr.write(f"{WARNING} Cryptoasset cannot be identified\n")
            sys.stderr.write(f"{Fore.RESET}Enter symbol: ")
            asset = input()
            if not asset:
                raise UnknownCryptoassetError(kwargs["filename"], kwargs.get("worksheet", ""))

    for data_row in sorted(
            data_rows, key=lambda dr: Decimal(dr.row_dict["UserSeq"]), reverse=False
    ):
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
            _parse_deribit_row(
                data_rows,
                parser,
                data_row,
                positions,
                uid,
                asset,
            )
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: (uid: {uid}) Balance={balance[uid].normalize():0,f} {asset}\n"
            )

    balance_diff = Decimal(0)
    if uid in positions:
        for instrument, position in positions[uid].items():
            balance_diff += position.unrealised_pnl
            balance_diff -= position.trading_fees
            balance_diff += position.funding_fees

            sys.stderr.write(
                f"{Fore.CYAN}conv: Open Position: (uid: {uid}) {instrument} "
                f"unrealised_pnl={position.unrealised_pnl.normalize():0,f} "
                f"trading_fees={position.trading_fees.normalize():0,f} "
                f"funding_fees={position.funding_fees.normalize():0,f}\n"
            )

    if balance_diff:
        sys.stderr.write(
            f"{Fore.CYAN}conv: Balance difference: {balance_diff.normalize():0,f} {asset} "
            f"(for all open positions)\n"
        )


def _parse_deribit_row(
        data_rows: List["DataRow"],
        parser: DataParser,
        data_row: "DataRow",
        positions: Dict[Uid, Dict[Instrument, Position]],
        uid: Uid,
        asset: str,
) -> None:
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(
        f"{row_dict['Date']}.{row_dict['UserSeq'][-6:]}"
    )
    data_row.parsed = True

    if "Fee Paid" in row_dict:
        row_dict["Fee Charged"] = row_dict["Fee Paid"]

    if "Size" in row_dict:
        row_dict["Base Amount"] = row_dict["Size"]

    if "Amount" in row_dict:
        row_dict["Base Amount"] = row_dict["Amount"]

    if row_dict["Type"] == "deposit":
        data_row.tx_raw = TxRawPos(tx_dest_pos=parser.in_header.index("Info"))
        data_row.t_record = TransactionOutRecord(
            TrType.DEPOSIT,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset=asset,
            wallet=WALLET,
        )
        if data_row.t_record.buy_quantity:
            balance[uid] += data_row.t_record.buy_quantity
    elif row_dict["Type"] == "withdrawal":
        data_row.tx_raw = TxRawPos(tx_dest_pos=parser.in_header.index("Info"))
        data_row.t_record = TransactionOutRecord(
            TrType.WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Change"])) - Decimal(row_dict["Fee Charged"]),
            sell_asset=asset,
            fee_quantity=Decimal(row_dict["Fee Charged"]),
            fee_asset=asset,
            wallet=WALLET,
        )
        if data_row.t_record.sell_quantity:
            balance[uid] -= data_row.t_record.sell_quantity
            if data_row.t_record.fee_quantity:
                balance[uid] -= data_row.t_record.fee_quantity
    elif row_dict["Type"] == "transfer":
        if Decimal(row_dict["Change"]) > 0:
            data_row.t_record = TransactionOutRecord(
                TrType.DEPOSIT,
                data_row.timestamp,
                buy_quantity=Decimal(row_dict["Change"]),
                buy_asset=asset,
                wallet=WALLET,
            )
            if data_row.t_record.buy_quantity:
                balance[uid] += data_row.t_record.buy_quantity
        else:
            data_row.t_record = TransactionOutRecord(
                TrType.WITHDRAWAL,
                data_row.timestamp,
                sell_quantity=abs(Decimal(row_dict["Change"])),
                sell_asset=asset,
                wallet=WALLET,
            )
            if data_row.t_record.sell_quantity:
                balance[uid] -= data_row.t_record.sell_quantity
    # the following is to handle Spot transactions which are not currently handles in this parser
    # currently Deribit charges no commissions for Spot
    # Spot trades are recorded both in the base asset file and the quote asset file
    # this def ensures spot trades are only counted once but that the balance[uid] is correctly recorded
    # in both base and quote files
    elif (row_dict["Type"] in ("trade", "delivery")) and \
            (not re.search('(?i)([0-3][0-9](JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[0-9][0-9])|(PERPETUAL)', row_dict["Instrument"])):
        instrument = Instrument(row_dict["Instrument"])
        if (row_dict["Trade ID"] in spot_trades):
            balance[uid] += Decimal(row_dict["Change"])
            if config.debug:
                sys.stderr.write(
                    f"{Fore.GREEN}conv: (uid: {uid}) spot trade {row_dict.get('Side')} : {row_dict.get('Change')} {asset} \n"
                )
        if (row_dict["Side"] in ("close buy", "liquidation buy")) and (row_dict["Trade ID"] not in spot_trades):
            if asset == instrument.split("_")[0]:
                data_row.t_record = TransactionOutRecord(
                    TrType.TRADE,
                    data_row.timestamp,
                    buy_quantity=Decimal(row_dict["Amount"]),
                    buy_asset=asset,
                    sell_quantity=Decimal(row_dict["Amount"]) * Decimal(row_dict["Price"]),
                    sell_asset=instrument.split("_")[1],
                    fee_quantity=Decimal(row_dict["Fee Charged"]),
                    fee_asset=asset,
                    wallet=WALLET,
                )
            else:
                data_row.t_record = TransactionOutRecord(
                    TrType.TRADE,
                    data_row.timestamp,
                    buy_quantity=Decimal(row_dict["Amount"]),
                    buy_asset=asset,
                    sell_quantity=round(Decimal(row_dict["Amount"]) / Decimal(row_dict["Price"]), 8),
                    sell_asset=instrument.split("_")[0],
                    fee_quantity=Decimal(row_dict["Fee Charged"]),
                    fee_asset=asset,
                    wallet=WALLET,
                )
            spot_trades.append(row_dict["Trade ID"])
            balance[uid] += data_row.t_record.buy_quantity
            if config.debug:
                sys.stderr.write(
                    f"{Fore.GREEN}conv: (uid: {uid}) spot trade bought: ({data_row.t_record.buy_quantity}) ({data_row.t_record.buy_asset}) \n"
                    f"{Fore.GREEN}conv: (uid: {uid}) spot trade sold: ({data_row.t_record.sell_quantity}) ({data_row.t_record.sell_asset})\n"
                )
        elif (row_dict["Side"] in ["close sell", "liquidation sell"]) and (row_dict["Trade ID"] not in spot_trades):
            if asset == instrument.split("_")[0]:
                data_row.t_record = TransactionOutRecord(
                    TrType.TRADE,
                    data_row.timestamp,
                    buy_quantity=Decimal(row_dict["Amount"]) * Decimal(row_dict["Price"]),
                    buy_asset=instrument.split("_")[1],
                    sell_quantity=Decimal(row_dict["Amount"]),
                    sell_asset=asset,
                    fee_quantity=Decimal(row_dict["Fee Charged"]),
                    fee_asset=asset,
                    wallet=WALLET,
                )
            else:
                data_row.t_record = TransactionOutRecord(
                    TrType.TRADE,
                    data_row.timestamp,
                    # buy_quantity=Decimal(row_dict["Amount"]),
                    buy_quantity=round(Decimal(row_dict["Amount"]) / Decimal(row_dict["Price"]), 8),
                    buy_asset=instrument.split("_")[0],
                    # sell_quantity=round(Decimal(row_dict["Amount"]) / Decimal(row_dict["Price"]),8),
                    sell_quantity=Decimal(row_dict["Amount"]),
                    sell_asset=asset,
                    fee_quantity=Decimal(row_dict["Fee Charged"]),
                    fee_asset=asset,
                    wallet=WALLET,
                )
            spot_trades.append(row_dict["Trade ID"])
            balance[uid] -= data_row.t_record.sell_quantity
            if config.debug:
                sys.stderr.write(
                    f"{Fore.GREEN}conv: (uid: {uid}) spot trade sold: ({data_row.t_record.sell_quantity} {data_row.t_record.sell_asset})\n"
                    f"{Fore.GREEN}conv: (uid: {uid}) spot trade bought: ({data_row.t_record.buy_quantity} {data_row.t_record.buy_asset})\n "
                )
    elif row_dict["Type"] in ("trade", "delivery") and \
            re.search('(?i)([0-3][0-9](JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[0-9][0-9])|(PERPETUAL)', row_dict["Instrument"]):
        instrument = Instrument(row_dict["Instrument"])
        if uid not in positions:
            positions[uid] = {}
        if instrument not in positions[uid]:
            positions[uid][instrument] = Position()
        #  it should be noted that funding fees sometimes appear
        #  in lines with Type "trade" but don't seem to be included
        #  in Deribit P&L or equity?
        trading_fee = Decimal(row_dict["Fee Charged"])
        unrealised_pnl = Decimal(row_dict["Cash Flow"])
        change = Decimal(row_dict["Change"])

        if change == unrealised_pnl - trading_fee:
            # Accumulate unrealised profit and loss, and trading fees
            positions[uid][instrument].unrealised_pnl += unrealised_pnl
            positions[uid][instrument].trading_fees += trading_fee
            balance[uid] += unrealised_pnl - trading_fee
        elif change == unrealised_pnl:
            # Assumes trading_fees are taken from "Fee Balance"
            # Accumulate unrealised profit and loss, and trading fees
            positions[uid][instrument].unrealised_pnl += unrealised_pnl
            positions[uid][instrument].trading_fees += trading_fee
            balance[uid] += unrealised_pnl - trading_fee
        elif change == -abs(trading_fee):
            # Accumulate only trading fees
            positions[uid][instrument].trading_fees += trading_fee
            balance[uid] -= trading_fee
        else:
            raise RuntimeError(f"Unexpected Change for {instrument}")

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:unrealised_pnl="
                f"{positions[uid][instrument].unrealised_pnl.normalize():0,f} "
                f"({unrealised_pnl.normalize():+0,f})\n"
                f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:trading_fees="
                f"{positions[uid][instrument].trading_fees.normalize():0,f} "
                f"({trading_fee.normalize():+0,f})\n"
                f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:funding_fees="
                f"{positions[uid][instrument].funding_fees.normalize():0,f}\n"
            )

        # Realise profit/loss and total fees when position closed or reduced
        if row_dict["Side"] in ("close buy", "close sell"):
            position = abs(Decimal(row_dict["Position"]))
            base_amount = Decimal(row_dict["Base Amount"])
            partial_close = 1 - (position / (base_amount + position))

            if config.debug:
                sys.stderr.write(
                    f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:position={position} "
                    f"(base_amount={base_amount})\n"
                )

            _close_position(data_rows, data_row, positions, uid, asset, partial_close)
        # in a cross currency margin account you can use many different currencies as margin - this can lead to negative
        # balances e.g your margin money is in ETH and you short the ETH_USDC-PERPETUAL. If ETH goes up, the short
        # position becomes negative in USDC. Deribit and other exchanges charge a rate of interest on negative balances
        # so we need to add negative balances to funding fee and adjust balance[uid]
    elif row_dict["Type"] in ("settlement", "negative_balance_fee", "correction"):
        if row_dict["Type"] == "settlement":
            instrument = Instrument(row_dict["Instrument"])
        else:
            # rows / lines where "Type" is negative_balance_fee  or "correction" have a blank '' for Instrument
            # therefore have to look back to previous row(s)
            # however, it has to be said that negative_balance_fee may well apply to a number of positions
            # I only have one position per account but it would probably be better to generalise it
            # into a new column of row.t_record
            # "correction" has a note explaining which instrument it applies to
            # but in this draft I just apply it to the closest listed row
            instrument = Instrument(row_dict["Instrument"])
            counter = 1
            if not re.search('(?i)([0-3][0-9](JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[0-9][0-9])|(PERPETUAL)', instrument):
                while (data_row.line_num+counter) <= len(data_rows):
                    instrument = data_rows[data_row.line_num + counter].row_dict["Instrument"]
                    counter += 1
                    if re.search('(?i)([0-3][0-9](JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[0-9][0-9])|(PERPETUAL)', instrument):
                        break
        if row_dict["Side"] in ("long", "short"):
            if uid not in positions:
                raise RuntimeError(f"No position open for {instrument}")
            if instrument not in positions[uid]:
                raise RuntimeError(f"No position open for {instrument}")
            # Accumulate funding fees
            funding_fee = Decimal(row_dict["Funding"])
            positions[uid][instrument].funding_fees += funding_fee
            balance[uid] += funding_fee
            # Accumulate unrealised profit and loss
            unrealised_pnl = Decimal(row_dict["Cash Flow"]) - funding_fee
            positions[uid][instrument].unrealised_pnl += unrealised_pnl
            balance[uid] += unrealised_pnl
            if config.debug:
                sys.stderr.write(
                    f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:unrealised_pnl="
                    f"{positions[uid][instrument].unrealised_pnl.normalize():0,f} "
                    f"({unrealised_pnl.normalize():+0,f})\n"
                    f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:trading_fees="
                    f"{positions[uid][instrument].trading_fees.normalize():0,f}\n"
                    f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:funding_fees="
                    f"{positions[uid][instrument].funding_fees.normalize():0,f} "
                    f"({funding_fee.normalize():+0,f})\n"
                )
        # account fr negative balance fees
        if row_dict["Side"] == "-" and row_dict["Type"] == "negative_balance_fee":
            # Accumulate for negative balance fees
            # Deduct them from funding fees
            negative_balance_fee = Decimal(row_dict["Cash Flow"])
            positions[uid][instrument].funding_fees += negative_balance_fee
            balance[uid] += negative_balance_fee
            if config.debug:
                sys.stderr.write(
                    f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:negative_balance_fee="
                    f"{negative_balance_fee}\n"
                )
        if row_dict["Side"] == "-" and row_dict["Type"] == "correction":
            # Accumulate for corrections
            # Add / Deduct them from funding fees
            correction = Decimal(row_dict["Cash Flow"])
            positions[uid][instrument].funding_fees += correction
            balance[uid] += correction
            if config.debug:
                sys.stderr.write(
                    f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:correction="
                    f"{correction}\n"
                )
        if row_dict["Side"] == "-" and row_dict["Type"] != "negative_balance_fee"\
                and row_dict["Type"] != "correction":
            # Position has already closed, final settlement
            unrealised_pnl = Decimal(row_dict["Cash Flow"])
            balance[uid] += unrealised_pnl

            if unrealised_pnl > 0:
                data_row.t_record = TransactionOutRecord(
                    TrType.MARGIN_GAIN,
                    data_row.timestamp,
                    buy_quantity=unrealised_pnl,
                    buy_asset=asset,
                    wallet=WALLET,
                    note=instrument,
                )
            else:
                data_row.t_record = TransactionOutRecord(
                    TrType.MARGIN_LOSS,
                    data_row.timestamp,
                    sell_quantity=abs(unrealised_pnl),
                    sell_asset=asset,
                    wallet=WALLET,
                    note=instrument,
                )
    elif row_dict["Type"] == "position move":
        instrument = Instrument(row_dict["Instrument"])
        if row_dict["Info"].startswith("From"):
            if uid not in positions:
                positions[uid] = {}
            if instrument not in positions[uid]:
                positions[uid][instrument] = Position()
    elif row_dict["Type"] == "transfer from insurance":
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE_REBATE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["Change"]),
            buy_asset="BTC",
            wallet=WALLET,
        )
        if data_row.t_record.buy_quantity:
            balance[uid] += data_row.t_record.buy_quantity
    elif row_dict["Type"] == "socialized fund":
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["Change"])),
            sell_asset="BTC",
            wallet=WALLET,
        )
        if data_row.t_record.sell_quantity:
            balance[uid] -= data_row.t_record.sell_quantity
    else:
        raise UnexpectedTypeError(parser.in_header.index("Type"), "Type", row_dict["Type"])


def _close_position(
        data_rows: List["DataRow"],
        data_row: "DataRow",
        positions: Dict[Uid, Dict[Instrument, Position]],
        uid: Uid,
        asset: str,
        partial_close: Decimal,
) -> None:
    row_dict = data_row.row_dict
    instrument = Instrument(row_dict["Instrument"])

    realised_pnl = (positions[uid][instrument].unrealised_pnl * partial_close).quantize(PRECISION)
    trading_fees = (positions[uid][instrument].trading_fees * partial_close).quantize(PRECISION)
    funding_fees = (positions[uid][instrument].funding_fees * partial_close).quantize(PRECISION)

    if partial_close == 1:
        if config.debug:
            sys.stderr.write(
                f"{Fore.CYAN}conv: Closed position: (uid: {uid}) {instrument} "
                f"realised_pnl={realised_pnl.normalize():0,f} "
                f"trading_fees={trading_fees.normalize():0,f} "
                f"funding_fees={funding_fees.normalize():0,f}\n"
            )
        del positions[uid][instrument]
    else:
        if config.debug:
            sys.stderr.write(
                f"{Fore.CYAN}conv: Partially closed position ({partial_close.normalize():.2%}): "
                f"(uid: {uid}) {instrument} "
                f"realised_pnl={realised_pnl.normalize():0,f} "
                f"trading_fees={trading_fees.normalize():0,f} "
                f"funding_fees={funding_fees.normalize():0,f}\n"
            )

        positions[uid][instrument].unrealised_pnl -= realised_pnl
        positions[uid][instrument].trading_fees -= trading_fees
        positions[uid][instrument].funding_fees -= funding_fees

        if config.debug:
            sys.stderr.write(
                f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:unrealised_pnl="
                f"{positions[uid][instrument].unrealised_pnl.normalize():0,f} "
                f"({1 - partial_close.normalize():.2%})\n"
                f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:trading_fees="
                f"{positions[uid][instrument].trading_fees.normalize():0,f} "
                f"({1 - partial_close.normalize():.2%})\n"
                f"{Fore.GREEN}conv: (uid: {uid}) {instrument}:funding_fees="
                f"{positions[uid][instrument].funding_fees.normalize():0,f} "
                f"({1 - partial_close.normalize():.2%})\n"
            )

    if realised_pnl > 0:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_GAIN,
            data_row.timestamp,
            buy_quantity=realised_pnl,
            buy_asset=asset,
            wallet=WALLET,
            note=instrument,
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_LOSS,
            data_row.timestamp,
            sell_quantity=abs(realised_pnl),
            sell_asset=asset,
            wallet=WALLET,
            note=instrument,
        )

    dup_data_row = copy.copy(data_row)
    dup_data_row.row = []

    if funding_fees - trading_fees > 0:
        dup_data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE_REBATE,
            data_row.timestamp,
            buy_quantity=funding_fees - trading_fees,
            buy_asset=asset,
            wallet=WALLET,
            note=instrument,
        )
    else:
        dup_data_row.t_record = TransactionOutRecord(
            TrType.MARGIN_FEE,
            data_row.timestamp,
            sell_quantity=abs(funding_fees - trading_fees),
            sell_asset=asset,
            wallet=WALLET,
            note=instrument,
        )
    data_rows.append(dup_data_row)


def _get_uid_and_asset(filename: str) -> Tuple[Uid, str]:
    match = re.match(r".*transaction_log-(\d+)-([A-Z]{3,4})-.*", filename)

    if match:
        return Uid(match.group(1)), match.group(2)

    match = re.match(r".*[- ]([A-Z]{3,4})[-.*|.csv]", filename)

    if match:
        return Uid(""), match.group(1)

    return Uid(""), ""


DataParser(
    ParserType.EXCHANGE,
    "Deribit",
    [
        "ID",
        "UserSeq",
        "Date",
        "Instrument",
        "Type",
        "Side",
        "Amount",  # New field
        "Base Amount",
        "Position",
        "Price",
        "Mark Price",
        "Index Price",
        "Cash Flow",
        "Funding",
        "Fee Rate",
        "Fee Charged",
        "Fee Balance",
        "Change",
        "Balance",
        "Equity",
        "Trade ID",
        "Order ID",
        "Info",
        "Note",
    ],
    worksheet_name="Deribit",
    all_handler=parse_deribit,
)

DataParser(
    ParserType.EXCHANGE,
    "Deribit",
    [
        "ID",
        "UserSeq",
        "Date",
        "Instrument",
        "Type",
        "Side",
        "Base Amount",
        "Position",
        "Price",
        "Mark Price",
        "Index Price",
        "Cash Flow",
        "Funding",
        "Fee Rate",
        "Fee Charged",
        "Fee Balance",
        "Change",
        "Balance",
        "Equity",
        "Trade ID",
        "Order ID",
        "Info",
        "Note",  # New field
    ],
    worksheet_name="Deribit",
    all_handler=parse_deribit,
)

DataParser(
    ParserType.EXCHANGE,
    "Deribit",
    [
        "ID",
        "UserSeq",
        "Date",
        "Instrument",
        "Type",
        "Side",
        "Base Amount",  # Renamed
        "Position",
        "Price",
        "Mark Price",
        "Index Price",  # New field
        "Cash Flow",
        "Funding",
        "Fee Rate",
        "Fee Charged",  # Renamed
        "Fee Balance",
        "Change",
        "Balance",
        "Equity",
        "Trade ID",
        "Order ID",
        "Info",
    ],
    worksheet_name="Deribit",
    all_handler=parse_deribit,
)

DataParser(
    ParserType.EXCHANGE,
    "Deribit",
    [
        "ID",
        "UserSeq",
        "Date",
        "Instrument",
        "Type",
        "Side",
        "Size",
        "Position",
        "Price",
        "Mark Price",
        "Cash Flow",
        "Funding",
        "Fee Rate",
        "Fee Paid",
        "Fee Balance",
        "Change",
        "Balance",
        "Equity",
        "Trade ID",
        "Order ID",
        "Info",
    ],
    worksheet_name="Deribit",
    all_handler=parse_deribit,
)
