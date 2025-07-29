# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import copy
import re
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union

from colorama import Fore, Style
from tqdm import tqdm

from .bt_types import TRANSFER_TYPES, AssetSymbol, Date, Note, Timestamp, TrType, Wallet
from .config import config
from .price.valueasset import ValueAsset, ValueOrigin
from .t_record import TransactionRecord
from .utils import disable_tqdm


class TransactionHistory:
    def __init__(
        self, transaction_records: List[TransactionRecord], value_asset: ValueAsset
    ) -> None:
        self.value_asset = value_asset
        self.transactions: List[Union[Buy, Sell]] = []

        if config.debug:
            print(f"{Fore.CYAN}split transaction records")

        for tr in tqdm(
            transaction_records,
            unit="tr",
            desc=f"{Fore.CYAN}split transaction records{Fore.GREEN}",
            disable=disable_tqdm(),
        ):
            if config.debug:
                print(f"{Fore.MAGENTA}split: TR {tr}")

            self.get_all_values(tr)

            # The fee value (trading fee) as an allowable cost to the buy, the sell or both
            if tr.fee and tr.fee.disposal and tr.fee.proceeds:
                if tr.buy and tr.buy.acquisition and tr.sell and tr.sell.disposal:
                    if tr.t_type in (TrType.TRADE, TrType.SWAP):
                        if tr.buy.asset in config.fiat_list:
                            tr.sell.fee_value = tr.fee.proceeds
                        elif tr.sell.asset in config.fiat_list:
                            tr.buy.fee_value = tr.fee.proceeds
                        else:
                            # Crypto-to-crypto trades
                            if config.trade_allowable_cost_type == config.TRADE_ALLOWABLE_COST_BUY:
                                tr.buy.fee_value = tr.fee.proceeds
                            elif (
                                config.trade_allowable_cost_type == config.TRADE_ALLOWABLE_COST_SELL
                            ):
                                tr.sell.fee_value = tr.fee.proceeds
                            else:
                                # Split fee between both
                                tr.buy.fee_value = tr.fee.proceeds / 2
                                tr.sell.fee_value = tr.fee.proceeds - tr.buy.fee_value
                    elif tr.t_type is TrType.LOST:
                        if config.transaction_fee_allowable_cost:
                            # Assign fee to the disposal
                            tr.sell.fee_value = tr.fee.proceeds
                    else:
                        raise RuntimeError(f"Unexpected tr.t_type: {tr.t_type}")
                elif tr.buy and tr.buy.acquisition:
                    if config.transaction_fee_allowable_cost:
                        tr.buy.fee_value = tr.fee.proceeds
                elif tr.sell and tr.sell.disposal:
                    if config.transaction_fee_allowable_cost:
                        tr.sell.fee_value = tr.fee.proceeds
                else:
                    # Special case for transfer fees
                    if tr.t_type in TRANSFER_TYPES:
                        if config.transfer_fee_allowable_cost:
                            tr.fee.fee_value = tr.fee.proceeds

            if tr.t_type not in (TrType.LOST, TrType.SWAP):
                if tr.buy:
                    tr.buy.set_tid()
                    self.transactions.append(tr.buy)
                    if config.debug:
                        print(f"{Fore.GREEN}split:   {tr.buy}")

                if tr.sell:
                    tr.sell.set_tid()
                    self.transactions.append(tr.sell)
                    if config.debug:
                        print(f"{Fore.GREEN}split:   {tr.sell}")

                if tr.fee:
                    tr.fee.set_tid()
                    self.transactions.append(tr.fee)
                    if config.debug:
                        print(f"{Fore.GREEN}split:   {tr.fee}")
            else:
                # Special case for LOST/SWAP, sell and fee must be before buy-back/buy
                if tr.sell:
                    tr.sell.set_tid()
                    self.transactions.append(tr.sell)
                    if config.debug:
                        print(f"{Fore.GREEN}split:   {tr.sell}")

                if tr.fee:
                    tr.fee.set_tid()
                    self.transactions.append(tr.fee)
                    if config.debug:
                        print(f"{Fore.GREEN}split:   {tr.fee}")

                if tr.buy:
                    tr.buy.set_tid()
                    self.transactions.append(tr.buy)
                    if config.debug:
                        print(f"{Fore.GREEN}split:   {tr.buy}")

        if config.debug:
            print(f"{Fore.CYAN}split: total transactions={len(self.transactions)}")

    def get_all_values(self, tr: TransactionRecord) -> None:
        if tr.buy and tr.buy.acquisition and tr.buy.cost is None:
            if tr.sell:
                tr.buy.cost, tr.buy.cost_origin = self.which_asset_value(tr.buy, tr.sell)
            else:
                tr.buy.cost, tr.buy.cost_origin = self.value_asset.get_value(tr.buy)

        if tr.sell and tr.sell.disposal and tr.sell.proceeds is None:
            if tr.buy:
                tr.sell.proceeds, tr.sell.proceeds_origin = tr.buy.cost, tr.buy.cost_origin
            else:
                tr.sell.proceeds, tr.sell.proceeds_origin = self.value_asset.get_value(tr.sell)

        if tr.fee and tr.fee.disposal and tr.fee.proceeds is None:
            if tr.fee.asset not in config.fiat_list:
                if tr.fee.quantity == 0:
                    tr.fee.proceeds = Decimal(0)
                    tr.fee.proceeds_origin = ValueOrigin(tr.fee)
                    return

                if tr.buy and tr.buy.asset == tr.fee.asset:
                    if tr.buy.cost and tr.buy.quantity:
                        price = tr.buy.cost / tr.buy.quantity
                        tr.fee.proceeds = tr.fee.quantity * price

                        if tr.buy.cost_origin is None:
                            raise RuntimeError("Missing tr.buy.cost_origin")

                        tr.fee.proceeds_origin = ValueOrigin(
                            tr.buy,
                            tr.buy.cost_origin.price_record,
                            derived_price=True,
                        )
                    else:
                        tr.fee.proceeds, tr.fee.proceeds_origin = self.value_asset.get_value(tr.fee)
                elif tr.sell and tr.sell.asset == tr.fee.asset:
                    if tr.sell.proceeds and tr.sell.quantity:
                        price = tr.sell.proceeds / tr.sell.quantity
                        tr.fee.proceeds = tr.fee.quantity * price

                        if tr.sell.proceeds_origin is None:
                            raise RuntimeError("Missing tr.sell.proceeds_origin")

                        tr.fee.proceeds_origin = ValueOrigin(
                            tr.sell,
                            tr.sell.proceeds_origin.price_record,
                            derived_price=True,
                        )
                    else:
                        tr.fee.proceeds, tr.fee.proceeds_origin = self.value_asset.get_value(tr.fee)
                else:
                    # Must be a 3rd cryptoasset
                    tr.fee.proceeds, tr.fee.proceeds_origin = self.value_asset.get_value(tr.fee)
            else:
                # Fee paid in fiat
                tr.fee.proceeds, tr.fee.proceeds_origin = self.value_asset.get_value(tr.fee)

    def which_asset_value(self, buy: "Buy", sell: "Sell") -> Tuple[Decimal, ValueOrigin]:
        if config.trade_asset_type == config.TRADE_ASSET_TYPE_BUY:
            if buy.cost is None:
                value, origin = self.value_asset.get_value(buy)
            else:
                if buy.cost_origin is None:
                    raise RuntimeError("Missing buy.cost_origin")

                value, origin = buy.cost, buy.cost_origin
        elif config.trade_asset_type == config.TRADE_ASSET_TYPE_SELL:
            if sell.proceeds is None:
                value, origin = self.value_asset.get_value(sell)
            else:
                if sell.proceeds_origin is None:
                    raise RuntimeError("Missing sell.proceeds_origin")

                value, origin = sell.proceeds, sell.proceeds_origin
        else:
            pos_sell_asset = pos_buy_asset = len(config.asset_priority) + 1

            if sell.asset in config.asset_priority:
                pos_sell_asset = config.asset_priority.index(sell.asset)
            if buy.asset in config.asset_priority:
                pos_buy_asset = config.asset_priority.index(buy.asset)

            if pos_sell_asset <= pos_buy_asset:
                if sell.proceeds is None:
                    value, origin = self.value_asset.get_value(sell)
                else:
                    if sell.proceeds_origin is None:
                        raise RuntimeError("Missing sell.proceeds_origin")

                    value, origin = sell.proceeds, sell.proceeds_origin
            else:
                if buy.cost is None:
                    value, origin = self.value_asset.get_value(buy)
                else:
                    if buy.cost_origin is None:
                        raise RuntimeError("Missing buy.cost_origin")

                    value, origin = buy.cost, buy.cost_origin

        return value, origin


class TransactionBase:  # pylint: disable=too-many-instance-attributes
    POOLED = "<pooled>"

    def __init__(self, t_type: TrType, asset: AssetSymbol, quantity: Decimal) -> None:
        self.tid: Optional[List[int]] = None
        self.t_record: Optional[TransactionRecord] = None
        self.t_type = t_type
        self.asset = asset
        self.quantity = quantity
        self.fee_value: Optional[Decimal] = None
        self.wallet: Wallet = Wallet("")
        self.timestamp: Timestamp
        self.note: Note = Note("")
        self.is_split = False
        self.matched = False
        self.pooled: List[Union[Buy, Sell]] = []

    def name(self) -> str:
        return self.__class__.__name__

    def set_tid(self) -> None:
        if not self.t_record:
            raise RuntimeError("Missing t_record")

        self.tid = self.t_record.set_tid()

    def _format_tid(self) -> str:
        if self.tid:
            return f"[TID:{self.tid[0]}.{self.tid[1]}]"
        return ""

    def is_crypto(self) -> bool:
        return bool(self.asset not in config.fiat_list)

    def is_nft(self) -> bool:
        match = re.match(r".+#(\d+)$", self.asset)
        return bool(match)

    def date(self) -> Date:
        return Date(self.timestamp.date())

    def is_fee_fixed(self) -> bool:
        if (
            self.t_record
            and self.t_record.fee
            and self.t_record.fee.proceeds_origin
            and self.t_record.fee.proceeds_origin.price_record
        ):
            return False
        return True

    def format_quantity(self) -> str:
        return f"{self.quantity.normalize():0,f}"

    def _format_note(self) -> str:
        if self.note:
            return f"'{self.note}' "
        return ""

    def _format_pooled(self, bold: bool = False) -> str:
        if self.pooled:
            return (
                f" {Style.BRIGHT if bold else ''}({len(self.pooled)})"
                f"{Style.NORMAL if bold else ''}"
            )
        return ""

    def _format_fee(self) -> str:
        if self.fee_value is not None:
            return (
                f" + fee={'' if self.is_fee_fixed() else '~'}"
                f"{config.sym()}{self.fee_value:0,.2f} {config.ccy}"
            )

        return ""

    def _format_timestamp(self) -> str:
        if not self.timestamp:
            raise RuntimeError("Missing timestamp")

        if self.timestamp.microsecond:
            return f"{self.timestamp:%Y-%m-%dT%H:%M:%S.%f %Z}"
        return f"{self.timestamp:%Y-%m-%dT%H:%M:%S %Z}"

    def _format_price(self, price: Optional[Decimal]) -> str:
        if price and self.asset != config.ccy:
            return f" '1 {self.asset}={config.sym()}{price:0,.2f} {config.ccy}'"
        return ""

    def __hash__(self) -> int:
        return hash(str(self.tid))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TransactionBase):
            return NotImplemented
        return (self.asset, self.timestamp, self.tid) == (other.asset, other.timestamp, other.tid)

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __lt__(self, other: "TransactionBase") -> bool:
        return (self.asset, self.timestamp, self.tid if self.tid else []) < (
            other.asset,
            other.timestamp,
            other.tid if other.tid else [],
        )

    def __deepcopy__(self, memo: Dict[int, object]) -> "TransactionBase":
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k in ("t_record", "cost_origin", "proceeds_origin"):
                # Keep references to transaction records
                setattr(result, k, v)
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result


class Buy(TransactionBase):  # pylint: disable=too-many-instance-attributes
    ACQUISITIONS = {
        TrType.MINING,
        TrType.STAKING_REWARD,
        TrType.STAKING,
        TrType.INTEREST,
        TrType.DIVIDEND,
        TrType.INCOME,
        TrType.GIFT_RECEIVED,
        TrType.FORK,
        TrType.AIRDROP,
        TrType.REFERRAL,
        TrType.CASHBACK,
        TrType.FEE_REBATE,
        TrType.LOAN,
        TrType.MARGIN_GAIN,
        TrType.MARGIN_FEE_REBATE,
        TrType.TRADE,
        TrType.SWAP,
    }

    def __init__(
        self,
        t_type: TrType,
        buy_quantity: Decimal,
        buy_asset: AssetSymbol,
        buy_value: Optional[Decimal],
    ):
        super().__init__(t_type, buy_asset, buy_quantity)
        self.acquisition = bool(self.t_type in self.ACQUISITIONS)
        self.cost = None
        self.cost_origin: Optional[ValueOrigin] = None

        if self.acquisition and buy_value is not None:
            self.cost = buy_value
            self.cost_origin = ValueOrigin(self)

    def __iadd__(self, other: "Buy") -> "Buy":
        if not self.pooled:
            self.pooled.append(copy.deepcopy(self))

        # Pool buys
        if self.asset != other.asset:
            raise RuntimeError("Assets do not match")

        self.quantity += other.quantity

        if self.cost is None or other.cost is None:
            raise RuntimeError("Missing cost")

        self.cost += other.cost

        if self.fee_value is not None and other.fee_value is not None:
            self.fee_value += other.fee_value
        elif self.fee_value is None and other.fee_value is not None:
            self.fee_value = other.fee_value

        # Keep timestamp of earliest transaction
        self.timestamp = min(other.timestamp, self.timestamp)

        if other.wallet != self.wallet:
            self.wallet = Wallet(self.POOLED)

        if other.cost_origin and other.cost_origin.price_record:
            self.cost_origin = other.cost_origin

        if other.note != self.note:
            self.note = Note(self.POOLED)

        self.pooled.append(other)
        return self

    def split_buy(self, sell_quantity: Decimal) -> "Buy":
        remainder = copy.deepcopy(self)

        if self.cost is None or remainder.cost is None:
            raise RuntimeError("Missing cost")

        self.cost = self.cost * (sell_quantity / self.quantity)

        if self.fee_value:
            self.fee_value = self.fee_value * (sell_quantity / self.quantity)

        self.quantity = sell_quantity
        self.set_tid()
        self.is_split = True

        # pylint: disable=attribute-defined-outside-init
        remainder.cost = remainder.cost - self.cost
        # pylint: enable=attribute-defined-outside-init

        if self.fee_value and remainder.fee_value:
            remainder.fee_value = remainder.fee_value - self.fee_value

        remainder.quantity = remainder.quantity - sell_quantity

        remainder.cost_origin = copy.copy(self.cost_origin)
        if remainder.cost_origin and self.cost_origin and self.cost_origin.origin is self:
            remainder.cost_origin.origin = remainder

        remainder.set_tid()
        remainder.is_split = True
        return remainder

    def price(self) -> Decimal:
        if self.cost is not None and self.fee_value is not None and self.quantity:
            return (self.cost + self.fee_value) / self.quantity
        if self.cost is not None and self.quantity:
            return self.cost / self.quantity
        return Decimal(0)

    def is_cost_fixed(self) -> bool:
        if self.cost_origin and self.cost_origin.price_record:
            return False
        return True

    def _format_cost(self) -> str:
        if self.cost is not None:
            return (
                f" ({'=' if self.is_cost_fixed() else '~'}"
                f"{config.sym()}{self.cost:0,.2f} {config.ccy})"
            )
        return ""

    def format_str(self, quantity_bold: bool = False) -> str:
        return (
            f"{self.name().upper()}{'*' if not self.acquisition else ''} "
            f"{self.t_type.value}"
            f"{Style.BRIGHT if quantity_bold else ''} "
            f"{self.format_quantity()} "
            f"{self.asset}"
            f"{Style.NORMAL if quantity_bold else ''}"
            f"{self._format_cost()}"
            f"{self._format_fee()}"
            f"{self._format_price(self.price())} "
            f"'{self.wallet}' "
            f"{self._format_timestamp()} "
            f"{self._format_note()}"
            f"{self._format_tid()}"
            f"{self._format_pooled()}"
        )

    def __str__(self) -> str:
        return self.format_str()


class Sell(TransactionBase):  # pylint: disable=too-many-instance-attributes
    DISPOSALS = {
        TrType.SPEND,
        TrType.GIFT_SENT,
        TrType.GIFT_SPOUSE,
        TrType.CHARITY_SENT,
        TrType.LOST,
        TrType.LOAN_REPAYMENT,
        TrType.LOAN_INTEREST,
        TrType.MARGIN_LOSS,
        TrType.MARGIN_FEE,
        TrType.TRADE,
        TrType.SWAP,
    }

    def __init__(
        self,
        t_type: TrType,
        sell_quantity: Decimal,
        sell_asset: AssetSymbol,
        sell_value: Optional[Decimal],
    ):
        super().__init__(t_type, sell_asset, sell_quantity)
        self.disposal = bool(self.t_type in self.DISPOSALS)
        self.proceeds = None
        self.proceeds_origin: Optional[ValueOrigin] = None

        if self.disposal and sell_value is not None:
            self.proceeds = sell_value
            self.proceeds_origin = ValueOrigin(self)

    def __iadd__(self, other: "Sell") -> "Sell":
        if not self.pooled:
            self.pooled.append(copy.deepcopy(self))

        # Pool sells
        if self.asset != other.asset:
            raise RuntimeError("Assets do not match")

        self.quantity += other.quantity

        if self.proceeds is None or other.proceeds is None:
            raise RuntimeError("Missing proceeds")

        self.proceeds += other.proceeds

        if self.fee_value is not None and other.fee_value is not None:
            self.fee_value += other.fee_value
        elif self.fee_value is None and other.fee_value is not None:
            self.fee_value = other.fee_value

        # Keep timestamp of latest transaction
        self.timestamp = max(other.timestamp, self.timestamp)

        if other.wallet != self.wallet:
            self.wallet = Wallet(self.POOLED)

        if other.proceeds_origin and other.proceeds_origin.price_record:
            self.proceeds_origin = other.proceeds_origin

        if other.note != self.note:
            self.note = Note(self.POOLED)

        self.pooled.append(other)
        return self

    def split_sell(self, buy_quantity: Decimal) -> "Sell":
        remainder = copy.deepcopy(self)

        if self.proceeds is None or remainder.proceeds is None:
            raise RuntimeError("Missing proceeds")

        self.proceeds = self.proceeds * (buy_quantity / self.quantity)

        if self.fee_value:
            self.fee_value = self.fee_value * (buy_quantity / self.quantity)

        self.quantity = buy_quantity
        self.set_tid()

        # pylint: disable=attribute-defined-outside-init
        remainder.proceeds = remainder.proceeds - self.proceeds
        # pylint: enable=attribute-defined-outside-init

        if self.fee_value and remainder.fee_value:
            remainder.fee_value = remainder.fee_value - self.fee_value

        remainder.quantity = remainder.quantity - buy_quantity

        remainder.proceeds_origin = copy.copy(self.proceeds_origin)
        if (
            remainder.proceeds_origin
            and self.proceeds_origin
            and self.proceeds_origin.origin is self
        ):
            remainder.proceeds_origin.origin = remainder

        remainder.set_tid()
        remainder.is_split = True
        return remainder

    def price(self) -> Decimal:
        if self.proceeds is not None and self.fee_value is not None and self.quantity:
            return (self.proceeds - self.fee_value) / self.quantity
        if self.proceeds is not None and self.quantity:
            return self.proceeds / self.quantity
        return Decimal(0)

    def is_proceeds_fixed(self) -> bool:
        if self.proceeds_origin and self.proceeds_origin.price_record:
            return False
        return True

    def _format_proceeds(self) -> str:
        if self.proceeds is not None:
            return (
                f" ({'=' if self.is_proceeds_fixed() else '~'}"
                f"{config.sym()}{self.proceeds:0,.2f} {config.ccy})"
            )
        return ""

    def format_str(self, quantity_bold: bool = False) -> str:
        return (
            f"{self.name().upper()}{'*' if not self.disposal else ''} "
            f"{self.t_type.value}"
            f"{Style.BRIGHT if quantity_bold else ''} "
            f"{self.format_quantity()} "
            f"{self.asset}"
            f"{Style.NORMAL if quantity_bold else ''}"
            f"{self._format_proceeds()}"
            f"{self._format_fee()}"
            f"{self._format_price(self.price())} "
            f"'{self.wallet}' "
            f"{self._format_timestamp()} "
            f"{self._format_note()}"
            f"{self._format_tid()}"
            f"{self._format_pooled()}"
        )

    def __str__(self) -> str:
        return self.format_str()
