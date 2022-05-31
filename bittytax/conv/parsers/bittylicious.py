# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2022

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Bittylicious"

def parse_bittylicious(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['startedTime'])

    if row_dict['status'] != "RECEIVED":
        return

    if row_dict['direction'] == "BUY":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['coinAmount'],
                                                 buy_asset=row_dict['coin'],
                                                 sell_quantity=row_dict['fiatCurrencyAmount'],
                                                 sell_asset=row_dict['fiatCurrency'],
                                                 wallet=WALLET)
    elif row_dict['direction'] == "SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['fiatCurrencyAmount'],
                                                 buy_asset=row_dict['fiatCurrency'],
                                                 sell_quantity=row_dict['coinAmount'],
                                                 sell_asset=row_dict['coin'],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('direction'), 'direction',
                                  row_dict['direction'])

DataParser(DataParser.TYPE_EXCHANGE,
           "Bittylicious",
           ['reference', 'direction', 'status', 'coin', 'coinAmount', 'fiatCurrency',
            'fiatCurrencyAmount', 'startedTime', 'endedTime', 'transactionID', 'coinAddress'],
           worksheet_name="Bittylicious",
           row_handler=parse_bittylicious)
