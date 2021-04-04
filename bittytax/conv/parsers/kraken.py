# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError, UnexpectedTradingPairError

WALLET = "Kraken"

QUOTE_ASSETS =  ['AUD', 'CAD', 'CHF', 'DAI', 'ETH', 'EUR', 'GBP', 'JPY', 'USD', 'USDC',
                 'USDT', 'XBT', 'XETH', 'XXBT', 'ZCAD', 'ZEUR', 'ZGBP', 'ZJPY', 'ZUSD']

ALT_ASSETS = {"KFEE": "FEE", "XETC": "ETC", "XETH": "ETH", "XLTC": "LTC", "XMLN": "MLN",
              "XREP": "REP", "XXBT": "XBT", "XXDG": "XDG", "XXLM": "XLM", "XXMR": "XMR",
              "XXRP": "XRP", "XZEC": "ZEC", "ZAUD": "AUD", "ZCAD": "CAD", "ZEUR": "EUR",
              "ZGBP": "GBP", "ZJPY": "JPY", "ZUSD": "USD"}

def parse_kraken_deposits_withdrawals(data_row, _parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[2])

    if in_row[3] == "deposit" and in_row[0] != "":
        # Check for txid to filter failed transactions
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[7],
                                                 buy_asset=normalise_asset(in_row[6]),
                                                 fee_quantity=in_row[8],
                                                 fee_asset=normalise_asset(in_row[6]),
                                                 wallet=WALLET)
    elif in_row[3] == "withdrawal" and in_row[0] != "":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[7])),
                                                 sell_asset=normalise_asset(in_row[6]),
                                                 fee_quantity=in_row[8],
                                                 fee_asset=normalise_asset(in_row[6]),
                                                 wallet=WALLET)
    elif in_row[3] == "transfer" and in_row[0] != "":
        if float(in_row[7]) >= 0:
            # Positive transfers are forks and airdrops
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[7],
                                                     buy_asset=normalise_asset(in_row[6]),
                                                     fee_quantity=in_row[8],
                                                     fee_asset=normalise_asset(in_row[6]),
                                                     wallet=WALLET)
        else:
            # Negative transfers are unlisted assets
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                     data_row.timestamp,
                                                     sell_quantity=abs(Decimal(in_row[7])),
                                                     sell_asset=normalise_asset(in_row[6]),
                                                     fee_quantity=in_row[8],
                                                     fee_asset=normalise_asset(in_row[6]),
                                                     wallet=WALLET)

def parse_kraken_trades(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[3])

    base_asset, quote_asset = split_trading_pair(in_row[2])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(2, parser.in_header[2], in_row[2])

    if in_row[4] == "buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[9],
                                                 buy_asset=normalise_asset(base_asset),
                                                 sell_quantity=in_row[7],
                                                 sell_asset=normalise_asset(quote_asset),
                                                 fee_quantity=in_row[8],
                                                 fee_asset=normalise_asset(quote_asset),
                                                 wallet=WALLET)
    elif in_row[4] == "sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[7],
                                                 buy_asset=normalise_asset(quote_asset),
                                                 sell_quantity=in_row[9],
                                                 sell_asset=normalise_asset(base_asset),
                                                 fee_quantity=in_row[8],
                                                 fee_asset=normalise_asset(quote_asset),
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(4, parser.in_header[4], in_row[4])


def split_trading_pair(trading_pair):
    for quote_asset in sorted(QUOTE_ASSETS, reverse=True):
        if trading_pair.endswith(quote_asset):
            return trading_pair[:-len(quote_asset)], quote_asset

    return None, None

def normalise_asset(asset):
    if asset in ALT_ASSETS:
        asset = ALT_ASSETS.get(asset)

    if asset == "XBT":
        return "BTC"
    return asset

DataParser(DataParser.TYPE_EXCHANGE,
           "Kraken Deposits/Withdrawals",
           ['txid', 'refid', 'time', 'type', 'subtype', 'aclass', 'asset', 'amount', 'fee',
            'balance'],
           worksheet_name="Kraken D,W",
           row_handler=parse_kraken_deposits_withdrawals)

DataParser(DataParser.TYPE_EXCHANGE,
           "Kraken Trades",
           ['txid', 'ordertxid', 'pair', 'time', 'type', 'ordertype', 'price', 'cost', 'fee', 'vol',
            'margin', 'misc', 'ledgers', 'postxid', 'posstatus', 'cprice', 'ccost', 'cfee', 'cvol',
            'cmargin', 'net', 'trades'],
           worksheet_name="Kraken T",
           row_handler=parse_kraken_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "Kraken Trades",
           ['txid', 'ordertxid', 'pair', 'time', 'type', 'ordertype', 'price', 'cost', 'fee', 'vol',
            'margin', 'misc', 'ledgers'],
           worksheet_name="Kraken T",
           row_handler=parse_kraken_trades)
