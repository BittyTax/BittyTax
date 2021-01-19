# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020
# WhippingBoy 2021

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Celsius"

def parse_celsius(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[1])

    if in_row[2] == "deposit":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[4]),
                                                 buy_asset=in_row[3],
                                                 wallet=WALLET)
    elif in_row[2] == "interest":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[4]),
                                                 buy_asset=in_row[3],
                                                 wallet=WALLET)
    elif in_row[2] == "withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[4])),
                                                 sell_asset=in_row[3],
                                                 wallet=WALLET)
    elif in_row[2] == "inbound_transfer":                                                 
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,                  
                                                 sell_quantity=abs(Decimal(in_row[4])),
                                                 sell_asset=in_row[3],                 
                                                 wallet=WALLET) 
    elif in_row[2] == "outbound_transfer":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[4])),
                                                 sell_asset=in_row[3],
                                                 wallet=WALLET)
    elif in_row[2] == "referrer_award":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INCOME,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[4])),
                                                 sell_asset=in_row[3],
                                                 wallet=WALLET)

    elif in_row[2] == "promo_code_reward":   
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INCOME,     
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[4])),
                                                 sell_asset=in_row[3],
                                                 wallet=WALLET)
    elif in_row[2] == "referred_award":                                             
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INCOME,     
                                                 data_row.timestamp,                   
                                                 sell_quantity=abs(Decimal(in_row[4])),
                                                 sell_asset=in_row[3],                 
                                                 wallet=WALLET) 

    else:
        raise UnexpectedTypeError(1, parser.in_header[1], in_row[2])
DataParser(DataParser.TYPE_WALLET,
           "Celsius",
           ['Internal id', ' Date and time',' Transaction type', ' Coin type', ' Coin amount', ' USD Value',
           ' Original Interest Coin', ' Interest Amount In Original Coin', ' Confirmed'],
           worksheet_name="Celsius",
           row_handler=parse_celsius)
