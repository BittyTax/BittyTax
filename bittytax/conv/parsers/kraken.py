# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020

from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError, UnexpectedTradingPairError

WALLET = "Kraken"

QUOTE_ASSETS = ['AUD', 'CAD', 'CHF', 'DAI', 'ETH', 'EUR', 'GBP', 'JPY', 'USD', 'USDC',
                'USDT', 'XBT', 'XETH', 'XXBT', 'ZAUD', 'ZCAD', 'ZEUR', 'ZGBP', 'ZJPY', 'ZUSD']

ALT_ASSETS = {'KFEE': 'FEE', 'XETC': 'ETC', 'XETH': 'ETH', 'XLTC': 'LTC', 'XMLN': 'MLN',
              'XREP': 'REP', 'XXBT': 'XBT', 'XXDG': 'XDG', 'XXLM': 'XLM', 'XXMR': 'XMR',
              'XXRP': 'XRP', 'XZEC': 'ZEC', 'ZAUD': 'AUD', 'ZCAD': 'CAD', 'ZEUR': 'EUR',
              'ZGBP': 'GBP', 'ZJPY': 'JPY', 'ZUSD': 'USD'}

def parse_kraken_deposits_withdrawals(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['time'])

    if row_dict['type'] == "deposit" and row_dict['txid'] != "":
        # Check for txid to filter failed transactions
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['amount'],
                                                 buy_asset=normalise_asset(row_dict['asset']),
                                                 fee_quantity=row_dict['fee'],
                                                 fee_asset=normalise_asset(row_dict['asset']),
                                                 wallet=WALLET)
    elif row_dict['type'] == "withdrawal" and row_dict['txid'] != "":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(row_dict['amount'])),
                                                 sell_asset=normalise_asset(row_dict['asset']),
                                                 fee_quantity=row_dict['fee'],
                                                 fee_asset=normalise_asset(row_dict['asset']),
                                                 wallet=WALLET)

def parse_kraken_trades(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['time'])

    base_asset, quote_asset = split_trading_pair(row_dict['pair'])
    if base_asset is None or quote_asset is None:
        raise UnexpectedTradingPairError(parser.in_header.index('pair'), 'pair', row_dict['pair'])

    if row_dict['type'] == "buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['vol'],
                                                 buy_asset=normalise_asset(base_asset),
                                                 sell_quantity=row_dict['cost'],
                                                 sell_asset=normalise_asset(quote_asset),
                                                 fee_quantity=row_dict['fee'],
                                                 fee_asset=normalise_asset(quote_asset),
                                                 wallet=WALLET)
    elif row_dict['type'] == "sell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['cost'],
                                                 buy_asset=normalise_asset(quote_asset),
                                                 sell_quantity=row_dict['vol'],
                                                 sell_asset=normalise_asset(base_asset),
                                                 fee_quantity=row_dict['fee'],
                                                 fee_asset=normalise_asset(quote_asset),
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('type'), 'type', row_dict['type'])

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
