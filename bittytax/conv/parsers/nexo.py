# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

import re
from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Nexo"

ASSET_NORMALISE = {'NEXONEXO': 'NEXO',
                   'NEXOBNB': 'NEXO',
                   'NEXOBEP2': 'NEXO',
                   'USDTERC': 'USDT'}

def parse_nexo(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date / Time'], tz='Europe/Zurich')

    if "rejected" in row_dict['Details']:
        # Skip failed transactions
        return

    asset = row_dict['Currency']
    for local_asset in ASSET_NORMALISE:
        asset = asset.replace(local_asset, ASSET_NORMALISE[local_asset])

    if row_dict.get('USD Equivalent') and asset != config.ccy:
        value = DataParser.convert_currency(row_dict['USD Equivalent'].strip('$'),
                                            'USD', data_row.timestamp)
    else:
        value = None

    if row_dict['Type'] in ("Deposit", "ExchangeDepositedOn"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=asset,
                                                 buy_value=value,
                                                 wallet=WALLET)
    elif row_dict['Type'] in ("Interest", "FixedTermInterest", "InterestAdditional"):
        if Decimal(row_dict['Amount']) > 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                     data_row.timestamp,
                                                     buy_quantity=row_dict['Amount'],
                                                     buy_asset=asset,
                                                     buy_value=value,
                                                     wallet=WALLET)
        else:
            # Interest on loan is just informational
            return
    elif row_dict['Type'] == "Dividend":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DIVIDEND,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=asset,
                                                 buy_value=value,
                                                 wallet=WALLET)
    elif row_dict['Type'] == "Bonus":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Amount'],
                                                 buy_asset=asset,
                                                 buy_value=value,
                                                 wallet=WALLET)

    elif row_dict['Type'] == "Exchange":
        match = re.match(r'^-(\d+|\d+\.\d+) / \+(\d+|\d+\.\d+)$', row_dict['Amount'])
        buy_quantity = None
        sell_quantity = None

        if match:
            buy_quantity = match.group(2)
            sell_quantity = match.group(1)

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=buy_quantity,
                                                 buy_asset=asset.split('/')[1],
                                                 buy_value=value,
                                                 sell_quantity=sell_quantity,
                                                 sell_asset=asset.split('/')[0],
                                                 sell_value=value,
                                                 wallet=WALLET)
    elif row_dict['Type'] in ("Withdrawal", "WithdrawExchanged"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(row_dict['Amount'])),
                                                 sell_asset=asset,
                                                 sell_value=value,
                                                 wallet=WALLET)
    elif row_dict['Type'] == "Liquidation":
        # Repayment of loan
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(row_dict['Amount'])),
                                                 sell_asset=asset,
                                                 sell_value=value,
                                                 wallet=WALLET)
    elif row_dict['Type'] in ("WithdrawalCredit", "UnlockingTermDeposit", "LockingTermDeposit",
                              "Repayment"):
        # Skip loan operations which are not disposals or are just informational
        return
    elif row_dict['Type'] in ("DepositToExchange", "ExchangeToWithdraw",
                              "TransferIn", "TransferOut"):
        # Skip internal operations
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index('Type'), 'Type', row_dict['Type'])

DataParser(DataParser.TYPE_SAVINGS,
           "Nexo",
           ['Transaction', 'Type', 'Currency', 'Amount', 'USD Equivalent', 'Details',
            'Outstanding Loan', 'Date / Time'],
           worksheet_name="Nexo",
           row_handler=parse_nexo)

DataParser(DataParser.TYPE_SAVINGS,
           "Nexo",
           ['Transaction', 'Type', 'Currency', 'Amount', 'Details', 'Outstanding Loan',
            'Date / Time'],
           worksheet_name="Nexo",
           row_handler=parse_nexo)
