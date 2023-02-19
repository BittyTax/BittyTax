# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownUsernameError

WALLET = "ChangeTip"
AMOUNT = 'Amount in Satoshi'

def parse_changetip(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['When'])

    if row_dict['Status'] == "Delivered":
        if row_dict['To'] in config.usernames:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=Decimal(row_dict[AMOUNT]) /
                                                     10 ** 8,
                                                     buy_asset="BTC",
                                                     wallet=WALLET)
        elif row_dict['From'] in config.usernames:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_SENT,
                                                     data_row.timestamp,
                                                     sell_quantity=Decimal(row_dict[AMOUNT]) /
                                                     10 ** 8,
                                                     sell_asset="BTC",
                                                     wallet=WALLET)
        else:
            raise UnknownUsernameError(kwargs['filename'], kwargs.get('worksheet'))
    else:
        return

DataParser(DataParser.TYPE_EXCHANGE,
           "ChangeTip",
           ['On', 'From', 'To', 'When', 'Amount in Satoshi', 'mBTC', 'Status', 'Message'],
           worksheet_name="ChangeTip",
           row_handler=parse_changetip)
