![BittyTax logo](https://github.com/BittyTax/BittyTax/raw/master/img/BittyTax.png)
[![Version badge][version-badge]][version]
[![License badge][license-badge]][license]
[![Python badge][python-badge]][python]
[![Downloads badge][downloads-badge]][downloads]
[![Stars badge][github-stars-badge]][github-stars]
[![Twitter badge][twitter-badge]][twitter]
[![Discord badge][discord-badge]][discord]
[![Donation badge][donation-badge]][PayPal]
# BittyTax
BittyTax is a collection of command-line tools to help you calculate your cryptoasset taxes in the UK.

It's completely free to use, and retains your privacy as there is no need to share your data with a 3rd party.

BittyTax comprises of the following tools.

1. `bittytax` - process your transaction records and generate a PDF tax report (see [Accounting Tool](#accounting-tool)) 

2. `bittytax_conv` - convert your wallet and exchange files into transaction records (see [Conversion Tool](#conversion-tool))

3. `bittytax_price` - (optional) lookup historic price data for cryptoassets and foreign currencies (see [Price Tool](#price-tool))

This tool is designed to be used by someone who is already familiar with cryptoasset taxation rules in the UK. HMRC has published guidance on this. We've collected some useful links in the [Resources](#resources) section at the end.


## Disclaimer
This software is copyright (c) Nano Nano Ltd, and licensed for use under the AGPLv3 License, see [LICENSE](https://github.com/BittyTax/BittyTax/blob/master/LICENSE) file for details.

Nano Nano Ltd does not provide tax, legal, accounting or financial advice. This software and its content are provided for information only, and as such should not be relied upon for tax, legal, accounting or financial advice.

You should obtain specific professional advice from a professional accountant, tax or legal/financial advisor before you take any action.

This software is provided 'as is', Nano Nano Ltd does not give any warranties of any kind, express or implied, as to the suitability or usability of this software, or any of its content.

## Getting Started

### Prerequisites
You need to have Python 2.7 or 3.x installed on your machine before you can install BittyTax. MacOS and most Linux distributions already come with Python pre-installed.

If you need to install Python we recommend you install Python 3.8. See https://wiki.python.org/moin/BeginnersGuide/Download for instructions.

**Note:** BittyTax is currently in Beta version (see the [CHANGELOG](https://github.com/BittyTax/BittyTax/blob/master/CHANGELOG.md) file for details). It has been tested on MacOS and Windows 10, using both Python 2.7 and Python 3.8.

### Installing

To install the latest release:
```console
    $ pip install BittyTax
```

or [download the ZIP file](https://github.com/BittyTax/BittyTax/archive/master.zip), unpack, navigate to the top level of the repository and install using:

```console
    $ python setup.py install
```

Note: This will install the latest unreleased version which may include untested changes. Check the [CHANGELOG](https://github.com/BittyTax/BittyTax/blob/master/CHANGELOG.md) for more information.

### Upgrade

To upgrade to the latest release:

```console
    $ pip install --upgrade BittyTax
```

## Transaction Records
BittyTax is only as accurate as the data you provide it. This means it's essential that you keep records of ALL cryptoasset transactions, which includes not just trades but also records of spending, gifts sent or received, etc.

The `bittytax_conv` tool is provided to assist with this transaction record keeping, it allows data exported from various different wallets and exchanges to be processed into the format required by the `bittytax` accounting tool. Manual entry or editing of this data may also be required. It is vital that converted data files are reviewed against the raw data and audited before use.

Transaction records can be stored in an Excel or CSV file. Excel is preferred as it makes editing and managing your data easier. Data can be split across multiple worksheets, for example, you might want to split up transactions by wallet or exchange, or by transaction type. With Excel you can also annotate your records, append additional data columns, or even include the original raw data for reference.

A transaction record is represented as a row of data which contains the following fields in the order given.

| Field | Type | Description |
| --- | --- | ---|
| Type | `Deposit` | Tokens deposited to a wallet you own  
| | `Mining` | Tokens received as income from mining |
| | `Staking` | Tokens received as income from staking |
| | `Interest` | Tokens received as interest |
| | `Dividend` | Tokens received as a dividend |
| | `Income` | Tokens received as other income |
| | `Gift-Received` | Tokens received as a gift |
| | `Withdrawal` | Tokens withdrawn from a wallet you own |
| | `Spend` | Tokens spent on goods or services |
| | `Gift-Sent` | Tokens sent as a gift |
| | `Gift-Spouse` | Tokens gifted to your spouse or civil partner |
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
| Fee Value | | Value in UK pounds (GBP) of the fee |
| Wallet | | Name of wallet |
| Timestamp | | Date/time of transaction |

The transaction Type dictates which fields in the row are required, either (M)andatory or (O)ptional.   

| Type | Buy Quantity | Buy Asset | Buy Value | Sell Quantity | Sell Asset | Sell Value | Fee Quantity | Fee Asset | Fee Value | Wallet | Timestamp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---| --- |
| `Deposit` | M | M |   |||| O | O |  | O | M |
| `Mining` | M | M | O |||| O | O | O| O | M |
| `Staking` | M | M | O |||| O | O | O| O | M |
| `Interest` | M | M | O |||| O | O | O| O | M |
| `Dividend` | M | M | O |||| O | O | O| O | M |
| `Income` | M | M | O |||| O | O | O| O | M |
| `Gift-Received` | M | M | O |||| O | O | O| O | M |
| `Withdrawal` |||| M | M |   | O | O |   | O | M |
| `Spend` |||| M | M | O | O | O | O | O | M |
| `Gift-Sent` |||| M | M | O | O | O | O | O | M |
| `Gift-Spouse` |||| M | M |  | O | O | O | O | M |
| `Charity-Sent` |||| M | M | O | O | O | O | O | M |
| `Trade` | M | M | O | M | M | O | O | O | O | O | M

- If fees are specified, the Buy Quantity or Sell Quantity should be the gross amount (i.e. prior to any fee adjustment).

- The Buy Value, Sell Value and Fee Value fields are always optional, if you don't provide a fixed value, bittytax will calculate the value for you via one of its price data sources.

- Wallet name is optional, but recommended if you want to audit your cryptoasset balances across multiple wallets.  

- Timestamps should be in Excel Date & Time format (as UTC), or if text, in the format `YYYY-MM-DDTHH:MM:SS ZZZ`, where timezone (ZZZ) can be GMT, BST or UTC.

- Cryptoasset symbol names need to be consistent throughout your transaction records. For example, Bitcoin Cash was referred to as both BCC and BCH at the time of the first fork, but more recently as BCHABC or BAB. The symbol name you choose should match the symbol name used by the price data source, otherwise valuations will fail. See [Price Tool](#price-tool) for more information.

- Transaction records can be listed in any order. Bittytax will sort them by Timestamp before processing.

Example files are provided in both [Excel](https://github.com/BittyTax/BittyTax/blob/master/data/example.xlsx) and [CSV](https://github.com/BittyTax/BittyTax/blob/master/data/example.csv) format.

### Deposit
A `Deposit` is a transfer transaction record, indicating the receipt of cryptoasset tokens to a wallet you control. For example, you might have deposited tokens to a wallet on a cryptocurrency exchange.

Deposit should NOT be used to record transfers to someone else's wallet, this would be categorised as either a `Gift-Sent` or  a `Spend`. 

There should be an equivalent `Withdrawal` transaction record for every deposit, since tokens are always moving out of one wallet into another. The quantity of tokens deposited will normally be less than the quantity withdrawn due to network transaction fees. Deposits and Withdrawals are not taxable events. 

The Deposit type can also be used to record fiat deposits into an exchange. Although this is not used for tax calculations, it will be used for auditing purposes.

### Withdrawal
A `Withdrawal` is a transfer transaction record, indicating tokens being sent from a wallet you control. It is always used in combination with a `Deposit` transaction.

The Withdrawal type can also be used to record fiat withdrawals from an exchange.

### Mining
The `Mining` transaction type is used to identify tokens received as income from mining. The `Income` transaction type could also be used to record this - its use is purely descriptive.

These transaction records will appear within your income tax report.

### Staking
The `Staking` transaction type is used to identify tokens received as income from staking.

These transaction records will appear within your income tax report.

### Interest
The `Interest` transaction type is used to identify tokens received as interest.

These transaction records will appear within your income tax report.

### Dividend
The `Dividend` transaction type is used to identify tokens received as a dividend.

These transaction records will appear within your income tax report.

### Income
The `Income` transaction type is used to identify tokens received as other income, i.e. income which cannot be categorised as `Mining`, `Staking`, `Interest` or `Dividend`.

These transaction records will appear within your income tax report.

### Gift-Received
The `Gift-Received` transaction type is used to record cryptoasset tokens received as a gift.

A gift received is not taxed as income.

### Spend
A `Spend` is a disposal transaction record, which is used to capture the spending of tokens on goods or services.

As a disposal transaction, it is applicable for Capital Gains tax.

### Gift-Sent
A `Gift-Sent` is a disposal transaction record, which identifies cryptoasset tokens sent as a gift.

As a disposal transaction, it is applicable for Capital Gains tax.

### Gift-Spouse
`Gift-Spouse` is a disposal transaction record, it identifies cryptoasset tokens gifted to your spouse or civil partner.

This disposal is recorded as "No-Gain/No-Loss", it is applicable for Capital Gains tax, although there will be no gain as the proceeds are calculated to match the acquisition cost (including fees).

Your spouses' accounts should contain an equivalent `Gift-Received` transaction record, with a Buy Value that matches the proceeds of your "No-Gain/No-Loss" disposal.

### Charity-Sent
A `Charity-Sent` is a disposal transaction record, it identifies cryptoasset tokens sent to a charity as a gift. It's handling is the same as a `Gift-Sent` - it's purpose is purely descriptive.

### Trade
The `Trade` transaction type records the exchange of one cryptoasset for another, or for fiat currency.

This could be for one for the following reasons.

- Fiat-to-crypto *(acquisition)*
- Crypto-to-crypto *(disposal)*
- Crypto-to-fiat *(disposal)*

In the case of a fiat-to-crypto trade, the Sell Asset would be fiat (i.e. GBP or whatever currency you used) and Sell Quantity would contain the amount. There is no reason to specify the Sell Value if the currency is GBP.

In the opposite case, crypto-to-fiat, the Buy Asset would be fiat, and the Buy Quantity the amount in fiat.

Trades which are a *disposal* are applicable for Capital Gains tax.

### Other types?
Below is a list of some other situations which you might need to record, but which don't have a specific transaction type defined. These could be added in the future if users feel it would be of benefit.

1. **Airdrop** - If nothing was done in return for them, these tokens can be recorded as a `Gift-Received`. If the distribution of tokens was dependant upon providing a service or other conditions, these tokens can be recorded as `Income`. See [HMRC Guidance on Airdrops](https://www.gov.uk/government/publications/tax-on-cryptoassets/cryptoassets-for-individuals#airdrops).  
1. **Dust clean** - Some exchanges remove very small amounts (dust) of cryptoasset tokens from wallets after a period of time, since these are too small to be traded or withdrawn. This can be captured as a `Spend` with a Sell Value of 0.  
1. **Fork** - If a cryptoasset you own is forked and a new cryptoasset is created, this can be recorded as a `Gift-Received` but with a Buy Value of 0. This assumes that you are not splitting the cost between the original and new cryptoasset. Currently, it is not possible to derive a cost from the original cryptoasset and apportion this to the new one. See [HMRC Guidance on Blockchain forks](https://www.gov.uk/government/publications/tax-on-cryptoassets/cryptoassets-for-individuals#fork).
1. **Lost** - Tokens which have been lost (i.e. the private keys are unrecoverable) have to be reported/accepted by HMRC as a *"negligible value claim"*. These are treated as a disposal, followed by a re-acquisition for the amount lost, since technically you still own the cryptoasset. This can be recorded as a crypto-to-fiat `Trade` with a GBP cost of 0, followed by a fiat-to-crypto `Trade` for exactly the same quantity of the cryptoasset, also with a cost of 0. See [HMRC Guidance on losing public and private keys](https://www.gov.uk/government/publications/tax-on-cryptoassets/cryptoassets-for-individuals#losing-public-and-private-keys).

## Accounting Tool
Once you have all of your transaction records stored in an Excel or CSV file, you can use `bittytax` to process them and generate your report.

    bittytax <filename>

### PDF Report
By default the report is given the filename `BittyTax_Report.pdf`. You can see an example file [here](https://github.com/BittyTax/BittyTax/blob/master/data/BittyTax_Report.pdf).

If you want to use a different filename or to specify a folder, you can use the `-o` option as shown below.

    bittytax <filename> -o <output_filename>

The PDF generator can be a bit slow when handling large amounts of data. If you prefer, you can output the report to the terminal window by using the `--nopdf` option.

    bittytax <filename> --nopdf

The report is split into the following sections.

1. [Audit](#audit)
2. [Tax Report](#tax-report) (per year)
3. Appendix - [Price Data](#price-data) (per year)
4. Appendix - [Current Holdings](#current-holdings)

#### Audit
The imported transaction records are audited by calculating what the final balances should be for each asset in your wallet.

If the balances listed in the report don't match, it could be that your transaction records are incomplete.

If you do get issues, you can use the `-d` or `--debug` option to turn on logging (see [Audit Transaction Records](#audit-transaction-records)).

Although important, the audit can be disabled by using the `-s` or `--skipaudit` option.

#### Tax Report
By default, tax reports are produced for all years which contain taxable events.

If you only want a report for a specific year you can do this using the `-ty` or `--taxyear` option. 

    bittytax <filename> -ty 2020

Full details of the tax calculations can be seen by turning on the debug output (see [Processing](#processing)).

#### Capital Gains
Cryptoasset disposals are listed in date order and by asset.

For a "Bed and Breakfast" disposal, the date of the buyback is given in brackets.

If a disposal results in a loss, the negative amount is highlighted in red.

Totals are listed per asset (if more than 1 disposal) as well as the totals for that tax year.

The **Summary** section provides enough information for you to complete the "Other property, assets and gains" section within your self assessment tax return, or to give to your accountant to complete.

If the disposal proceeds exceed more than 4 times the annual tax-free allowance this is shown. HMRC requires you to report this in your self assessment even if the gain was within your annual allowance.

HMRC also requires you to include details of each gain or loss. You can use the `--summary` option in combination with `--taxyear` to generate a PDF report which only includes the capital gains disposals and summary for that specific tax year, this can then be attached to your self assessment. You can see an example summary report [here](https://github.com/BittyTax/BittyTax/blob/master/data/BittyTax_Report_Summary.pdf).

The **Tax Estimate** section is given purely as an estimate. Capital gains tax figures are calculated at both the basic and higher rate, and take into consideration the full tax-free allowance.  

Obviously you would need to take into account other capital gains/losses in the same year, and use the correct tax rate according to your income. Always consult with a professional accountant before filing.

#### Income
Income events are listed in date order and by asset, with totals per asset (if more than 1 event).

Totals are also given per Income Type (`Mining`, `Staking`, `Interest`, `Dividend` and `Income`), as well as the totals for that tax year.

You should check with an accountant for how this should be reported according to your personal situation.

#### Price Data
The appendix section contains all the historic price data which bittytax has used in the tax calculations.

This includes both fiat and crypto prices, split by tax year.

It is important to check that the symbol names of your assets have been interpreted correctly, and that the prices look reasonable, otherwise your tax calculations will be incorrect. See [Price Tool](#price-tool) for more information on how price data is retrieved.

Links are provided against each price, pointing to the exact data source API which was used to retrieve the data. 

#### Current Holdings
The appendix section also contains details of your remaining cryptoasset balances. The cost (including fees), the current valuation, and the calculated gain (or loss) are shown.

By default, empty wallets are excluded, this setting can be changed in the config file, see [Config](#config).

The data source used to get the latest price is the same as for the historic price data.

### Processing
You can turn on debug using the `-d` or `--debug` option to see full details of how the transaction records are processed.

1. [Import Transaction Records](#import-transaction-records)
2. [Audit Transaction Records](#audit-transaction-records)
3. [Split Transaction Records](#split-transaction-records)
3. [Pool Same Day](#pool-same-day)
4. [Match "same day" Rule](#match-same-day-rule)
5. [Match "bed and breakfast" Rule](#match-bed-and-breakfast-rule)
6. [Process Unmatched (Section 104)](#process-unmatched-section-104)
7. [Process Income](#process-income)

#### Import Transaction Records
First the transaction records are imported and validated according to their transaction type, making sure that the correct mandatory and optional fields are included.

In the log, the worksheet name (Excel only) and row number are shown against the raw record data being imported.

Empty rows are allowed, and filtered out during the import.

Each record is given a unique Transaction ID (TID), these are allocated in chronological order (using the timestamp) regardless of the file ordering.

```
Excel file: example.xlsx
importing 'Sheet1' rows
...
import: 'Sheet1' row[2] ['Deposit', '870.0', 'GBP', '', '', '', '', '', '', '', 'LocalBitcoins', '2013-05-24T20:16:46 UTC'] [TID:1]
import: 'Sheet1' row[3] ['Trade', '10.0', 'BTC', '', '870.0', 'GBP', '', '', '', '', 'LocalBitcoins', '2013-05-24T20:17:40 UTC'] [TID:2]
import: 'Sheet1' row[4] ['Withdrawal', '', '', '', '10.0', 'BTC', '', '', '', '', 'LocalBitcoins', '2013-05-24T20:20:49 UTC'] [TID:3]
import: 'Sheet1' row[5] ['Deposit', '10.0', 'BTC', '', '', '', '', '', '', '', 'Desktop wallet', '2013-05-24T21:20:49 BST'] [TID:4]
import: 'Sheet1' row[6] ['Deposit', '2693.8', 'USD', '', '', '', '', '', '', '', 'Bitstamp', '2014-05-29T08:33:00 UTC'] [TID:5]
import: 'Sheet1' row[7] ['Spend', '', '', '', '0.002435', 'BTC', '0.8', '', '', '', 'Desktop wallet', '2014-06-26T12:25:02 BST'] [TID:6]
import: 'Sheet1' row[8] ['Gift-Sent', '', '', '', '0.02757', 'BTC', '', '', '', '', 'Desktop wallet', '2014-07-18T14:12:47 BST'] [TID:7]
import: 'Sheet1' row[9] ['Trade', '0.41525742', 'BTC', '', '257.53', 'USD', '', '1.29', 'USD', '', 'Bitstamp', '2014-07-23T10:58:00 UTC'] [TID:8]
import: 'Sheet1' row[10] ['Trade', '0.58474258', 'BTC', '', '362.63', 'USD', '', '1.82', 'USD', '', 'Bitstamp', '2014-07-23T10:58:00 UTC'] [TID:9]

```
#### Audit Transaction Records
The audit function takes the transaction records, and then replays them in chronological order.

The simulation of tokens (and also fiat) being moved between wallets allows you to compare the calculated final balances against your real world wallets and exchange balances.

Bittytax will raise a warning if a cryptoasset balance goes negative during the audit. This could happen if the time ordering of your transaction records is not accurate.

The log shows for each transaction record (TR) which wallets are being updated.

The wallet name and asset name are shown with its balance, and in brackets the quantity that has been added or subtracted.

```console
audit transaction records
...
audit: TR Trade 0.41525742 BTC <- 257.53 USD + fee=1.29 USD 'Bitstamp' 2014-07-23T10:58:00 UTC [TID:8]
audit:   Bitstamp:BTC=0.41525742 (+0.41525742)
audit:   Bitstamp:USD=2,436.27 (-257.53)
audit:   Bitstamp:USD=2,434.98 (-1.29)
audit: TR Trade 0.58474258 BTC <- 362.63 USD + fee=1.82 USD 'Bitstamp' 2014-07-23T10:58:00 UTC [TID:9]
audit:   Bitstamp:BTC=1 (+0.58474258)
audit:   Bitstamp:USD=2,072.35 (-362.63)
audit:   Bitstamp:USD=2,070.53 (-1.82)
audit: TR Trade 0.86 BTC <- 521.16 USD + fee=2.51 USD 'Bitstamp' 2014-07-24T13:08:00 UTC [TID:10]
audit:   Bitstamp:BTC=1.86 (+0.86)
audit:   Bitstamp:USD=1,549.37 (-521.16)
audit:   Bitstamp:USD=1,546.86 (-2.51)
audit: TR Trade 0.9 BTC <- 545.7 USD + fee=2.51 USD 'Bitstamp' 2014-07-24T13:08:00 UTC [TID:11]
audit:   Bitstamp:BTC=2.76 (+0.9)
audit:   Bitstamp:USD=1,001.16 (-545.7)
audit:   Bitstamp:USD=998.65 (-2.51)
audit: TR Trade 1.64037953 BTC <- 994.07 USD + fee=4.58 USD 'Bitstamp' 2014-07-24T13:09:00 UTC [TID:12]
audit:   Bitstamp:BTC=4.40037953 (+1.64037953)
audit:   Bitstamp:USD=4.58 (-994.07)
audit:   Bitstamp:USD=0 (-4.58)
audit: TR Withdrawal 4.40037953 BTC 'Bitstamp' 2014-07-24T21:01:00 UTC [TID:13]
audit:   Bitstamp:BTC=0 (-4.40037953)
```

#### Split Transaction Records
Before any tax calculations can take place, transaction records need to be split into their constitute parts, in terms of cryptoasset buys and cryptoasset sells (each with their own valuation in GBP).

This requires the buy, sell and fee assets in the transaction record first to be given a valuation, that is unless a fixed value has already been specified, or the asset is already in GBP.

Valuations are calculated via one of the historic price date sources, see [Price Tool](#price-tool) for how.

Note that `Deposit` and `Withdrawal` transactions are not taxable events so no valuation is required.

In the log, any transaction buys (BUY) or sells (SELL) that are created by the split are shown below the transaction record (TR). These transactions have unique TIDs allocated sequentially based on the parent transaction ID, i.e. (34.1, 34.2, 34.3, etc).

If historic price data has been used for the valuation, it is indicated by the `~` symbol, fixed values are show as `=`.

GBP values are displayed with 2 decimal places, although no actual rounding has taken place. Rounding only happens when a taxable event is recorded.

Timestamps are normalised to be in local time (GMT or BST). This is so that tax calculations for the same day will be correct.

##### Fee Handling
Each buy or sell transaction can include a fee. Its value is populated by the fee specified in the transaction record.

If a transaction record involves more than one cryptoasset (i.e. a `Trade` crypto-to-crypto) then the fee's valuation has to be split evenly between the buy and sell transactions.

If the fee asset is also a cryptoasset, then paying the fee counts as a separate disposal. This is recorded by adding an additional `Spend` transaction.

Since `Deposit` and `Withdrawal` transactions are not taxable, any additional `Spend` transactions created for these are also flagged as non-taxable.

Non-taxable transactions are marked with `*` in the log and have no GBP valuation.

```console
split transaction records
...
split: TR Trade 10 BTC <- 870 GBP 'LocalBitcoins' 2013-05-24T20:17:40 UTC [TID:2]
split:   BUY Trade 10 BTC (=£870.00 GBP) 'LocalBitcoins' 2013-05-24T21:17:40 BST [TID:2.1]
...
split: TR Withdrawal 7.0002 BTC 'Desktop wallet' 2017-03-24T22:57:44 GMT [TID:32]
split:   SELL* Withdrawal 7.0002 BTC 'Desktop wallet' 2017-03-24T22:57:44 GMT [TID:32.1]
split: TR Deposit 7 BTC 'Poloniex' 2017-03-24T22:57:44 UTC [TID:33]
split:   BUY* Deposit 7 BTC 'Poloniex' 2017-03-24T22:57:44 GMT [TID:33.1]
split: TR Trade 1.00000013 ETH <- 0.03729998 BTC + fee=0.0015 ETH 'Poloniex' 2017-04-12T19:38:26 UTC [TID:34]
price: 2017-04-12, 1 BTC=969.6202 GBP via CoinDesk (Bitcoin)
price: 2017-04-12, 1 BTC=£969.62 GBP, 0.03729998 BTC=£36.17 GBP
split:   BUY Trade 1.00000013 ETH (~£36.17 GBP) + fee=~£0.03 GBP 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.1]
split:   SELL Trade 0.03729998 BTC (~£36.17 GBP) + fee=~£0.03 GBP 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.2]
split:   SELL Spend 0.0015 ETH (~£0.05 GBP) 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.3]

```

### Pool Same Day
HMRC stipulates that ["*All shares of the same class in the same company acquired by the same person on the same day and in the same capacity are treated as though they were acquired by a single transaction*"](https://www.gov.uk/hmrc-internal-manuals/capital-gains-manual/cg51560#IDATX33F). This applies in the same way to disposals.

Tokens of the same cryptoasset acquired on the same day are pooled together into a single buy transaction. The same applies for tokens disposed of on the same day - they are pooled into a single sell transaction.

Only taxable transactions (i.e. acquisitions and disposals) are included within these pools.

Pooled transactions are indicated by a transaction count at the end, shown within square brackets. The transactions contained within the pool are then indented below it, and shown with brackets.

```console
pool same day transactions
pool: BUY Trade 10 BTC (=£870.00 GBP) 'LocalBitcoins' 2013-05-24T21:17:40 BST [TID:2.1]
pool: SELL* Withdrawal 10 BTC 'LocalBitcoins' 2013-05-24T21:20:49 BST [TID:3.1]
pool: BUY* Deposit 10 BTC 'Desktop wallet' 2013-05-24T21:20:49 BST [TID:4.1]
pool: SELL Spend 0.002435 BTC (=£0.80 GBP) 'Desktop wallet' 2014-06-26T12:25:02 BST [TID:6.1]
pool: SELL Gift-Sent 0.02757 BTC (~£10.14 GBP) 'Desktop wallet' 2014-07-18T14:12:47 BST [TID:7.1]
pool: BUY Trade 1 BTC (~£364.22 GBP) + fee=~£1.83 GBP 'Bitstamp' 2014-07-23T11:58:00 BST [TID:8.1] [2]
pool:   (BUY Trade 0.41525742 BTC (~£151.25 GBP) + fee=~£0.76 GBP 'Bitstamp' 2014-07-23T11:58:00 BST [TID:8.1])
pool:   (BUY Trade 0.58474258 BTC (~£212.97 GBP) + fee=~£1.07 GBP 'Bitstamp' 2014-07-23T11:58:00 BST [TID:9.1])
```

### Match "same day" Rule
See ["*The “same day” rule TCGA92/S105(1)*"](https://www.gov.uk/hmrc-internal-manuals/capital-gains-manual/cg51560#IDATX33F).

This tax function matches any buy and sell transactions, of the same cryptoasset, that occur on the same day. 

If the buy and sell quantities do not match, the transaction with the larger quantity will be split into two, and the cost and fee apportioned between them.

This allows a gain or a loss to be calculated for the matching transactions, taking into consideration the combined fees. The transaction containing the remainder is then carried forward, and used in further tax calculations.

In the log, you can see which transactions have been "*same day*" matched, if a buy or sell has been split, and the resulting disposal event.

New transactions created by a split are allocated the next TID in sequence.

```console
match same day transactions
...
match: SELL Spend 0.62207655 ETH (~£22.50 GBP) 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.3] [4]
match: BUY Trade 249.23062521 ETH (~£9,012.71 GBP) + fee=~£11.25 GBP 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.1] [4]
match:   split: BUY Trade 0.62207655 ETH (~£22.50 GBP) + fee=~£0.03 GBP 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.4] [4]
match:   split: BUY Trade 248.60854866 ETH (~£8,990.22 GBP) + fee=~£11.22 GBP 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.5] [4]
match:   Disposal(same day) gain=£-0.03 (proceeds=£22.50 - cost=£22.50 - fees=£0.03)
```

### Match "bed and breakfast" Rule

See ["*The “bed and breakfast” rule TCGA92/S106A(5) and (5A)*"](https://www.gov.uk/hmrc-internal-manuals/capital-gains-manual/cg51560#IDATR33F).
 
This tax functions matches sells to buybacks of the same cryptoasset which occur within 30 days.

As with the ["same day"](#match-same-day-rule) rule, if the buy and sell quantities do not match, a transaction will be split.

Transactions are sorted by timestamp, and matched in chronological order.

Any matched "same day" transactions are excluded from this rule.

In the log, you can see which transactions have been matched by the "*bed & breakfast*" rule, and the resulting disposal event.

```console
match bed & breakfast transactions
...
match: SELL Trade 5.32294271 BTC (~£1,474.69 GBP) + fee=~£1.47 GBP 'Poloniex' 2016-01-27T22:09:19 GMT [TID:18.2] [5]
match: BUY Trade 5.54195456 BTC (~£1,471.32 GBP) + fee=~£1.47 GBP 'Poloniex' 2016-01-29T13:51:01 GMT [TID:23.5] [9]
match:   split: BUY Trade 5.32294271 BTC (~£1,413.17 GBP) + fee=~£1.41 GBP 'Poloniex' 2016-01-29T13:51:01 GMT [TID:23.6] [9]
match:   split: BUY Trade 0.21901185 BTC (~£58.14 GBP) + fee=~£0.06 GBP 'Poloniex' 2016-01-29T13:51:01 GMT [TID:23.7] [9]
match:   Disposal(bed & breakfast) gain=£58.63 (proceeds=£1,474.69 - cost=£1,413.17 - fees=£2.89)
```

### Process Unmatched (Section 104)
Any transactions which remain unmatched are processed according to Section 104 Taxation of Capital Gains Act 1992.

Each cryptoasset is held in its own pool, known as a Section 104 holding. The unmatched transactions are processed in chronological order.

As tokens are acquired, the total cost and total fees for that cryptoasset holding increases.

If all tokens in a holding are disposed of, the cost will be the total cost of that cryptoasset holding, and likewise, the fees would be the total fees.

If only some tokens are disposed of, the cost is calculated as a fraction of the total cost. This fraction is calculated by the number of tokens disposed of divided by the total number of tokens held. The fees are also calculated as a fraction in the same way.

The gain or loss is then calculated by subtracting this cost and any fees from the proceeds of the disposal. Fees are included from both the Section 104 holding (acquisition fees) and also the disposal fee.

For non-taxable transactions such as `Withdrawal` and `Deposit`, the tokens are removed and then re-added to the holding (but at zero cost).

**NOTE:** It is important that no disposal event happens to a holding between a `Withdrawal` and a `Deposit`. This is because the tokens are removed temporarily, so it would impact the cost calculation.

In the log, before the Section 104 calculations, the updated transactions are listed for clarity. This includes any new "split" transactions which have been added by the matching function.

Transactions which have been matched, and so excluded from the Section 104 holding, are denoted with // at the start.
```console
updated transactions
updated: BUY Trade 10 BTC (=£870.00 GBP) 'LocalBitcoins' 2013-05-24T21:17:40 BST [TID:2.1]
updated: SELL* Withdrawal 10 BTC 'LocalBitcoins' 2013-05-24T21:20:49 BST [TID:3.1]
updated: BUY* Deposit 10 BTC 'Desktop wallet' 2013-05-24T21:20:49 BST [TID:4.1]
updated: //SELL Spend 0.002435 BTC (=£0.80 GBP) 'Desktop wallet' 2014-06-26T12:25:02 BST [TID:6.1]
updated: //SELL Gift-Sent 0.02757 BTC (~£10.14 GBP) 'Desktop wallet' 2014-07-18T14:12:47 BST [TID:7.1]
updated: //BUY Trade 0.002435 BTC (~£0.89 GBP) + fee=~£0.00 GBP 'Bitstamp' 2014-07-23T11:58:00 BST [TID:8.2] [2]
updated: //BUY Trade 0.02757 BTC (~£10.04 GBP) + fee=~£0.05 GBP 'Bitstamp' 2014-07-23T11:58:00 BST [TID:8.4] [2]
updated: BUY Trade 0.969995 BTC (~£353.29 GBP) + fee=~£1.77 GBP 'Bitstamp' 2014-07-23T11:58:00 BST [TID:8.5] [2]
```

As the unmatched transactions are processed, the impact it has on the individual holding is shown in the log.

When a disposal takes place, the gain calculation is then shown below. 

```console
process unmatched transactions
...
section104: BUY Trade 843.00981977 ETH (~£1,471.74 GBP) + fee=~£1.47 GBP 'Poloniex' 2016-01-27T22:04:21 GMT [TID:18.5] [5]
section104:   ETH=843.00981977 (+843.00981977) cost=£1,471.74 GBP (+£1,471.74 GBP) fees=£1.47 GBP (+£1.47 GBP}
section104: SELL Trade 843.00981977 ETH (~£1,474.27 GBP) + fee=~£1.47 GBP 'Poloniex' 2016-01-29T14:12:31 GMT [TID:23.2] [9]
section104:   ETH=0 (-843.00981977) cost=£0.00 GBP (-£1,471.74 GBP) fees=£0.00 GBP (-£1.47 GBP}
section104:   Disposal(section 104) gain=£-0.42 (proceeds=£1,474.27 - cost=£1,471.74 - fees=£2.95)
```

### Process Income
This function searches through all the original transactions, and records any that are applicable for income tax. Currently this is `Mining`, `Staking`, `Interest`, `Dividend` and `Income` transaction types.

## Conversion Tool
The bittytax conversion tool `bittytax_conv` takes all of the data files exported from your wallets and exchanges, normalises them into the transaction record format required by bittytax, and consolidates them into a single Excel spreadsheet for you to review, make edits, and add any missing records.

Don't worry if you don't have Microsoft Excel installed. These spreadsheets will work with [OpenOffice](https://www.openoffice.org) or [LibreOffice](https://www.libreoffice.org). You can also use [Google Sheets](https://www.google.co.uk/sheets/about/) or [Numbers for Mac](https://www.apple.com/uk/numbers/), although some conditional formatting is not supported.

Each converted file appears within its own worksheet. Data files of the same format are aggregated together. The transaction records and the original raw data appear side by side, sorted by timestamp, making it easier for you to review and to provide traceability.

The converter takes care of all the cell formatting to ensure that all decimal places are displayed correctly, and if numbers exceed 15-digits of precision (an Excel limitation) they are stored as text to prevent any truncation.

For most wallet files, transactions can only be categorised as deposits or withdrawals. You will need to edit these to reflect your real transactions (i.e. spends, gifts, income, etc.). This is easy with Excel, as the valid options are selectable via a dropdown menu.

**Wallets:**
- Electrum
- HandCash
- Helium
- Ledger Live
- Nexo
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
- Crypto.com
- Cryptopia
- Cryptsy
- Gatehub
- Gravity (Bitstocks)
- HitBTC
- Hotbit
- Kraken
- KuCoin
- Liquid
- OKEx
- Poloniex
- TradeSatoshi
- Uphold
- Wirex

**Explorers:**
- Energy Web
- Etherscan

**Accounting:**
- CoinTracking

### Usage
The help option displays a full list of recognised data file formats, as well as details of all command line arguments.

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

If there is any overlap in the reporting period this can result in duplicate entries which will cause your data not to balance out. One solution to this is to manually remove these duplicates, another is for the conversion tool to do it for you by specifying the `--duplicates` argument.

This option should be used with care, since some exchange files can appear to have exact duplicates but can be due to partially filled orders within the exact same time period, with same order id and even the same amount!

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

This will instantly show you what the remaining balance of each asset should be for that wallet or exchange file.

**Recap**

You can also use the conversion tool to convert your wallet or exchange files into the import CSV format used by Recap (see https://help.recap.io/en/articles/2631702-importing-csvs-into-custom-accounts).

    bittytax_conv --format RECAP <filename>

### Notes:
1. Some exchanges only allow the export of trades. This means transaction records of deposits and withdrawals will have to be created manually, otherwise the assets will not balance.
1. Bitfinex - when exporting your data, make sure the "*Date Format*" is set to "*DD-MM-YY*" which is the default.
1. ChangeTip - the conversion tool requires your username(s) to be configured. This is to identify which transactions are a gift received or a gift sent. See [Config](#config).
1. Coinbase - the latest "*Transaction history (all-time)*" report format from Coinbase is not as complete and detailed as previous reports. Below is a list of issues I'm aware of, there may be others.
    * Early referral rewards appear as BTC buys. These are filtered from real buys by checking if the fee is zero.
    * EUR buys/sells are listed as GBP. The actual currency is identified from the description in the "*Notes*" field.
    * Fiat deposits/withdrawals are not shown in the report so will not balance.
    * Crypto deposits/withdrawals which are relayed to/from Coinbase Pro are missing so will not balance.

    If you are also using Coinbase Pro, and your account does not balance, see below.
1. Coinbase Pro - generate the "*Account Statement*" report and export. This report on its own should balance correctly.

    If you are also using Coinbase, the only way to get these accounts to both balance (with the current reporting) is to treat them as one entity.

    In your transaction records file, change the wallet name from 'Coinbase Pro' to 'Coinbase'. Then remove any deposit or withdrawal transaction records which are for crypto, since these also appear in the Coinbase transaction records as they are relayed. It's important to keep any fiat ones, as these are missing in the Coinbase report. This should make the accounts balance correctly, apart from maybe some deposit fees which you would have to account for from your own records.

    This converter can be very slow with large amounts of data.
1. CoinTracking - export the "*Trade Prices*" report, but first change the date and time format to include seconds. This can be found under "*Account Settings*" -> "*Display Settings*". Select the special format "*d.m.Y H:i:s*".
1. Etherscan - for ERC-20 (Tokens) and ERC-721 (NFTs) exports, it is important that the filename contains your ethereum address (Etherscan does this by default), as it is used to determine if transactions are being sent or received.
1. GateHub - some exports contain incomplete data (i.e. no counter asset in an "*exchange*"), which are possibly failed transactions. The tool will filter them and raise a warning for you to review, the data still appears to balance correctly. Any XRP network fees which cannot be attributed to a "*payment*" or an "*exchange*" will be included separately as a spend transaction record.
1. Hotbit - the exported file (.xls) is actually a html file, you will need to open this file in Excel and then "*Save As*" the Excel workbook format (.xlsx) before you can convert it.
1. Kraken - export both the "*Trades*" and  "*Ledgers*" history.
1. Qt Wallet - by default, unconfirmed transactions are filtered by the conversion tool. If you want to include them, use the `-uc` or `--unconfirmed` command argument.

## Price Tool
The bittytax price tool `bittytax_price` allows you to get the latest and historic prices of cryptoassets and foreign currencies. Its use is not strictly required as part of the process of completing your accounts, but provides a useful insight into the prices which bittytax will assign when it comes to value your cryptoassets in UK pounds.

**Data Sources:**
The following price data sources are used.

- [Exchange Rates API](https://exchangeratesapi.io) - foreign currency exchange rates *(primary fiat)*
- [Rates API](https://ratesapi.io) - foreign currency exchange rates *(secondary fiat)*
- [CoinDesk BPI](https://www.coindesk.com/api) - bitcoin price index *(primary bitcoin)*
- [Crypto Compare](https://min-api.cryptocompare.com) - cryptoasset prices *(primary crypto, secondary bitcoin)*
- [Coin Gecko](https://www.coingecko.com/en/api) - cryptoasset prices *(secondary crypto)*
- [Coin Paprika](https://coinpaprika.com/api/) - cryptoasset prices

The priority (primary, secondary, etc) to which data source is used and for which asset is controlled by the `bittytax.conf` config file, (see [Config](#config)). If your cryptoasset cannot be identified by the primary data source, the secondary source will be used, and so on. 

All historic price data is cached within the .bittytax/cache folder in your home directory. This is to prevent repeated lookups and reduce load on the APIs which could fail due to throttling.

### Usage

To get the latest price of an asset, use the `latest` command, followed by the asset symbol name. This can be a cryptoasset (i.e. BTC) or a foreign currency (i.e. USD). An optional quantity can also be specified.

    bittytax_price latest asset [quantity]

If the lookup is successful not only will the price be displayed in the terminal window, but also the data source used and the full name of the asset. This is useful in making sure the asset symbol you are using in your transaction records is the correct one.

```console
$ bittytax_price latest ETH 0.5
1 ETH=0.03064 BTC via CryptoCompare (Ethereum)
1 BTC=10,147.0942 GBP via CoinDesk (Bitcoin)
1 ETH=£310.91 GBP
0.5 ETH=£155.45 GBP
```

If you wish to perform a historic data lookup, use the `historic` command instead, followed by the asset symbol name and the date.  The date can be in either `YYYY-MM-DD` or `DD/MM/YYYY` formats.

    bittytax_price historic asset date [quantity]

By specifying a quantity to price, you can use the tool to calculate the historic price of a specific transaction. This can be used as a memory jogger if you are looking at old wallet transactions and trying to remember what it was you spent your crypto on!

```console
$ bittytax_price historic BTC 2014-06-24 0.002435
1 BTC=338.5947 GBP via CoinDesk (Bitcoin)
1 BTC=£338.59 GBP
0.002435 BTC=£0.82 GBP
```

Since there is no standardisation of cryptoasset symbols, it's possible that the same symbol has different meanings across different data sources. For example, EDG is Edgeless on CryptoCompare but Edgeware on CoinGecko.

A quick way to check this is to use the `list` command, followed by an asset symbol name.

    bittytax_price list [asset]

This command will return any matches it finds for that asset symbol name across all the data sources.

```console
$ bittytax_price list EDG
EDG (Edgeware) via CoinGecko
EDG (Edgeless) via CoinPaprika
EDG (Edgeless) via CryptoCompare
```

You can also get a complete list of all supported assets (in alphabetical order) by not specifying any asset.

If bittytax is not picking up the correct asset price for you, you can change the config so that the asset symbol only uses the data source you require. See [Config](#config).

The `latest` and `historic` price commands also give you the `-ds` option to override the config and specify the data source directly. It's a quick way to check asset prices are correct before updating your config.

```console
$ bittytax_price historic EDG 2020-07-04 -ds CoinGecko
1 EDG=0.000000637935405438 BTC via CoinGecko (Edgeware)
1 BTC=7,266.832558992103 GBP via CoinGecko (Bitcoin)
1 EDG=£0.00 GBP
```

You can also set the data source to `ALL`, this will return price data for all data sources which have a match. If the [Price Data](#price-data) appendix in your tax report has any missing data, you can use this method to find prices. Some data sources have price history going back further than others.

```console
$ bittytax_price historic EDG 2020-07-04 -ds ALL
1 EDG=0.000000637935405438 BTC via CoinGecko (Edgeware)
1 BTC=7,266.832558992103 GBP via CoinGecko (Bitcoin)
1 EDG=£0.00 GBP
1 EDG=0.00000089 BTC via CoinPaprika (Edgeless)
1 BTC=7,339.45 GBP via CryptoCompare (Bitcoin)
1 EDG=£0.01 GBP
1 EDG=0.000001 BTC via CryptoCompare (Edgeless)
1 BTC=7,339.45 GBP via CryptoCompare (Bitcoin)
1 EDG=£0.01 GBP
```

To get a full details of all the arguments you can use the help option, either on its own or for a specific command.

    bittytax_price [command] --help

### Notes:
1. Not all data source APIs return prices in UK pounds (GBP), for this reason cryptoasset prices are requested in BTC and then converted from BTC into UK pounds (GBP) as a two step process.
1. Some APIs return multiple prices for the same day. If this is the case then the 'close' price is always used.
1. Historical price data is cached for each data source as a separate JSON file in the .bittytax/cache folder within your home directory.
1. CoinPaprika does not support BTC/GBP historic prices.

## Config
The `bittytax.conf` file resides in the .bittytax folder within your home directory.

The [default](https://github.com/BittyTax/BittyTax/blob/master/config/bittytax.conf) file created at runtime should cater for most users.

If you need to change anything, the parameters are described below. The file is in YAML format.

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
Used to differentiate between fiat and cryptoassets symbols. Make sure you configure all fiat currencies which appear within your transaction records here.

### crypto_list
Identifies which cryptoasset takes priority when calculating the value of a crypto-to-crypto trade (see [trade_asset_type](#trade_asset_type)). The priority is taken in sequence, so in an ETH/BTC trade, the value of the BTC would be used in preference to ETH when pricing the trade.

The list should contain the most prevalent cryptoassets which appear in exchange trading pairs. These are predominantly the higher market cap. tokens.

### trade_asset_type
Controls the method used to calculate the asset value of a trade:

- `0` = Buy asset value  
- `1` = Sell asset value  
- `2` = Priority asset value *(recommended)*  

For every trade there are always two assets involved: fiat-to-crypto, crypto-to-fiat or crypto-to-crypto. When bittytax is trying to calculate the value of a trade, it uses this parameter to determine which asset value should be used to price the trade in UK pounds.

For trades involving fiat, it's obvious that we want to price the asset using the fiat value. However, it's not so straight forward for crypto-to-crypto trades.

The recommended setting is `2` (Priority). This means that the asset value chosen will be selected according to the priority order defined by the `fiat_list` and `crypto_list` parameters combined. Fiat will always be chosen first, followed by the most prevalent cryptoasset.

Setting this parameter to `1` or `2` will result in either the buy asset value or the sell asset value always being used, regardless of whether the trades involved fiat or not. 

### show_empty_wallets
Include empty wallets in the current holdings report. Can be set to `True` or `False`.

### transfers_include
Include transfer transaction types (i.e. Deposit, Withdrawal) in tax calculations. Can be set to `True` (recommended) or `False`.

Although these transactions types are non-taxable, they do affect the cost basis of your cryptoasset holdings.

### data_source_select
Maps a specific asset symbol to a list of data sources in priority order.

This parameter overrides the any data sources defined by `data_source_fiat` and `data_source_crypto` (see below).

By default, only an entry for BTC exists. This selects CoinDesk as the primary data source for bitcoin prices and CryptoCompare as the secondary. 

If, for example you wanted EDG to use only the CoinGecko data source, you would change the config as follows.

```yaml
data_source_select: {
    'BTC': ['CoinDesk', 'CryptoCompare'],
    'EDG': ['CoinGecko'],
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

It's required for ChangeTip data files. The list of username(s) is used to identify which transactions are gifts received and gifts sent.

An example is shown below.
```yaml
usernames:
    ['Bitty_Bot', 'BittyBot']
```

## Future
These are some ideas for the project roadmap. 

Let me know what you would find most useful or any new features not mentioned you would like to see added.

### General
- Document code
- Add tests

### Conversion Tool
- Convert data from clipboard. Some wallets/exchanges don't provide an export function. It should be possible to copy the transaction data directly from the webpage and have the conversion tool analyse this data and then convert it into the transaction record format.
- Add exchange APIs to automatically convert new trades into the transaction record format.

### Accounting Tool
- BittyTax integration with Excel. The command line interface is not for everyone. By integrating with Excel (or OpenOffice), this would greatly improve the user experience.
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

## Donations ##
If you would like to support this project, you can donate via [PayPal]. All donations are gratefully received.

Disclosure: All donations go to Nano Nano Ltd, the creator and maintainer of this project. Nano Nano Ltd is not a charity, or non-profit organisation.

[version-badge]: https://img.shields.io/pypi/v/BittyTax.svg
[license-badge]: https://img.shields.io/pypi/l/BittyTax.svg
[python-badge]: https://img.shields.io/pypi/pyversions/BittyTax.svg
[downloads-badge]: https://img.shields.io/pypi/dm/bittytax
[github-stars-badge]: https://img.shields.io/github/stars/BittyTax/BittyTax?color=yellow
[twitter-badge]: https://img.shields.io/twitter/follow/bitty_tax?color=%231DA1F2&style=flat
[discord-badge]: https://img.shields.io/discord/581493570112847872.svg
[donation-badge]: https://img.shields.io/badge/donate-PayPal-179bd7.svg
[version]: https://pypi.org/project/BittyTax/
[license]: https://github.com/BittyTax/BittyTax/blob/master/LICENSE
[python]: https://wiki.python.org/moin/BeginnersGuide/Download
[downloads]: https://pypistats.org/packages/bittytax
[github-stars]: https://github.com/BittyTax/BittyTax/stargazers
[twitter]: https://twitter.com/intent/follow?screen_name=bitty_tax
[discord]: https://discord.gg/NHE3QFt
[PayPal]: https://www.paypal.com/donate?hosted_button_id=HVBQW8TBEHXLC
