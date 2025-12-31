# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from colorama import Fore, Style
from tqdm import tqdm
from typing_extensions import TypedDict

from .bt_types import AssetSymbol, TrRecordPart, TrType, Wallet
from .config import config
from .constants import WARNING
from .holdings import Holdings
from .t_record import TransactionRecord
from .transactions import Buy, Sell
from .utils import bt_tqdm_write, disable_tqdm


@dataclass
class AuditWallet:
    balance: Decimal = Decimal(0)
    staked: Decimal = Decimal(0)


@dataclass
class AuditTotals:
    total: Decimal = Decimal(0)
    transfers_mismatch: Decimal = Decimal(0)


@dataclass
class AuditLogEntry:
    change: Optional[Decimal]
    fee: Optional[Decimal]
    balance: Decimal
    staked: Decimal
    wallet: Wallet
    total: Decimal
    tr_part: TrRecordPart
    t_record: TransactionRecord


class ComparePoolFail(TypedDict):  # pylint: disable=too-few-public-methods
    asset: AssetSymbol
    audit_tot: Decimal
    s104_tot: Optional[Decimal]


class AuditRecords:
    def __init__(self, transaction_records: List[TransactionRecord]) -> None:
        self.wallets: Dict[Wallet, Dict[AssetSymbol, AuditWallet]] = {}
        self.totals: Dict[AssetSymbol, AuditTotals] = {}
        self.audit_log: Dict[AssetSymbol, List[AuditLogEntry]] = {}
        self.failures: List[ComparePoolFail] = []

        if config.debug:
            print(f"{Fore.CYAN}audit transaction records")

        for tr in tqdm(
            transaction_records,
            unit="tr",
            desc=f"{Fore.CYAN}audit transaction records{Fore.GREEN}",
            disable=disable_tqdm(),
        ):
            if config.debug:
                print(f"{Fore.MAGENTA}audit: TR {tr}")

            if tr.buy:
                self._add_tokens(tr.wallet, tr.buy)
                self._audit_log(
                    tr.buy.asset, tr.wallet, tr.buy.quantity, None, TrRecordPart.BUY, tr
                )
            if tr.sell:
                self._subtract_tokens(tr.wallet, tr.sell)
                self._audit_log(
                    tr.sell.asset, tr.wallet, -abs(tr.sell.quantity), None, TrRecordPart.SELL, tr
                )

            if tr.fee:
                self._subtract_tokens(tr.wallet, tr.fee)
                self._audit_log(
                    tr.fee.asset, tr.wallet, None, -abs(tr.fee.quantity), TrRecordPart.FEE, tr
                )

        if config.debug:
            print(f"{Fore.CYAN}audit: final balances by wallet")
            for wallet in sorted(self.wallets, key=str.lower):
                for asset in sorted(self.wallets[wallet]):
                    print(
                        f"{Fore.YELLOW}audit: {wallet}:{asset}={Style.BRIGHT}"
                        f"{self.wallets[wallet][asset].balance.normalize():0,f}{Style.NORMAL} "
                        f"staked={Style.BRIGHT}{self.wallets[wallet][asset].staked.normalize():0,f}"
                        f"{Style.NORMAL}"
                    )

            print(f"{Fore.CYAN}audit: final balances by asset")
            for asset in sorted(self.totals):
                print(
                    f"{Fore.YELLOW}audit: {asset}={Style.BRIGHT}"
                    f"{self.totals[asset].total.normalize():0,f}{Style.NORMAL}"
                )

        for asset in sorted(self.totals):
            if self.totals[asset].transfers_mismatch:
                print(
                    f"{WARNING} Transfers mismatch of "
                    f"{self.totals[asset].transfers_mismatch.normalize():+0,f} {asset} detected"
                )

        if config.audit_hide_empty:
            self._prune_empty()

    def _add_tokens(self, wallet: Wallet, buy: Buy) -> None:
        if wallet not in self.wallets:
            self.wallets[wallet] = {}

        if buy.asset not in self.wallets[wallet]:
            self.wallets[wallet][buy.asset] = AuditWallet()

        self.wallets[wallet][buy.asset].balance += buy.quantity

        if config.debug:
            print(
                f"{Fore.GREEN}audit:   {wallet}:{buy.asset}="
                f"{self.wallets[wallet][buy.asset].balance.normalize():0,f} "
                f"(+{buy.quantity.normalize():0,f})"
            )

        if buy.t_type is TrType.UNSTAKE:
            self.wallets[wallet][buy.asset].staked -= buy.quantity

            if config.debug:
                print(
                    f"{Fore.GREEN}audit:   {wallet}:{buy.asset}(staked)="
                    f"{self.wallets[wallet][buy.asset].staked.normalize():0,f} "
                    f"(-{buy.quantity.normalize():0,f})"
                )

            if self.wallets[wallet][buy.asset].staked < 0:
                bt_tqdm_write(
                    f"{WARNING} Staked balance at {wallet}:{buy.asset} "
                    f"is negative {self.wallets[wallet][buy.asset].staked.normalize():0,f}"
                )

        if buy.asset not in self.totals:
            self.totals[buy.asset] = AuditTotals()

        if buy.t_type is TrType.DEPOSIT and buy.is_crypto():
            self.totals[buy.asset].transfers_mismatch += buy.quantity

        if buy.t_type is not TrType.UNSTAKE:
            self.totals[buy.asset].total += buy.quantity

    def _subtract_tokens(self, wallet: Wallet, sell: Sell) -> None:
        if wallet not in self.wallets:
            self.wallets[wallet] = {}

        if sell.asset not in self.wallets[wallet]:
            self.wallets[wallet][sell.asset] = AuditWallet()

        self.wallets[wallet][sell.asset].balance -= sell.quantity

        if config.debug:
            print(
                f"{Fore.GREEN}audit:   {wallet}:{sell.asset}="
                f"{self.wallets[wallet][sell.asset].balance.normalize():0,f} "
                f"(-{sell.quantity.normalize():0,f})"
            )
        # ignore if balance is lower than 0.00000001
        if self.wallets[wallet][sell.asset].balance < -0.00000001 and sell.is_crypto():
            bt_tqdm_write(
                f"{WARNING} Balance at {wallet}:{sell.asset} "
                f"is negative {self.wallets[wallet][sell.asset].balance.normalize():0,f}"
            )

        if sell.t_type is TrType.STAKE:
            self.wallets[wallet][sell.asset].staked += sell.quantity

            if config.debug:
                print(
                    f"{Fore.GREEN}audit:   {wallet}:{sell.asset}(staked)="
                    f"{self.wallets[wallet][sell.asset].staked.normalize():0,f} "
                    f"(+{sell.quantity.normalize():0,f})"
                )

        if sell.asset not in self.totals:
            self.totals[sell.asset] = AuditTotals()

        if sell.t_type is TrType.WITHDRAWAL and sell.is_crypto():
            self.totals[sell.asset].transfers_mismatch -= sell.quantity

        if sell.t_type is not TrType.STAKE:
            self.totals[sell.asset].total -= sell.quantity

    def _audit_log(
        self,
        asset: AssetSymbol,
        wallet: Wallet,
        quantity: Optional[Decimal],
        fee: Optional[Decimal],
        tr_part: TrRecordPart,
        tr: TransactionRecord,
    ) -> None:
        audit_log_entry = AuditLogEntry(
            quantity,
            fee,
            self.wallets[wallet][asset].balance,
            self.wallets[wallet][asset].staked,
            wallet,
            self.totals[asset].total,
            tr_part,
            tr,
        )

        if asset not in self.audit_log:
            self.audit_log[asset] = []

        self.audit_log[asset].append(audit_log_entry)

    def _prune_empty(self) -> None:
        for wallet in list(self.wallets):
            for asset in list(self.wallets[wallet]):
                if self.wallets[wallet][asset] == Decimal(0):
                    self.wallets[wallet].pop(asset)
            if not self.wallets[wallet]:
                self.wallets.pop(wallet)

    def compare_pools(self, holdings: Dict[AssetSymbol, Holdings]) -> bool:
        passed = True
        for asset in sorted(self.totals):
            if asset in config.fiat_list:
                continue

            if asset in holdings:
                difference = self.totals[asset].total - holdings[asset].quantity
                if not difference:
                    if config.debug:
                        print(f"{Fore.GREEN}check pool: {asset} (ok)")
                else:
                    if config.debug:
                        print(
                            f"{Fore.RED}check pool: {asset} "
                            f"{difference.normalize():+0,f} (mismatch)"
                        )

                    self._log_failure(asset, self.totals[asset].total, holdings[asset].quantity)
                    passed = False
            else:
                if config.debug:
                    print(f"{Fore.RED}check pool: {asset} (missing)")

                self._log_failure(asset, self.totals[asset].total, None)
                passed = False

        return passed

    def _log_failure(
        self, asset: AssetSymbol, audit_tot: Decimal, s104_tot: Optional[Decimal]
    ) -> None:
        failure: ComparePoolFail = {"asset": asset, "audit_tot": audit_tot, "s104_tot": s104_tot}
        self.failures.append(failure)

    def report_failures(self) -> None:
        print(
            f"\n{Fore.YELLOW}"
            f'{"Asset":<8} {"Audit Balance":>25} {"Section 104 Pool":>25} {"Difference":>25}'
        )

        for failure in self.failures:
            if failure["s104_tot"] is not None:
                print(
                    f'{Fore.WHITE}{failure["asset"]:<8} {failure["audit_tot"].normalize():25,f} '
                    f'{failure["s104_tot"].normalize():25,f} '
                    f'{Fore.RED}{(failure["audit_tot"] - failure["s104_tot"]).normalize():+25,f}'
                )
            else:
                print(
                    f'{Fore.WHITE}{failure["asset"]:<8} {failure["audit_tot"].normalize():25,f} '
                    f'{Fore.RED}{"<missing>":>25}'
                )
