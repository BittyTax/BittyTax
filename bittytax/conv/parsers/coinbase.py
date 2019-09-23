# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Coinbase"
DUPLICATE = "Duplicate"

def parse_coinbase_transfers(in_row):
    if in_row[1] == "Deposit":
        return TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                    DataParser.parse_timestamp(in_row[0]),
                                    buy_quantity=in_row[5],
                                    buy_asset=in_row[6],
                                    fee_quantity=in_row[4],
                                    fee_asset=in_row[6],
                                    wallet=WALLET)
    elif in_row[1] == "Withdrawal":
        return TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                    DataParser.parse_timestamp(in_row[0]),
                                    sell_quantity=in_row[5],
                                    sell_asset=in_row[6],
                                    fee_quantity=in_row[4],
                                    fee_asset=in_row[6],
                                    wallet=WALLET)
    elif in_row[1] == "Buy":
        return TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                    DataParser.parse_timestamp(in_row[0]),
                                    buy_quantity=in_row[2],
                                    buy_asset="BTC",
                                    sell_quantity=in_row[3],
                                    sell_asset=in_row[6],
                                    fee_quantity=in_row[4],
                                    fee_asset=in_row[6],
                                    wallet=WALLET)
    elif in_row[1] == "Sell":
        return TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                    DataParser.parse_timestamp(in_row[0]),
                                    buy_quantity=in_row[3],
                                    buy_asset=in_row[6],
                                    sell_quantity=in_row[2],
                                    sell_asset="BTC",
                                    fee_quantity=in_row[4],
                                    fee_asset=in_row[6],
                                    wallet=WALLET)
    else:
        raise ValueError("Unrecognised Type: " + in_row[1])

def parse_coinbase_transactions(in_row):
    if in_row[21] != "":
        # Hash so must be external crypto deposit or withdrawal
        if Decimal(in_row[2]) < 0:
            return TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                        DataParser.parse_timestamp(in_row[0]),
                                        sell_quantity=abs(Decimal(in_row[2])),
                                        sell_asset=in_row[3],
                                        wallet=WALLET)
        else:
            return TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                        DataParser.parse_timestamp(in_row[0]),
                                        buy_quantity=in_row[2],
                                        buy_asset=in_row[3],
                                        wallet=WALLET)
    elif in_row[12] != "":
        # Transfer ID so could be a trade or external fiat deposit/withdrawal
        if in_row[3] != in_row[8]:
            # Currencies are different so must be a trade
            if Decimal(in_row[2]) < 0:
                return TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                            DataParser.parse_timestamp(in_row[0]),
                                            buy_quantity=Decimal(in_row[7]) + Decimal(in_row[9]),
                                            buy_asset=in_row[8],
                                            sell_quantity=abs(Decimal(in_row[2])),
                                            sell_asset=in_row[3],
                                            fee_quantity=in_row[9],
                                            fee_asset=in_row[10],
                                            wallet=WALLET)
            else:
                return TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                            DataParser.parse_timestamp(in_row[0]),
                                            buy_quantity=in_row[2],
                                            buy_asset=in_row[3],
                                            sell_quantity=Decimal(in_row[7]) - Decimal(in_row[9]),
                                            sell_asset=in_row[8],
                                            fee_quantity=in_row[9],
                                            fee_asset=in_row[10],
                                            wallet=WALLET)
        else:
            if Decimal(in_row[2]) < 0:
                return TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                            DataParser.parse_timestamp(in_row[0]),
                                            sell_quantity=in_row[7],
                                            sell_asset=in_row[3],
                                            fee_quantity=in_row[9],
                                            fee_asset=in_row[10],
                                            wallet=WALLET)
            else:
                return TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                            DataParser.parse_timestamp(in_row[0]),
                                            buy_quantity=in_row[7],
                                            buy_asset=in_row[3],
                                            fee_quantity=in_row[9],
                                            fee_asset=in_row[10],
                                            wallet=WALLET)
    else:
        # Could be a referral bonus or deposit/withdrawal to/from Coinbase Pro
        if in_row[5] != "" and in_row[3] == "BTC":
            # Bonus is always in BTC
            return TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                        DataParser.parse_timestamp(in_row[0]),
                                        buy_quantity=in_row[2],
                                        buy_asset=in_row[3],
                                        wallet=WALLET)
        elif in_row[5] != "" and in_row[3] != "BTC":
            # Special case, flag as duplicate entry, trade will be in BTC Wallet Transactions Report
            if Decimal(in_row[2]) < 0:
                return TransactionOutRecord(DUPLICATE,
                                            DataParser.parse_timestamp(in_row[0]),
                                            sell_quantity=abs(Decimal(in_row[2])),
                                            sell_asset=in_row[3],
                                            wallet=WALLET)
            else:
                return TransactionOutRecord(DUPLICATE,
                                            DataParser.parse_timestamp(in_row[0]),
                                            buy_quantity=in_row[2],
                                            buy_asset=in_row[3],
                                            wallet=WALLET)
        elif Decimal(in_row[2]) < 0:
            return TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                        DataParser.parse_timestamp(in_row[0]),
                                        sell_quantity=abs(Decimal(in_row[2])),
                                        sell_asset=in_row[3],
                                        wallet=WALLET)
        else:
            return TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                        DataParser.parse_timestamp(in_row[0]),
                                        buy_quantity=in_row[2],
                                        buy_asset=in_row[3],
                                        wallet=WALLET)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase Transfers",
           ['Timestamp', 'Type', None, 'Subtotal', 'Fees', 'Total', 'Currency', 'Price Per Coin',
            'Payment Method', 'ID', 'Share'],
           row_handler=parse_coinbase_transfers)

DataParser(DataParser.TYPE_EXCHANGE,
           "Coinbase Transactions",
           ['Timestamp', 'Balance', 'Amount', 'Currency', 'To', 'Notes', 'Instantly Exchanged',
            'Transfer Total', 'Transfer Total Currency', 'Transfer Fee', 'Transfer Fee Currency',
            'Transfer Payment Method', 'Transfer ID', 'Order Price', 'Order Currency', None,
            'Order Tracking Code', 'Order Custom Parameter', 'Order Paid Out',
            'Recurring Payment ID', None, None],
           row_handler=parse_coinbase_transactions)
