# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2021

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Ethereum"

def parse_zerion(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Date'] + ' ' + row_dict['Time'])

    # We have to strip carriage returns from fields, this is a bug in the Zerion exporter
    if row_dict['Buy Amount']:
        buy_quantity = row_dict['Buy Amount'].split('\n')[0]
        buy_asset = row_dict['Buy Currency'].split('\n')[0]
        buy_value = DataParser.convert_currency(row_dict['Buy Fiat Amount'].split('\n')[0],
                                                row_dict['Buy Fiat Currency'].split('\n')[0],
                                                data_row.timestamp)
    else:
        buy_quantity = None
        buy_asset = ''
        buy_value = None

    if row_dict['Sell Amount']:
        sell_quantity = row_dict['Sell Amount'].split('\n')[0]
        sell_asset = row_dict['Sell Currency'].split('\n')[0]
        sell_value = DataParser.convert_currency(row_dict['Sell Fiat Amount'].split('\n')[0],
                                                 row_dict['Sell Fiat Currency'].split('\n')[0],
                                                 data_row.timestamp)
    else:
        sell_quantity = None
        sell_asset = ''
        sell_value = None

    if row_dict['Fee Amount']:
        fee_quantity = row_dict['Fee Amount'].split('\n')[0]
        fee_asset = row_dict['Fee Currency'].split('\n')[0]
        fee_value = DataParser.convert_currency(row_dict['Fee Fiat Amount'].split('\n')[0],
                                                row_dict['Fee Fiat Currency'].split('\n')[0],
                                                data_row.timestamp)
    else:
        fee_quantity = None
        fee_asset = ''
        fee_value = None

    if row_dict['Accounting Type'] == "Income":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=buy_quantity,
                                                 buy_asset=buy_asset,
                                                 buy_value=buy_value,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 fee_value=fee_value,
                                                 wallet=WALLET)
    elif row_dict['Accounting Type'] == "Spend":
        if sell_quantity is None and fee_quantity is None:
            return

        # If a Spend only contains fees, we must include a sell of zero
        if sell_quantity is None:
            sell_quantity = 0
            sell_asset = fee_asset

        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=sell_quantity,
                                                 sell_asset=sell_asset,
                                                 sell_value=sell_value,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 fee_value=fee_value,
                                                 wallet=WALLET)
    elif row_dict['Accounting Type'] == "Trade":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=buy_quantity,
                                                 buy_asset=buy_asset,
                                                 buy_value=buy_value,
                                                 sell_quantity=sell_quantity,
                                                 sell_asset=sell_asset,
                                                 sell_value=sell_value,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=fee_asset,
                                                 fee_value=fee_value,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('Accounting Type'), 'Accounting Type',
                                  row_dict['Accounting Type'])

DataParser(DataParser.TYPE_EXPLORER,
           "Zerion (ETH Transactions)",
           ['Date', 'Time', 'Transaction Type', 'Status', 'Application', 'Accounting Type',
            'Buy Amount', 'Buy Currency', 'Buy Currency Address', 'Buy Fiat Amount',
            'Buy Fiat Currency', 'Sell Amount', 'Sell Currency', 'Sell Currency Address',
            'Sell Fiat Amount', 'Sell Fiat Currency', 'Fee Amount', 'Fee Currency',
            'Fee Fiat Amount', 'Fee Fiat Currency', 'Sender', 'Receiver', 'Tx Hash', 'Link',
            'Timestamp', 'Changes JSON'],
           worksheet_name="Zerion",
           row_handler=parse_zerion)
