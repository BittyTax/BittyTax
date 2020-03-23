![BittyTax logo](https://github.com/BittyTax/BittyTax/raw/master/img/BittyTax.png)
[![Version badge][version-badge]][version] [![License badge][license-badge]][license] [![Python badge][python-badge]][python] [![Discord badge][discord-badge]][discord]
# BittyTax
BittyTax is a collection of command-line tools to help you manage your cryptoasset accounts. Allowing you to audit, value and calculate your annual UK Capital Gains and Income Tax.

This tool is designed to be used by someone who is already familiar with cryptoasset taxation rules in the UK. HMRC has published guidance, some useful links are provided in the [Resources](#resources) section at the end.

BittyTax comprises of 3 different tools.

1. `bittytax` - process transaction records, audit accounts, provide a tax summary for each year and display the current value of your cryptoasset portfolio (see [Accounting Tool](#accounting-tool)) 

2. `bittytax_conv` - converts data files from many different wallets and exchanges into the bittytax transaction record format (see [Conversion Tool](#conversion-tool))

3. `bittytax_price` - (optional) lookup historic price data for cryptoassets and foreign currencies (see [Price Tool](#price-tool))

## Disclaimer
This software is copyright (c) Nano Nano Ltd, and licensed for use under the AGPLv3 License, see [LICENSE](https://github.com/BittyTax/BittyTax/blob/master/LICENSE) file for details.

Nano Nano Ltd does not provide tax, legal, accounting or financial advice. This software and its content are provided for information only, and as such should not be relied upon for tax, legal, accounting or financial advice.

You should obtain specific professional advice from a professional accountant, tax or legal/financial advisor before you take any action.

This software is provided 'as is', Nano Nano Ltd does not give any warranties of any kind, express or implied, as to the suitability or usability of this software, or any of its content.

## Getting Started

### Prerequisites
You need to have Python 2.7 or 3.x installed on your machine before you can install BittyTax. MacOS and most Linux distributions already come with Python pre-installed.

If you need to install Python we recommend you install Python 3.x, see https://wiki.python.org/moin/BeginnersGuide/Download for instructions.

**Note:** BittyTax is currently in Beta version (see the [CHANGELOG](https://github.com/BittyTax/BittyTax/blob/master/CHANGELOG.md) file for details) it has been tested on MacOS and Windows 10, using both Python 2.7, and Python 3.7.

### Installing

To install the latest release:
```console
    $ pip install BittyTax
```

or [download the ZIP file](https://github.com/BittyTax/BittyTax/archive/master.zip), unpack, navigate to the top level of the repository and install using:

```console
    $ python setup.py install
```

Note: This will install the latest unreleased version which may include untested changes, check the [CHANGELOG](https://github.com/BittyTax/BittyTax/blob/master/CHANGELOG.md).

### Upgrade

To upgrade to the latest release:

```console
    $ pip install --upgrade BittyTax
```

## Transaction Records
BittyTax is only as accurate as the data you provide it, it is essential that you keep records of ALL cryptoasset transactions - not just trades but also records of spending, gifts send and received, etc.

The `bittytax_conv` tool is provided to assist with this transaction record keeping, it allows data exported from various different wallets and exchanges to be processed into the format required by the `bittytax` accounting tool. Manual entry or editing of this data may also be required. It is vital that converted data files are reviewed against the raw data and audited before use.

Transaction records can be stored in an Excel or CSV file. Excel is preferred as it makes editing and managing your data easier. Data can be split across multiple worksheets, for example, you might want to split up transactions by wallet or exchange, or by transaction type. With Excel you can also annotate your records, append additional data columns, or even include the original raw data for reference.

A transaction record is represented as a row of data which contains the following fields in the order given.

| Field | Type | Description |
| --- | --- | ---|
| Type | `Deposit` | Tokens deposited to a wallet you own  
| | `Mining` | Tokens received as income from mining |
| | `Income` | Tokens received as other income |
| | `Gift-Received` | Tokens received as a gift |
| | `Withdrawal` | Tokens withdrawn from a wallet you own |
| | `Spend` | Tokens spent on goods or services |
| | `Gift-Sent` | Tokens sent as a gift |
| | `Charity-Sent` | Tokens sent to a charity as a gift |
| | `Trade` | Tokens exchanged for another token or fiat currency |
| Buy Quantity | | Quantity of the asset acquired |
| Buy Asset | | Symbol name of the asset acquired |
| Buy Value | | Value in UK pounds (GBP) of the asset acquired |
| Sell Quantity | |  Quantity of the asset disposed |
| Sell Asset | | Symbol name  of the asset disposed |
| Sell Value | | Value in UK pounds (GBP) of the asset disposed |
| Fee Quantity | | Quantity of the fee |
| Fee Asset | | Symbol name of the asset used for fees |
| Fee Value | | Value in UK ponds (GBP) of the fee |
| Wallet | | Name of wallet |
| Timestamp | | Date/time of transaction |

The transaction Type dictates which fields in the row are required, either (M)andatory or (O)ptional.   

| Type | Buy Quantity | Buy Asset | Buy Value | Sell Quantity | Sell Asset | Sell Value | Fee Quantity | Fee Asset | Fee Value | Wallet | Timestamp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---| --- |
| `Deposit` | M | M |   |||| O | O |  | O | M |
| `Mining` | M | M | O |||| O | O | O| O | M |
| `Income` | M | M | O |||| O | O | O| O | M |
| `Gift-Received` | M | M | O |||| O | O | O| O | M |
| `Withdrawal` |||| M | M |   | O | O |   | O | M |
| `Spend` |||| M | M | O | O | O | O | O | M |
| `Gift-Sent` |||| M | M | O | O | O | O | O | M |
| `Charity-Sent` |||| M | M | O | O | O | O | O | M |
| `Trade` | M | M | O | M | M | O | O | O | O | O | M

- If fees are specified, the Buy or Sell Quantity should be the gross amount (i.e. prior to any fee adjustment).

- The Buy Value, Sell Value and Fee Value fields are always optional, if you don't provide a fixed value, bittytax will calculate the value for you via one of it's price data sources.

- Wallet name is optional, but recommended if you want to audit your cryptoasset balances across multiple wallets.  

- Timestamp should be in the format `YYYY-MM-DDTHH:MM:SS ZZZ`, recognised timezones (ZZZ) are GMT, BST and UTC.

- Cryptoasset symbol names need to be consistent throughout your transaction records. For example, Bitcoin Cash was referred to as both BCC and BCH at the time of the first fork, but also more recently as BCHABC or BAB. The symbol name you choose should match the symbol name used by the price data source, otherwise valuations will fail, see [Price Tool](#price-tool) for more information.

- Transaction records can be listed in any order, bittytax will sort them by Timestamp before processing.

Example files are provided in both [Excel](https://github.com/BittyTax/BittyTax/blob/master/data/example.xlsx) and [CSV](https://github.com/BittyTax/BittyTax/blob/master/data/example.csv) format.

### Deposit
A `Deposit` is a transfer transaction record, indicating the receipt of cryptoasset tokens to a wallet you control. For example, you might have deposited tokens to a wallet on an exchange, ready to be traded.

Deposit should NOT be used to record transfers to someone else's wallet, this would be categorised as either a `Gift-Sent` or  a `Spend`. 

There should be an equivalent `Withdrawal` transaction record for every deposit, since tokens are always moving out of one wallet into another. The quantity of tokens deposited will normally be less than the quantity withdrawn due to network transaction fees. Deposits and Withdrawals are not taxable events. 

The Deposit type can also be used to record fiat deposits into an exchange, although this is not used for tax calculations it will be used for auditing purposes.

### Withdrawal
A `Withdrawal` is a transfer transaction record, it indicates tokens being sent from a wallet you control. It is always used in combination with a `Deposit` transaction.

The Withdrawal type can also be used to record fiat withdrawals from an exchange.

### Mining
The `Mining` transaction type is used to identify tokens received as income from mining. The `Income` transaction type could also be used to record this, its use is purely descriptive.

These transaction records will appear within your income tax report.

### Income
The `Income` transaction type is used to identify tokens received as other income.

These transaction records will appear within your income tax report.

### Gift-Received
The `gift-received` transaction type is used to record cryptoasset tokens received as a gift.

A gift received is not taxed as income.

### Spend
A `Spend` is a disposal transaction record, it's used to capture the spending of tokens on goods or services.

As a disposal transaction, it is applicable for Capital Gains tax.

### Gift-Sent
A `Gift-Sent` is a disposal transaction record, it identifies cryptoasset tokens sent as a gift.

As a disposal transaction, it is applicable for Capital Gains tax.

### Charity-Sent
A `Charity-Sent` is a disposal transaction record, it identifies cryptoasset tokens sent to a charity as a gift. It's handling is the same as a `Gift-Sent`, it's purpose is purely descriptive.

### Trade
The `Trade` transaction type records the exchange of one cryptoasset for another, or for fiat currency.

This could be for one for the following reasons.

- Fiat-to-crypto *(acquisition)*
- Crypto-to-crypto *(disposal)*
- Crypto-to-fiat *(disposal)*

In the case of a fiat-to-crypto trade, the Sell Asset would be fiat, i.e. GBP, or whatever currency you used, and Sell Quantity would contain the amount. There is no reason to specify the Sell Value if the currency is GBP.

In the opposite case, crypto-to-fiat, the Buy Asset would be fiat, and the Buy Quantity the amount in fiat.

Trades which are a *disposal* are applicable for Capital Gains tax.

### Other types?
Below is a list of some other situations which you might need to record, but which don't have a specific transaction type defined. These could be added in the future if users feel it would be of benefit.

1. **Airdrop** - These tokens can be recorded as either a `Gift-Received`, if nothing was done in return for them, or `Income` if the distribution of tokens was dependant upon providing a service or other conditions, see [HMRC Guidance on Airdrops](https://www.gov.uk/government/publications/tax-on-cryptoassets/cryptoassets-for-individuals#airdrops).  
1. **Dust clean** - Some exchanges remove very small amounts (dust) of cryptoasset tokens from wallets after a period of time, since these are too small to be traded or withdrawn. This can be captured as a `Spend` with a Sell Value of 0.  
1. **Fork** - If a cryptoasset you own forks, and a new cryptoasset is created, this can be recorded as a `Gift-Received` but with a Buy Value of 0. This assumes that you are not splitting the cost between the original and new cryptoasset. Currently it is not possible to derive a cost from the original cryptoasset and apportion this to the new one. See [HMRC Guidance on Blockchain forks](https://www.gov.uk/government/publications/tax-on-cryptoassets/cryptoassets-for-individuals#fork).
1. **Gift to spouse** - If cryptoasset tokens are gifted to your spouse, it can be recorded as a `Gift-Sent` but with a Sell Value of 0.
1. **Margin funding** - Tokens received from an exchange in return for margin funding can be captured as `Income`.
1. **Lost** - Tokens which have been lost, i.e. the private keys are unrecoverable, have to be reported/accepted by HMRC as a *"negligible value claim"*. These are treated as a disposal, followed by a re-acquisition for the amount lost, since technically you still own the cryptoasset. This can be recorded as a crypto-to-fiat `Trade` with a GBP cost of 0, followed by a fiat-to-crypto `Trade` for exactly the same quantity of the cryptoasset, also with a cost of 0. See [HMRC Guidance on losing public and private keys](https://www.gov.uk/government/publications/tax-on-cryptoassets/cryptoassets-for-individuals#losing-public-and-private-keys).
1. **Staking** - Tokens received from Proof of Stake (POS) can be recorded as `Mining` or `Income`.

## Accounting Tool
Once you have all of your transaction records stored in an Excel or CSV file you can use `bittytax` to process them.

    bittytax <filename>

There are additional command line arguments which you can use, to see all these use the help command.

    bittytax --help

The `-ty` or `--taxyear` argument tells bittytax to only output a tax summary for the year you specify, by default tax summaries will be produced for all years which contain taxable events.

    bittytax <filename> -ty 2020

You can turn on debug using the `-d` or `--debug` command argument, this causes bittytax to produce detailed logging of the transaction records, the audit and tax calculations. 

The accounting tool performs the following functions:

1. [Import Transaction Records](#import-transaction-records)
2. [Audit Transaction Records](#audit-transaction-records)
3. [Split Transaction Records](#split-transaction-records)
3. [Pool Same Day](#pool-same-day)
4. [Match "same day" Rule](#match-same-day-rule)
5. [Match "bed and breakfast" Rule](#match-bed-and-breakfast-rule)
6. [Process Unmatched (Section 104)](#process-unmatched-section-104)
7. [Process Income](#process-income)
8. [Tax Summary Report](#tax-summary-report) (for each year)
9. [Current Holdings Report](#current-holdings-report)

### Import Transaction Records
First the transaction records are imported, and validated according to their transaction type, making sure that the correct mandatory and optional fields are included. Empty rows are allowed, they are filtered out during the import.

#### Logging
If you enable debug logging you will see if bittytax has correctly loaded your transaction records from the file.

As you can see in the example below, the worksheet name (Excel only) and row number are given along with the row data.

Each row is given a unique Transaction ID, these are allocated in chronological order, regardless of the ordering in your file. So the first transaction you ever made will be TID:1.

```
INFO -- : ==IMPORT TRANSACTION RECORDS FROM EXCEL FILE: example.xlsx ==
DEBUG -- : 'Sheet1' Row[2]: ['Deposit', '870.0', 'GBP', '', '', '', '', '', '', '', 'LocalBitcoins', '2013-05-24T20:16:46 UTC'] TID:1
DEBUG -- : 'Sheet1' Row[3]: ['Trade', '10.0', 'BTC', '', '870.0', 'GBP', '', '', '', '', 'LocalBitcoins', '2013-05-24T20:17:40 UTC'] TID:2
DEBUG -- : 'Sheet1' Row[4]: ['Withdrawal', '', '', '', '10.0', 'BTC', '', '', '', '', 'LocalBitcoins', '2013-05-24T20:20:49 UTC'] TID:3
DEBUG -- : 'Sheet1' Row[5]: ['Deposit', '10.0', 'BTC', '', '', '', '', '', '', '', 'Desktop wallet', '2013-05-24T21:20:49 BST'] TID:4
DEBUG -- : 'Sheet1' Row[6]: ['Deposit', '2693.8', 'USD', '', '', '', '', '', '', '', 'Bitstamp', '2014-05-29T08:33:00 UTC'] TID:5
DEBUG -- : 'Sheet1' Row[7]: ['Spend', '', '', '', '0.002435', 'BTC', '0.8', '', '', '', 'Desktop wallet', '2014-06-26T12:25:02 BST'] TID:6
DEBUG -- : 'Sheet1' Row[8]: ['Gift-Sent', '', '', '', '0.02757', 'BTC', '', '', '', '', 'Desktop wallet', '2014-07-18T14:12:47 BST'] TID:7
DEBUG -- : 'Sheet1' Row[9]: ['Trade', '0.41525742', 'BTC', '', '257.53', 'USD', '', '1.29', 'USD', '', 'Bitstamp', '2014-07-23T10:58:00 UTC'] TID:8
DEBUG -- : 'Sheet1' Row[10]: ['Trade', '0.58474258', 'BTC', '', '362.63', 'USD', '', '1.82', 'USD', '', 'Bitstamp', '2014-07-23T10:58:00 UTC'] TID:9
```
### Audit Transaction Records
The audit function takes the imported transaction records, and then replays them in chronological order.

The simulation of tokens (and also fiat) being moved between your wallets allows you to compare the calculated balances against your real world wallets and exchange balances.

```console
INFO -- : ==FINAL AUDIT BALANCES==
INFO -- : Bitstamp:BTC=0
INFO -- : Bitstamp:USD=0
INFO -- : Coinfloor:BTC=0
INFO -- : Coinfloor:GBP=0
INFO -- : Desktop wallet:BTC=13.11024863
INFO -- : LocalBitcoins:BTC=0
INFO -- : LocalBitcoins:GBP=0
INFO -- : Poloniex:BTC=2.89354264
INFO -- : Poloniex:ETH=248.60854866
INFO -- : Poloniex:XRP=19,037.77593453
```

If they don't match, it could be that your transaction records are incomplete.

Bittytax will raise a warning if a cryptoasset balance goes negative, this could happen if the time ordering of your transaction records is not accurate.

If you do get issues, you can turn on debug to produce detailed logging of the audit. You can then see what impact each individual transaction record has on your wallets.

In the debug example, you can see that for each transaction record (TR) the lines below show which wallets have been updated. The wallet name and asset name is displayed with its balance, and in brackets the quantity that has been added or subtracted.

```console
DEBUG -- : ==FULL AUDIT TRANSACTIONS RECORDS==
...
DEBUG -- : TR [TID:8] Trade: 0.41525742 BTC <- 257.53 USD + Fee=1.29 USD 'Bitstamp' 2014-07-23T11:58:00 BST
DEBUG -- : Bitstamp:BTC=0.41525742 (+0.41525742)
DEBUG -- : Bitstamp:USD=2,436.27 (-257.53)
DEBUG -- : Bitstamp:USD=2,434.98 (-1.29)
DEBUG -- : TR [TID:9] Trade: 0.58474258 BTC <- 362.63 USD + Fee=1.82 USD 'Bitstamp' 2014-07-23T11:58:00 BST
DEBUG -- : Bitstamp:BTC=1 (+0.58474258)
DEBUG -- : Bitstamp:USD=2,072.35 (-362.63)
DEBUG -- : Bitstamp:USD=2,070.53 (-1.82)
DEBUG -- : TR [TID:10] Trade: 0.86 BTC <- 521.16 USD + Fee=2.51 USD 'Bitstamp' 2014-07-24T14:08:00 BST
DEBUG -- : Bitstamp:BTC=1.86 (+0.86)
DEBUG -- : Bitstamp:USD=1,549.37 (-521.16)
DEBUG -- : Bitstamp:USD=1,546.86 (-2.51)
DEBUG -- : TR [TID:11] Trade: 0.9 BTC <- 545.7 USD + Fee=2.51 USD 'Bitstamp' 2014-07-24T14:08:00 BST
DEBUG -- : Bitstamp:BTC=2.76 (+0.9)
DEBUG -- : Bitstamp:USD=1,001.16 (-545.7)
DEBUG -- : Bitstamp:USD=998.65 (-2.51)
DEBUG -- : TR [TID:12] Trade: 1.64037953 BTC <- 994.07 USD + Fee=4.58 USD 'Bitstamp' 2014-07-24T14:09:00 BST
DEBUG -- : Bitstamp:BTC=4.40037953 (+1.64037953)
DEBUG -- : Bitstamp:USD=4.58 (-994.07)
DEBUG -- : Bitstamp:USD=0 (-4.58)
DEBUG -- : TR [TID:13] Withdrawal: 4.40037953 BTC 'Bitstamp' 2014-07-24T22:01:00 BST
DEBUG -- : Bitstamp:BTC=0 (-4.40037953)
```

Although important, the audit function can be disabled using the `-s` or `--skipaudit` command argument to speed up the tax reporting.

### Split Transaction Records
Before any tax calculations can take place, transaction records need to be split into their constitute parts, in terms of cryptoasset Buys and cryptoasset Sells, each with their own valuation in GBP.

This requires the buy, sell and fee assets each to be given valuations, that is unless a fixed value has already been specified, or the asset is already in GBP.

Valuations are calculated via one of the different historic price date sources, see [Price Tool](#price-tool) for how.

Note that `Deposit` and `Withdrawal` transactions are not taxable events so no valuation is required.

#### Fee Handling

Each cryptoasset Buy or Sell can include a fee. Its value is populated by the fee specified in the transaction record.

If a transaction record involves more than one cryptoasset (i.e. a `Trade` crypto-to-crypto) then the fee's valuation has to be split evenly between the Buy and Sell transactions.

If the fee asset is also a cryptoasset, then paying the fee counts as a separate disposal. This is recorded by adding an additional Sell transaction as a `Spend`.

Since `Deposit` and `Withdrawal` transactions are not taxable, any additional `Spend` transactions created for these are also flagged as not taxable.

#### Logging
By enabling debug logging you can check that transaction records have been split correctly into Buys and Sells, and that the correct valuations have been given.

Non-taxable transactions are marked with an asterisk * and have no GBP valuation.

All GBP values are displayed to 2 decimal places, although no actual rounding takes place until a taxable event is recorded.

Transaction IDs for Buys and Sells are made up from the parent transaction ID with a unique sub-ID, i.e. (1.1, 1.2, etc).

```console
DEBUG -- : ==SPLIT TRANSACTION RECORDS==
...
DEBUG -- : TR [TID:32] Withdrawal: 7.0002 BTC 'Desktop wallet' 2017-03-24T22:57:44 GMT
DEBUG -- : T-Sell* [TID:32.1] Withdrawal: 7.0002 BTC + Fee=£0.00 GBP 'Desktop wallet' 2017-03-24T22:57:44 GMT
DEBUG -- : TR [TID:33] Deposit: 7 BTC 'Poloniex' 2017-03-24T22:57:44 GMT
DEBUG -- : T-Buy* [TID:33.1] Deposit: 7 BTC + Fee=£0.00 GBP 'Poloniex' 2017-03-24T22:57:44 GMT
DEBUG -- : TR [TID:34] Trade: 1.00000013 ETH <- 0.03729998 BTC + Fee=0.0015 ETH 'Poloniex' 2017-04-12T20:38:26 BST
DEBUG -- : Price on 2017-04-12, 1 BTC=969.6202 GBP via CoinDesk (Bitcoin)
DEBUG -- : Price on 2017-04-12, 1 BTC=£969.62 GBP, 0.03729998 BTC=£36.17 GBP
DEBUG -- : T-Buy [TID:34.1] Trade: 1.00000013 ETH (£36.17 GBP) + Fee=£0.03 GBP 'Poloniex' 2017-04-12T20:38:26 BST
DEBUG -- : T-Sell [TID:34.2] Trade: 0.03729998 BTC (£36.17 GBP) + Fee=£0.03 GBP 'Poloniex' 2017-04-12T20:38:26 BST
DEBUG -- : T-Sell [TID:34.3] Spend: 0.0015 ETH (£0.05 GBP) + Fee=£0.00 GBP 'Poloniex' 2017-04-12T20:38:26 BST
```

### Pool Same Day
HMRC stipulates that ["*All shares of the same class in the same company acquired by the same person on the same day and in the same capacity are treated as though they were acquired by a single transaction*"](https://www.gov.uk/hmrc-internal-manuals/capital-gains-manual/cg51560#IDATX33F) this applies in the same way to disposals.

#### Pooling
Tokens of the same cryptoasset, acquired on the same day, are pooled together into a single Buy transaction, the same applies for tokens disposed of on the same day. These are pooled into a single Sell transaction.

Only taxable transactions (i.e. acquisitions and disposals) are included within these pools.

All timestamps are normalised to be in local time (GMT or BST) so that the same day calculation is correct.

Pooled transactions are indicated by the transaction count at the end, shown within square brackets. The transactions contained within the pool are indented below it.

```console
DEBUG -- : ==POOL SAME DAY TRANSACTIONS==
DEBUG -- : T-Buy [TID:2.1] Trade: 10 BTC (£870.00 GBP) + Fee=£0.00 GBP 'LocalBitcoins' 2013-05-24T21:17:40 BST
DEBUG -- : T-Sell* [TID:3.1] Withdrawal: 10 BTC + Fee=£0.00 GBP 'LocalBitcoins' 2013-05-24T21:20:49 BST
DEBUG -- : T-Buy* [TID:4.1] Deposit: 10 BTC + Fee=£0.00 GBP 'Desktop wallet' 2013-05-24T21:20:49 BST
DEBUG -- : T-Sell [TID:6.1] Spend: 0.002435 BTC (£0.80 GBP) + Fee=£0.00 GBP 'Desktop wallet' 2014-06-26T12:25:02 BST
DEBUG -- : T-Sell [TID:7.1] Gift-Sent: 0.02757 BTC (£10.14 GBP) + Fee=£0.00 GBP 'Desktop wallet' 2014-07-18T14:12:47 BST
DEBUG -- : T-Buy [TID:8.1] Trade: 1 BTC (£364.22 GBP) + Fee=£1.83 GBP 'Bitstamp' 2014-07-23T11:58:00 BST [2]
DEBUG -- :   T-Buy [TID:8.1] Trade: 0.41525742 BTC (£151.25 GBP) + Fee=£0.76 GBP 'Bitstamp' 2014-07-23T11:58:00 BST
DEBUG -- :   T-Buy [TID:9.1] Trade: 0.58474258 BTC (£212.97 GBP) + Fee=£1.07 GBP 'Bitstamp' 2014-07-23T11:58:00 BST
```

### Match "same day" Rule
See ["*The “same day” rule TCGA92/S105(1)*"](https://www.gov.uk/hmrc-internal-manuals/capital-gains-manual/cg51560#IDATX33F).

This tax function matches any Buy and Sell transactions, of the same cryptoasset, that occur on the same day. 

If the buy and sell quantities do not match, the transaction with the larger quantity will be split into two, and the cost and fee apportioned between them.

This allows a gain, or a loss, to be calculated for the matching transactions, taking into consideration the combined fees. The transaction containing the remainder is then carried forward, and used in further tax calculations.

#### Logging
With debug enabled you can see which transactions have been "*Same Day*" matched, and where a Buy or Sell has been split.  

Any new transactions created by splits are allocated a new TID containing the next sub-ID in sequence.

```console
DEBUG -- : ==MATCH SAME DAY TRANSACTIONS==
...
DEBUG -- : T-Sell [TID:34.3] Spend: 0.62207655 ETH (£22.50 GBP) + Fee=£0.00 GBP 'Poloniex' 2017-04-12T20:38:26 BST [4]
DEBUG -- : T-Buy [TID:34.1] Trade: 249.23062521 ETH (£9,012.71 GBP) + Fee=£11.25 GBP 'Poloniex' 2017-04-12T20:38:26 BST [4] (Same Day)
DEBUG -- : split: T-Buy [TID:34.4] Trade: 0.62207655 ETH (£22.50 GBP) + Fee=£0.03 GBP 'Poloniex' 2017-04-12T20:38:26 BST [4]
DEBUG -- : split: T-Buy [TID:34.5] Trade: 248.60854866 ETH (£8,990.22 GBP) + Fee=£11.22 GBP 'Poloniex' 2017-04-12T20:38:26 BST [4]
DEBUG -- :  Gain=£-0.03 (proceeds=£22.50 - cost=£22.50 - fees=£0.03)
```

### Match "bed and breakfast" Rule

See ["*The “bed and breakfast” rule TCGA92/S106A(5) and (5A)*"](https://www.gov.uk/hmrc-internal-manuals/capital-gains-manual/cg51560#IDATR33F).
 
This tax functions matches sells to buybacks of the same cryptoasset which occur within 30 days.

As with the ["same day"](#match-same-day-rule) rule, if the buy and sell quantities do not match, the transactions will be split. 

Transactions are sorted by timestamp, and matched in chronological order.

Any matched "same day" transactions are excluded from this rule.

#### Logging
With debug enabled you can see which transactions have been matched by the "*Bed & Breakfast*" rule, and the number of days between the Sell and Buy back.   

```console
DEBUG -- : ==MATCH BED & BREAKFAST TRANSACTIONS==
...
DEBUG -- : T-Sell [TID:18.2] Trade: 5.32294271 BTC (£1,474.69 GBP) + Fee=£1.47 GBP 'Poloniex' 2016-01-27T22:09:19 GMT [5]
DEBUG -- : T-Buy [TID:23.5] Trade: 5.54195456 BTC (£1,471.32 GBP) + Fee=£1.47 GBP 'Poloniex' 2016-01-29T13:51:01 GMT [9] (Bed & Breakfast, 2 days)
DEBUG -- : split: T-Buy [TID:23.6] Trade: 5.32294271 BTC (£1,413.17 GBP) + Fee=£1.41 GBP 'Poloniex' 2016-01-29T13:51:01 GMT [9]
DEBUG -- : split: T-Buy [TID:23.7] Trade: 0.21901185 BTC (£58.14 GBP) + Fee=£0.06 GBP 'Poloniex' 2016-01-29T13:51:01 GMT [9]
DEBUG -- :  Gain=£58.63 (proceeds=£1,474.69 - cost=£1,413.17 - fees=£2.89)
```

### Process Unmatched (Section 104)
Any transactions which remain unmatched are processed according to Section 104 Taxation of Capital Gains Act 1992.

Each cryptoasset is held in its own pool, known as a Section 104 holding, the unmatched transactions are processed in chronological order.

As tokens are acquired, the total cost and total fees for that cryptoasset holding increases.

If all tokens in a holding are disposed of, the cost will be the total cost of that cryptoasset holding, and likewise, the fees would be the total fees.

If only some tokens are disposed of, the cost is calculated as a fraction of the total cost. This fraction is calculated by the number of tokens disposed of, divided by the total number of tokens held. The fees are also calculated as a fraction in the same way.

The gain or loss, is then calculated by subtracting this cost and any fees from the proceeds of the disposal. Fees are included from both the Section 104 holding (acquisition fees) and also the disposal fee.

For non-taxable transactions such as `Withdrawal` and `Deposit`, the tokens are removed, and then re-added to the holding, but at zero cost. 

**NOTE:** It is important that no disposal event happens to a holding between a `Withdrawal` and a `Deposit`. This is because the tokens are removed temporarily, so would impact the cost calculation. The ordering of transactions can be checked in the debug log.

#### Logging
Before the Section 104 calculations, all the updated transactions are displayed for clarity, this includes any new "split" transactions which have been added by the matching function. This output is sorted by asset and timestamp.

The transactions which have been matched, and so excluded from the Section 104 holding, are denoted with (M) at the end.
```console
DEBUG -- : ==UPDATED TRANSACTIONS==
DEBUG -- : T-Buy [TID:2.1] Trade: 10 BTC (£870.00 GBP) + Fee=£0.00 GBP 'LocalBitcoins' 2013-05-24T21:17:40 BST
DEBUG -- : T-Sell* [TID:3.1] Withdrawal: 10 BTC + Fee=£0.00 GBP 'LocalBitcoins' 2013-05-24T21:20:49 BST
DEBUG -- : T-Buy* [TID:4.1] Deposit: 10 BTC + Fee=£0.00 GBP 'Desktop wallet' 2013-05-24T21:20:49 BST
DEBUG -- : T-Sell [TID:6.1] Spend: 0.002435 BTC (£0.80 GBP) + Fee=£0.00 GBP 'Desktop wallet' 2014-06-26T12:25:02 BST (M)
DEBUG -- : T-Sell [TID:7.1] Gift-Sent: 0.02757 BTC (£10.14 GBP) + Fee=£0.00 GBP 'Desktop wallet' 2014-07-18T14:12:47 BST (M)
DEBUG -- : T-Buy [TID:8.2] Trade: 0.002435 BTC (£0.89 GBP) + Fee=£0.00 GBP 'Bitstamp' 2014-07-23T11:58:00 BST [2] (M)
DEBUG -- : T-Buy [TID:8.4] Trade: 0.02757 BTC (£10.04 GBP) + Fee=£0.05 GBP 'Bitstamp' 2014-07-23T11:58:00 BST [2] (M)
DEBUG -- : T-Buy [TID:8.5] Trade: 0.969995 BTC (£353.29 GBP) + Fee=£1.77 GBP 'Bitstamp' 2014-07-23T11:58:00 BST [2]
```

With debug enabled you can see detailed logging of the unmatched transactions being processed, and the impact it has on the individual holding.

Below each transaction it shows the cryptoasset holding, and by what amount the token, total cost and total fees are being updated.

When a disposal takes place, indicated at the end of the transaction, the gain calculation is then shown below. 

```console
DEBUG -- : ==PROCESS UNMATCHED TRANSACTIONS==
...
DEBUG -- : T-Buy [TID:18.5] Trade: 843.00981977 ETH (£1,471.74 GBP) + Fee=£1.47 GBP 'Poloniex' 2016-01-27T22:04:21 GMT [5]
DEBUG -- : ETH=843.00981977 (+843.00981977) cost=£1,471.74 GBP (+£1,471.74 GBP) fees=£1.47 GBP (+£1.47 GBP)
DEBUG -- : T-Sell [TID:23.2] Trade: 843.00981977 ETH (£1,474.27 GBP) + Fee=£1.47 GBP 'Poloniex' 2016-01-29T14:12:31 GMT [9] (Disposal)
DEBUG -- : ETH=0 (-843.00981977) cost=£0.00 GBP (-£1,471.74 GBP) fees=£0.00 GBP (-£1.47 GBP)
DEBUG -- :  Gain=£-0.42 (proceeds=£1,474.27 - cost=£1,471.74 - fees=£2.95)
```

### Process Income
This function searches through all the original transactions, and records any that are applicable for income tax. Currently this is only the `Mining` and `Income` transaction types.

These are then output in the tax summary report.

### Tax Summary Report
Once all the tax calculations are complete, the results are displayed either for all years, or for the tax year you specified via the command argument. 

Cryptoasset disposals are listed in date order. For a "bed and breakfast" disposal, the date of the buyback is shown in brackets.

Enough information is provided for you to complete the "Other property, assets and gains" section within your self assessment tax return, or to give to your accountant to complete.

The capital gains tax figure is shown purely as an estimate, at the 20% rate. Obviously you would need to take into account other capital gains/losses in the same year, and use the correct tax rate according to your income.

The reporting function will raise a warning if the disposal proceeds exceed more than 4 times the annual allowance for that tax year, as you can see in the example report below. HMRC requires you to report this in your self assessment even if the gain was within your annual allowance.

Lastly, all income events are listed in date order for that year, along with the total income and total fees. You should check with an accountant for how this should be reported according to your personal situation.

```console
INFO -- : ==TAX SUMMARY 2017/2018==
INFO -- : --CAPITAL GAINS--
INFO -- : Asset   Date       Disposal Type                                 Quantity          Cost          Fees      Proceeds          Gain
INFO -- : BTC     12/04/2017 Bed & Breakfast (10/05/2017)                    1.0003     £1,358.61         £1.21       £969.91      £-389.91
INFO -- : BTC     12/04/2017 Section 104                                 8.29479379     £1,388.01        £13.56     £8,042.80     £6,641.23
INFO -- : BTC     08/08/2017 Same Day                                          0.24       £637.93         £0.00       £637.93         £0.00
INFO -- : BTC     08/08/2017 Section 104                                       4.76       £796.52         £2.02    £12,652.31    £11,853.77
INFO -- : BTC     09/09/2017 Section 104                                 0.99999993       £167.34         £2.86     £3,251.91     £3,081.71
INFO -- : BTC     24/12/2017 Bed & Breakfast (02/01/2018)                         2    £21,692.50        £60.44    £20,147.00    £-1,605.94
INFO -- : ETH     12/04/2017 Same Day                                    0.62207655        £22.50         £0.03        £22.50        £-0.03
INFO -- : XRP     09/09/2017 Same Day                                   30.22974602         £4.88         £0.00         £4.88         £0.00
INFO -- : XRP     01/04/2018 Bed & Breakfast (05/04/2018)              914.84163064       £146.59         £0.18       £312.16       £165.39
INFO -- : XRP     01/04/2018 Section 104                             1,085.15836936       £175.10         £0.13       £370.28       £195.05
INFO -- : Number of disposals=10
INFO -- : Disposal proceeds=£46,411.68
WARNING -- : Assets sold are more than 4 times the annual allowance (£45,200.00), this needs to be reported to HMRC
INFO -- : Allowable costs=£26,470.41
INFO -- : Gains in the year, before losses=£21,937.15
INFO -- : Losses in the year=£1,995.88
INFO -- : --TAX ESTIMATE--
INFO -- : Taxable Gain=£8,641.27 (-£11,300.00 tax-free allowance)
INFO -- : Capital Gains Tax=£1,728.25 (20%)
INFO -- : --INCOME--
INFO -- : Asset   Date       Income Type                                   Quantity        Amount          Fees
INFO -- : BTC     10/05/2017 Income                                          1.0003     £1,358.61         £0.00
INFO -- : BTC     02/01/2018 Mining                                            12.5   £135,578.11         £0.00
INFO -- : Total income=£136,936.72
INFO -- : Total fees=£0.00
```

### Current Holdings Report
The current holdings report lists all your remaining cryptoasset balances, the cost (including fees) and their current valuation.

By default, empty wallets are excluded, this setting can be changed in the config file, see [Config](#config).

The data source used for the current price is the same as used for historic prices, see [Price Tool](#price-tool).

```console
INFO -- : ==CURRENT HOLDINGS==
INFO -- : Asset                    Quantity          Cost         Value  Data Source
INFO -- : BTC                   16.00379127   £114,261.62   £101,210.84  CoinDesk (Bitcoin)
INFO -- : ETH                  248.60854866     £9,012.71    £50,217.50  CryptoCompare (Ethereum)
INFO -- : XRP               19,037.77593453     £3,076.55     £6,009.08  CryptoCompare (XRP)
INFO -- : Total cost=£126,350.88
INFO -- : Total value=£157,437.42

```

## Conversion Tool
The bittytax conversion tool `bittytax_conv` takes all of the data files exported from your wallets and exchanges, normalises these into the transaction record format required by bittytax, and consolidates them into a single Excel spreadsheet for you to review, make edits, and add any missing records.

Don't worry if you don't have Microsoft Excel installed, these spreadsheets also work with [OpenOffice](https://www.openoffice.org) or [LibreOffice](https://www.libreoffice.org).

Each converted file appears within it's own worksheet, data files of the same format are aggregated together. The transaction records and the original raw data appear side by side, sorted by timestamp, making it easier for you to review and to provide traceability.

The converter takes care of all the cell formatting to ensure that all decimal places are displayed correctly, and if numbers exceed 15-digits of precision (an Excel limitation) they are stored as text to prevent any truncation.

For most wallet files, transactions can only be categorised as deposits or withdrawals. You will need to edit these to reflect your real transactions, i.e. spends, gifts, income, etc. With Excel it's easy, the valid options are selectable via a dropdown menu.

**Wallets:**
- Electrum
- Ledger Live
- Qt Wallet (i.e. Bitcoin Core)
- Trezor

**Exchanges:**
- Binance
- Bitfinex
- Bitstamp
- Bittrex
- ChangeTip 
- Circle
- Coinbase
- Coinbase Pro
- Coinfloor
- Cryptopia
- Cryptsy
- Gatehub
- HitBTC
- KuCoin
- OKEx
- Poloniex
- TradeSatoshi
- Uphold
- Wirex

**Explorers:**
- Etherscan

### Usage
The help command displays a full list of recognised data file formats, as well as details of all command line arguments.

    bittytax_conv --help

To use the conversion tool (assuming you've already exported your data), just enter the filenames of all your data files, in any order, as command arguments.

Most terminals allow you to drag and drop files from the desktop into the terminal window, this saves you time by giving you the correct file path without having to enter it manually.

    bittytax_conv <filename> [<filename> ...]

Each file is analysed to try and match it against one of the recognised formats. If successful, an Excel file will be generated with the default filename `BittyTax_Records.xlsx`. Unrecognised files are skipped and a warning displayed.

If you want to change the default filename you can use the `-o` argument followed by the output filename.

    bittytax_conv <filename> [<filename> ...] -o <output filename>

### Duplicate Records

For some exchanges you have to repeatedly download your transaction history, this can happen if the exchange only lets you run a report for the previous 3 months.

If you have multiple export files for the same exchange, these can all be passed into the conversion tool which by default will group them together into the same worksheet and sort them by timestamp.

If there is any overlap in the reporting period this can result in duplicate entries which will cause your data not to balance.

One solution is to manually remove these duplicates, another is for the conversion tool to do it for you by specifying the `--duplicates` argument.

This option should be used with care, since some exchange files can appear to have exact duplicates, but can be due to partially filled orders within the exact same time period, with same order id and even same amount!

### Unidentified Cryptoassets

Some wallet exports do not specify the actual cryptoasset being used. This will result in an error when the file is processed.

The `-ca` or `--cryptoasset` argument can be used to manually specify the asset.

    bittytax_conv -ca BTC <filename>

If you have multiple wallet files with this issue, you can either process each one individually, and then consolidate them into a single spreadsheet. Or you could edit the asset name in the spreadsheet for any which are incorrect.

### Output Formats

The default output format is Excel, but you can also choose CSV or RECAP by using the `--format` argument.

**CSV**

CSV is the legacy format used by bittytax which outputs transaction records directly into the terminal window, unless an output filename is specified.

A useful feature of the CSV format is that the output can be piped directly into bittytax.

    bittytax_conv --format CSV <filename> | bittytax

This will instantly show you what the remaining balance of each asset should be for that wallet or exchange file. Bear in mind that for some exchanges (I will try and list them below) the data provided will not balance exactly. This is probably due to the rounding used in the export file being different to that used internally by the exchange.

**Recap**

You can also use the conversion tool to convert your wallet or exchange files into the import CSV format used by Recap (see https://help.recap.io/en/articles/2631702-importing-csvs-into-custom-accounts).

    bittytax_conv --format RECAP <filename>

### Notes:
1. Some exchanges only allow the export of trades, this means transaction records of deposits and withdrawals will have to be created manually, otherwise the assets will not balance.
1. Bitfinex - when exporting your data, make sure the "*Date Format*" is set to "*DD-MM-YY*" which is the default.
1. ChangeTip - the conversion tool requires your username(s) to be configured, this is to identify which transactions are a gift received or a gift sent, (see [Config](#config)).
1. Coinbase - has many different export formats, bittytax recognises the "*Transactions history*" and "*Buys, sells, and merchant payouts*" reports (also known as "*Transfers*"). Coinbase provides these reports for each individual wallet (both fiat and crypto). It's possible to end up with duplicate transaction records (i.e. one for the GBP wallet and another for the BTC wallet), these have to be filtered manually, the converter will flag some of these duplicates it finds by setting the transaction type to Duplicate.
1. Coinbase Pro - the converter recognises both the "*Fills Report*" export for trades and the "*Account Report*" export for deposits and withdrawals. Please note, the "*Account Report*" also contains details of the trades ("*match*") but with less detail, these are filtered by the tool to prevent duplicates.
1. GateHub - some exports contain incomplete data (i.e. no counter asset in an "*exchange*"), these are possibly failed transactions, the tool will filter them and raise a warning for you to review, the data still appears to balance correctly. Any Ripple network fees which cannot be attributed to a "*payment*" or an "*exchange*" will be included separately as a Spend transaction record.
1. Qt Wallet - by default, unconfirmed transactions are filtered by the conversion tool, if you want to include them use the `-uc` or `--unconfirmed` command argument.
1. Exchanges which do not balance (just some dust left) are Cryptopia, OKEx, TradeSatoshi.

## Price Tool
The bittytax price tool `bittytax_price` allows you to lookup current and historic prices of cryptoassets and foreign currencies. Its use is not strictly required as part of the process of completing your accounts but provides a useful insight into the prices which bittytax will assign when it comes to value your cryptoassets in UK pounds.

**Data Sources:**
The following price data sources are used.

- [Exchange Rates API](https://exchangeratesapi.io) - foreign currency exchange rates *(primary fiat)*
- [Rates API](https://ratesapi.io) - foreign currency exchange rates *(secondary fiat)*
- [CoinDesk BPI](https://www.coindesk.com/api) - bitcoin price index *(primary bitcoin)*
- [Crypto Compare](https://min-api.cryptocompare.com) - cryptoasset prices *(primary crypto, secondary bitcoin)*
- [Coin Gecko](https://www.coingecko.com/en/api) - cryptoasset prices *(secondary crypto)*
- [Coin Paprika](https://coinpaprika.com/api/) - cryptoasset prices

The priority (primary, secondary, etc) to which data source is used and for which asset is controlled by the `bittytax.conf` config file, (see [Config](#config)). If your cryptoasset cannot be identified by the primary data source, the secondary source will be used, and so on. 

All price data is cached within the .bittytax/cache folder in your home directory, this is to prevent repeated lookups and reduce load on the APIs which could fail due to throttling.

### Usage
To use the tool you need to pass the asset symbol name, either for a cryptoasset (i.e. BTC) or a foreign currency (i.e. USD), the second argument is only required for historic data lookups, the date must be in the format (YYYY-MM-DD). If the date is not specified the current price will be returned.

    bittytax_price asset [date]

If the lookup is successful not only will the price be displayed in the terminal window, but also the data source used and the full name of the asset. This is useful in making sure the asset symbol you are using in your transaction records is the correct one.

```console
$ bittytax_price ETH
INFO -- : 1 ETH=£124.93 GBP via CryptoCompare (Ethereum)
```

Since there is no standardisation of cryptoasset symbols, it's possible that the same symbol has two different meanings across different data sources. For example, BTCP is Bitcoin Private on CryptoCompare, but also Bitcoin Pro on CoinGecko.

If bittytax is not picking up the correct price for you, you can change the config so that the asset symbol only uses the data source you require, see [Config](#config).   

You can use the help command argument to display a full list of the command line arguments. 

    bittytax_price --help

Another useful function of the price tool is to calculate the historic price of a specific transaction, you can use the `-q` or `--quantity` argument to specify the quantity to price, this can be used as a memory jogger if you are looking at old wallet transactions and trying to remember what it was you spent your crypto on.

```console
$ bittytax_price BTC 2014-06-24 -q 0.002435
INFO -- : 1 BTC=£338.59 GBP via CoinDesk (Bitcoin)
INFO -- : 0.002435 BTC=£0.82 GBP
```

### Notes:
1. Not all data source APIs return prices in UK pounds (GBP), for this reason cryptoasset prices are requested in BTC and then converted from BTC into UK pounds (GBP) as a two step process.
1. Some APIs return multiple prices for the same day, if this is the case then the 'close' price is always used.
1. Historical price data is held for each data source as a separate JSON file in the .bittytax/cache folder within your home directory.

## Config
The `bittytax.conf` file resides in the .bittytax folder within your home directory.

The [default](https://github.com/BittyTax/BittyTax/blob/master/config/bittytax.conf) file created at runtime should cater for most users.

If you need to change anything, the parameters are described below, the file is in YAML format.

| Parameter | Default | Description |
| --- | --- | --- |
| `fiat_list:` | `['GBP', 'EUR', 'USD']` | List of fiat symbols used |
| `crypto_list:` | `['BTC', 'ETH', 'XRP', 'LTC', 'BCH', 'USDT']` | List of prioritised cryptoasset symbols | 
| `trade_asset_type:` | `2` | Method used to calculate asset value in a trade |
| `show_empty_wallets:` | `True` | Include empty wallets in current holdings report |
| `transfers_include:` | `True` | Include transfer transactions in tax calculations |
| `data_source_select:` | `{'BTC': ['CoinDesk']}` | Map asset to a specific data source(s) for prices | 
| `data_source_fiat:` | `['ExchangeRatesAPI', 'RatesAPI']` | Default data source(s) to use for fiat prices |
| `data_source_crypto:` | `['CryptoCompare', 'CoinGecko']` | Default data source(s) to use for cryptoasset prices |
| `usernames:` | | List of usernames as used by ChangeTip |

### fiat_list
Used to differentiate between fiat and cryptoassets symbols, make sure you configure all fiat currencies which appear within your transaction records here.

### crypto_list
Identifies which cryptoasset takes priority when calculating the value of a crypto-to-crypto trade (see [trade_asset_type](#trade_asset_type)). The priority is taken in sequence, so in an ETH/BTC trade, the value of the Bitcoin would be used in preference to Ethereum when pricing the trade.

The list should contain the most prevalent cryptoassets which appear in exchange trading pairs, these are predominantly the higher market cap. tokens.

### trade_asset_type
Controls the method used to calculate the asset value of a trade:

- `0` = Buy asset value  
- `1` = Sell asset value  
- `2` = Priority asset value *(recommended)*  

For every trade there are always two assets involved, fiat-to-crypto, crypto-to-fiat or crypto-to-crypto. When bittytax is trying to calculate the value of a trade, it uses this parameter to determine which asset value should be used to price the trade in UK pounds.

For trades involving fiat, it's obvious that we want to price the asset using the fiat value, but for crypto-to-crypto trades it's not so straight forward. 

The recommended setting is `2` (Priority), this means that the asset value chosen will be selected according to the priority order defined by the `fiat_list` and `crypto_list` parameters combined. Fiat will always be chosen first, followed by the most prevalent cryptoasset.

Setting this parameter to `1` or `2` will result in either the buy asset value or the sell asset value always being used, regardless of whether the trades involved fiat or not. 

### show_empty_wallets
Include empty wallets in the current holdings report. Can be set to `True` or `False`.

### transfers_include
Include transfer transaction types (i.e. Deposit, Withdrawal) in tax calculations. Can be set to `True` (recommended) or `False`.

Although these transactions types are non-taxable they do affect the cost basis of your cryptoasset holding.

### data_source_select
Maps a specific asset symbol to a list of data sources in priority order.

This parameter overrides the any data sources defined by `data_source_fiat` and `data_source_crypto`, see below.

By default, only an entry for BTC exists, this selects CoinDesk as the primary data source for bitcoin prices, and CryptoCompare as the secondary. 

If, for example you wanted BTCP to use only the CoinGecko data source, you would change the config as follows.

```yaml
data_source_select: {
    'BTC': ['CoinDesk', 'CryptoCompare'],
    'BTCP': ['CoinGecko'],
    }
```

### data_source_fiat
Specifies which data source(s), in priority order, will be used for retrieving foreign currency exchange rates.

```yaml
data_source_fiat:
    ['ExchangeRatesAPI', 'RatesAPI']
```

Supported data sources for fiat are:
- `ExchangeRatesAPI`
- `RatesAPI`

### data_source_crypto
Specifies which data source(s), in priority order, will be used for retrieving cryptoasset prices.

```yaml
data_source_crypto:
    ['CryptoCompare', 'CoinGecko']
```

Supported data sources for cryptoassets are:
- `CoinDesk`
- `CryptoCompare`
- `CoinGecko`
- `CoinPaprika`

### usernames
This parameter is only used by the conversion tool.

It's required for ChangeTip data files, the list of username(s) is used to identify which transactions are gifts received and gifts sent.

An example is shown below.
```yaml
usernames:
    ['Bitty_Bot', 'BittyBot']
```

## Future
Ideas for the project roadmap, let me know what you would fine most useful, or any new features you would like to see.

### General
- Document code
- Add tests

### Conversion Tool
- Convert data from clipboard. Some wallets/exchanges don't provide an export function, it should be possible to copy the transaction data directly from the webpage and have the conversion tool analysis this data and then convert it into the transaction record format.
- Add exchange APIs to automatically convert new trades into the transaction record format.

### Price Tool
- Add command option to list supported cryptoassets symbols/names for a specific data source(s).

### Accounting Tool
- BittyTax integration with Excel. The command line interface is not for everyone, by integrating with Excel (or OpenOffice) this would greatly improve the user experience.
- Create a PDF file for the tax summary report which can be attached to your self assessment.
- Add export function for QuickBooks (QBXML format), to include transactions records with exchange rate data added.
- Tax rules for other countries

## Resources
**HMRC Links:**
- https://www.gov.uk/government/publications/tax-on-cryptoassets/cryptoassets-for-individuals
- https://www.gov.uk/guidance/check-if-you-need-to-pay-tax-when-you-receive-cryptoassets
- https://www.gov.uk/guidance/check-if-you-need-to-pay-tax-when-you-sell-cryptoassets
- https://www.gov.uk/guidance/non-cash-pay-shares-commodities-you-provide-to-your-employees
- https://www.gov.uk/hmrc-internal-manuals/vat-finance-manual/vatfin2330
- https://www.gov.uk/hmrc-internal-manuals/capital-gains-manual/cg12100
- https://www.gov.uk/government/publications/cryptoassets-taskforce

**HMRC Webinar**
- https://www.youtube.com/watch?v=EzNebqkw13w

[version-badge]: https://img.shields.io/pypi/v/BittyTax.svg
[license-badge]: https://img.shields.io/pypi/l/BittyTax.svg
[python-badge]: https://img.shields.io/pypi/pyversions/BittyTax.svg
[discord-badge]: https://img.shields.io/discord/581493570112847872.svg
[version]: https://pypi.org/project/BittyTax/
[license]: https://github.com/BittyTax/BittyTax/blob/master/LICENSE
[discord]: https://discord.gg/NHE3QFt
[python]: https://wiki.python.org/moin/BeginnersGuide/Download
