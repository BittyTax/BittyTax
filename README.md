![BittyTax logo](https://github.com/BittyTax/BittyTax/raw/master/img/BittyTax.svg)
[![Version badge][version-badge]][version]
[![License badge][license-badge]][license]
[![Python badge][python-badge]][python]
[![Downloads badge][downloads-badge]][downloads]
[![Stars badge][github-stars-badge]][github-stars]
[![Sponsor badge][sponsor-badge]][sponsor]
[![X badge][x-badge]][x]
[![Discord badge][discord-badge]][discord]
[![PayPal badge][paypal-badge]][PayPal]
[![Bitcoin badge][bitcoin-badge]][bitcoin]
# BittyTax

## Overview
BittyTax is a collection of command-line tools to help you calculate your cryptoasset taxes in the UK.

This tool is designed to be used by someone who is already familiar with cryptoasset taxation rules in the UK. HMRC has published guidance on this. We've collected some useful links in the [Resources](#resources) section at the end.

BittyTax comprises of the following tools.

1. `bittytax` - process your transaction records and generate a PDF tax report (see [Accounting Tool](#accounting-tool)) 

2. `bittytax_conv` - convert your wallet and exchange files into transaction records (see [Conversion Tool](#conversion-tool))

3. `bittytax_price` - (optional) lookup historic price data for cryptoassets and foreign currencies (see [Price Tool](#price-tool))

Although UK focused, many of the tools can be used for other countries and currencies, see [International support](https://github.com/BittyTax/BittyTax/wiki/International-Support).

There is also a US version of BittyTax which has its own branch, see [USA](https://github.com/BittyTax/BittyTax/wiki/USA).

## Why use BittyTax?
* Open-source: growing community of users
* Free to use: no subscriptions, no transaction limits
* Protects your privacy: no need to share your data with a 3rd party
* Fully transparent: all calculations and data sources are provided
* Accuracy: built in integrity check, passes all the [HMRC example test cases](https://github.com/BittyTax/BittyTax/wiki/HMRC-Example-Test-Cases)
* Auditability: compliant with HMRC auditing requirements

## License/Disclaimer
This software is copyright (c) Nano Nano Ltd, and licensed for use under the AGPLv3 License, see [LICENSE](https://github.com/BittyTax/BittyTax/blob/master/LICENSE) file for details. The [BittyTaxAPI](https://github.com/BittyTax/BittyTax/wiki/BittyTaxAPI) server is licensed for personal use only. If you would like a license to use this software commercially, please [get in touch](mailto:hello@bitty.tax).

Nano Nano Ltd does not provide tax, legal, accounting or financial advice. This software and its content are provided for information only, and as such should not be relied upon for tax, legal, accounting or financial advice.

You should obtain specific professional advice from a [professional accountant](https://github.com/BittyTax/BittyTax/wiki/Crypto-Tax-Accountants-in-the-UK), tax or legal/financial advisor before you take any action.

This software is provided 'as is', Nano Nano Ltd does not give any warranties of any kind, express or implied, as to the suitability or usability of this software, or any of its content.

## Getting Started
You will need Python installed on your machine before you can install BittyTax, see the [installation](https://github.com/BittyTax/BittyTax/wiki/Installation) guide which covers Windows, macOS and Linux for full details.

If you are upgrading from a previous version of BittyTax, please follow the [upgrade](https://github.com/BittyTax/BittyTax/wiki/Upgrade) instructions.

## Transaction Records
BittyTax is only as accurate as the data you provide it. This means it's essential that you keep records of ALL cryptoasset transactions, which includes not just trades but also records of spending, income, gifts sent or received, etc.

The `bittytax_conv` tool is provided to assist with this transaction record keeping, it allows data exported from various different wallets and exchanges to be processed into the format required by the `bittytax` accounting tool. Manual entry or editing of this data may also be required. It is vital that converted data files are reviewed against the raw data and audited before use.

Transaction records can be stored in an Excel or CSV file. Excel is preferred as it makes editing and managing your data easier. Data can be split across multiple worksheets, for example, you might want to split up transactions by wallet or exchange, or by transaction type. With Excel you can also annotate your records, append additional data columns, or even include the original raw data for reference.

A transaction record is represented as a row of data which contains the following fields in the order given.

| Field | Type | Description |
| --- | --- | ---|
| Type | `Deposit` | Tokens deposited to a wallet you own |
| | `Unstake` | Tokens returned to a wallet after being staked |
| | `Mining` | Tokens received as income from mining |
| | `Staking-Reward` `Staking`\* | Tokens received as a reward from staking |
| | `Interest` | Tokens received as interest |
| | `Dividend` | Tokens received as a dividend |
| | `Income` | Tokens received as other income |
| | `Gift-Received` | Tokens received as a gift |
| | `Fork` | Tokens received as the result of a blockchain fork |
| | `Airdrop` | Tokens received from an airdrop |
| | `Referral` | Tokens received as a reward through a referral program |
| | `Cashback` | Tokens received as cashback |
| | `Fee-Rebate` | Tokens received as a rebate of fees |
| | `Loan` | Tokens received as a loan |
| | `Margin-Gain` | Tokens received as a result of a margin gain |
| | `Margin-Fee-Rebate` | Tokens received as a rebate of margin fees |
| | `Withdrawal` | Tokens withdrawn from a wallet you own |
| | `Stake` | Tokens withdrawn from a wallet to be staked |
| | `Spend` | Tokens spent on goods or services |
| | `Gift-Sent` | Tokens sent as a gift |
| | `Gift-Spouse` | Tokens gifted to your spouse or civil partner |
| | `Charity-Sent` | Tokens sent to a charity as a gift |
| | `Lost` | Tokens that have been lost or stolen |
| | `Loan-Repayment` | Tokens returned to the lender of a loan |
| | `Loan-Interest` | Tokens paid as a fee to the lender of a loan |
| | `Margin-Loss` | Tokens deducted as a result of a margin loss |
| | `Margin-Fee` | Tokens paid as fees for a margin position |
| | `Trade` | Tokens exchanged for another token or fiat currency |
| Buy Quantity | | Quantity of the asset acquired |
| Buy Asset | | Symbol name of the asset acquired |
| Buy Value in GBP | | Value in UK pounds of the asset acquired |
| Sell Quantity | |  Quantity of the asset disposed |
| Sell Asset | | Symbol name of the asset disposed |
| Sell Value in GBP | | Value in UK pounds of the asset disposed |
| Fee Quantity | | Quantity of the fee |
| Fee Asset | | Symbol name of the asset used for fees |
| Fee Value in GBP | | Value in UK pounds of the fee |
| Wallet | | Name of wallet |
| Timestamp | | Date/time of transaction |
| Note | | Description of transaction |

\* - `Staking` has been deprecated, please use `Staking-Reward`.

The transaction Type dictates which fields in the row are required, either (M)andatory or (O)ptional.   

| Type | Buy Quantity | Buy Asset | Buy Value in GBP | Sell Quantity | Sell Asset | Sell Value in GBP | Fee Quantity | Fee Asset | Fee Value in GBP | Wallet | Timestamp | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---| --- | --- |
| `Deposit` | M | M |   |||| O | O | O | O | M | O |
| `Unstake` | M | M |   |||| O | O | O | O | M | O |
| `Mining` | M | M | O |||| O | O | O| O | M | O |
| `Staking-Reward` | M | M | O |||| O | O | O| O | M | O |
| `Interest` | M | M | O |||| O | O | O| O | M | O |
| `Dividend` | M | M | O |||| O | O | O| O | M | O |
| `Income` | M | M | O |||| O | O | O| O | M | O |
| `Gift-Received` | M | M | O |||| O | O | O| O | M | O |
| `Fork` | M | M | O |||| O | O | O | O | M | O |
| `Airdrop` | M | M | O |||| O | O | O| O | M | O |
| `Referral` | M | M | O |||| O | O | O | O | M | O |
| `Cashback` | M | M | O |||| O | O | O | O | M | O |
| `Fee-Rebate` | M | M | O |||| O | O | O | O | M | O |
| `Loan` | M | M | O |||| O | O | O | O | M | O |
| `Margin-Gain` | M | M | O |||| O | O | O | O | M | O |
| `Margin-Free-Rebate` | M | M | O |||| O | O | O | O | M | O |
| `Withdrawal` |||| M | M |   | O | O | O | O | M | O |
| `Stake` |||| M | M |   | O | O | O | O | M | O |
| `Spend` |||| M | M | O | O | O | O | O | M | O |
| `Gift-Sent` |||| M | M | O | O | O | O | O | M | O |
| `Gift-Spouse` |||| M | M |  | O | O | O | O | M | O |
| `Charity-Sent` |||| M | M | O | O | O | O | O | M | O |
| `Lost` |||| M | M | O | O | O | O | O | M | O |
| `Loan-Repayment` |||| M | M | O | O | O | O | O | M | O |
| `Loan-Interest` |||| M | M | O | O | O | O | O | M | O |
| `Margin-Loss` |||| M | M | O | O | O | O | O | M | O |
| `Margin-Fee` |||| M | M | O | O | O | O | O | M | O |
| `Trade` | M | M | O | M | M | O | O | O | O | O | M | O |

- If the Fee Asset is the same as Sell Asset, then the Sell Quantity must be the net amount (after fee deduction), not gross amount.

- If the Fee Asset is the same as Buy Asset, then the Buy Quantity must be the gross amount (before fee deduction), not net amount.

- The Buy Value in GBP, Sell Value in GBP and Fee Value in GBP fields are always optional, if you don't provide a fixed value, bittytax will calculate the value for you via one of its price data sources.

- Wallet name is optional, but recommended if you want to audit your cryptoasset balances across multiple wallets.  

- Timestamps should be in Excel Date & Time format (as UTC), or if text, in the format `YYYY-MM-DDTHH:MM:SS.000000 ZZZ` where ZZZ represents the timezone, or if omitted UTC is assumed. Milliseconds or microseconds are optional.

- Cryptoasset symbol names need to be consistent throughout your transaction records. The symbol name you choose should match the symbol name used by the price data source, otherwise valuations will fail. See [Price Tool](#price-tool) for more information.  NFT assets should be identified with a unique symbol name in the format "\<Name\> #\<Id\>", i.e. `CryptoPunk #369`.

- Transaction records can be listed in any order. Bittytax will sort them by Timestamp before processing.

Example files are provided in both [Excel](https://github.com/BittyTax/BittyTax/blob/master/data/example.xlsx) and [CSV](https://github.com/BittyTax/BittyTax/blob/master/data/example.csv) format.

### Deposit
A `Deposit` is a transfer transaction record, indicating the receipt of cryptoasset tokens to a wallet you control. For example, you might have deposited tokens to a wallet on a cryptocurrency exchange.

Deposit should NOT be used to record transfers to someone else's wallet, this would be categorised as either a `Gift-Sent` or a `Spend`.

There should always be an equivalent `Withdrawal` transaction record for every deposit, since tokens are always moving out of one wallet into another.

It is important that any deposit fee paid is specified, the deposit quantity should be the gross amount (before fee deduction).

Deposits and Withdrawals are not taxable events, but paying the transfer fee is (unless otherwise configured), see [transfer_fee_disposal](#transfer_fee_disposal).

The Deposit type can also be used to record fiat deposits into an exchange. Although this is not used for tax calculations, it will be used for auditing purposes.

### Withdrawal
A `Withdrawal` is a transfer transaction record, indicating tokens being sent from a wallet you control. It is always used in combination with a `Deposit` transaction.

It is important that any withdrawal fee paid is specified, the withdrawal quantity should be the net amount (after fee deduction).

Its corresponding Deposit quantity should match the Withdrawal quantity, this is important, as the transfers will be removed from the tax calculations.

The Withdrawal type can also be used to record fiat withdrawals from an exchange.

### Stake
The `Stake` transaction type records tokens withdraw from a wallet to be staked for rewards.

As you are still the beneficial owner, they are included in your total holdings.

This is not a taxable event.

### Unstake

The `Unstake` transaction type records tokens returned to a wallet after being staked.

There should NOT be more tokens returned than were originally staked. Any additional tokens gained should be recorded a `Staking-Reward`.

This is not a taxable event.

### Mining
The `Mining` transaction type is used to identify tokens received as income from mining. The `Income` transaction type could also be used to record this - its use is purely descriptive.

These transaction records will appear within your income tax report. See [HMRC guidance on mining transactions](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto21150).

### Staking-Reward
The `Staking` transaction type is used to identify tokens received as income from staking.

These transaction records will appear within your income tax report. See [HMRC guidance on staking](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto21200).

If staking income is received as return for the lending of tokens (or providing liquidity), and beneficial ownership of those tokens transfers to the borrower/lending platform, then additional transaction records will need to be added to record disposals for both the lending and the repayment, see [HMRC guidance on making a DeFi loan](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto61620).

It's also possible that staking tokens received are considered capital instead of income, see [HMRC guidance on nature of the return](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto61214).

Our [HMRC DeFi examples](https://github.com/BittyTax/BittyTax/wiki/HMRC-Example-Test-Cases#decentralised-finance-defi-1) show you how you can structure your transaction records accordingly.

### Interest
The `Interest` transaction type is used to identify tokens received as interest.

These transaction records will appear within your income tax report.

The same [HMRC guidance on lending and staking](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto61000) as described above will also apply here. 

### Dividend
The `Dividend` transaction type is used to identify tokens received as a dividend.

These transaction records will appear within your income tax report.

### Income
The `Income` transaction type is used to identify tokens received as other income, i.e. income which cannot be categorised as `Mining`, `Staking`, `Interest` or `Dividend`.

These transaction records will appear within your income tax report.

### Gift-Received
The `Gift-Received` transaction type is used to record cryptoasset tokens received as a gift.

A gift received is not taxed as income.

### Fork
The `Fork` transaction type is used to identify tokens received for a new cryptoasset as a result of a blockchain fork.

These tokens are always given a Buy Value of 0, as currently it is not possible to derive a cost from the original cryptoasset, and apportion this to the new one. See [HMRC guidance on Blockchain forks](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto22300).

Tokens received for a fork are not taxed as income.

### Airdrop
The `Airdrop` transaction type is used to record cryptoasset tokens received from an airdrop.

Airdrop tokens are not taxed as income, as it is assumed that nothing was done in return for them.

If the airdrop distribution was dependant upon providing a service or other conditions, then they should be recorded as `Income`. See [HMRC guidance on airdrops](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto21250). 

### Referral
The `Referral` transaction type is used to record tokens received as a reward through a referral program.

Tokens received for referrals are not taxed as income.

### Cashback
The `Cashback` transaction type records tokens received as cashback for a spend transaction.

These tokens are are not taxed as income.

### Fee-Rebate

The `Fee-Rebate` transaction type is used to record tokens received as a rebate of fees.

For example, some exchanges offer rebates to market makers (traders who provide liquidity by posting buy and sell orders), as opposed to traders who execute existing orders (market takers) who are charged a fee.

Fee rebates are are not taxed as income.

### Spend
A `Spend` is a disposal transaction record, which is used to capture the spending of tokens on goods or services.

As a disposal transaction, it is applicable for Capital Gains tax.

### Gift-Sent
A `Gift-Sent` is a disposal transaction record, which identifies cryptoasset tokens sent as a gift.

As a disposal transaction, it is applicable for Capital Gains tax.

### Gift-Spouse
`Gift-Spouse` is a disposal transaction record, it identifies cryptoasset tokens gifted to your spouse or civil partner.

This disposal is recorded as "No-Gain/No-Loss", there will be no gain as the proceeds is calculated to match the acquisition cost (including fees).

Your spouses' accounts should contain an equivalent `Gift-Received` transaction record, with a Buy Value that matches the acquisition cost (minus any fees) as shown in your "No-Gain/No-Loss" disposal.

Note, BittyTax does not take into consideration the "same day" and "bed & breakfast" rules for "No-Gain/No-Loss" disposals.

### Charity-Sent
A `Charity-Sent` is a disposal transaction record, it identifies cryptoasset tokens sent to a registered charity as a gift.

These are not applicable for capital gains, and are considered a "No-Gain/No-Loss" disposal.

Note, BittyTax does not take into consideration the "same day" and "bed & breakfast" rules for "No-Gain/No-Loss" disposals.

### Lost
The `Lost` transaction type is used to record tokens that have been lost or stolen (i.e. private keys are unrecoverable) and a "negligible value claim" has been reported/accepted by HMRC. See [HMRC guidance on losing private keys](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto22400).

The lost tokens are treated as a disposal (for the quantity and value as agreed with HMRC) followed by a reacquisition for the quantity lost, since technically you still own the tokens. If a value is not specified, a default disposal value of zero is assumed.

### Trade
The `Trade` transaction type records the exchange of one cryptoasset for another, or for fiat currency.

This could be for one for the following reasons.

- Fiat-to-crypto *(acquisition)*
- Crypto-to-crypto *(disposal)*
- Crypto-to-fiat *(disposal)*

In the case of a fiat-to-crypto trade, the Sell Asset would be fiat (i.e. GBP or whatever currency you used) and Sell Quantity would contain the amount. There is no reason to specify the Sell Value if the currency is GBP.

In the opposite case, crypto-to-fiat, the Buy Asset would be fiat, and the Buy Quantity the amount in fiat.

Trades which are a *disposal* are applicable for Capital Gains tax.

### Loan
The `Loan` transaction type identifies tokens borrowed as a loan.

If you provided collateral for the loan then this might trigger a capital gains disposal, see [HMRC guidance on making a DeFi loan](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto61620).

### Loan-Repayment
The `Loan-Repayment` transaction type records the repayment (in part or full) of the borrowed tokens. This is separate to any interest charged on the loan.

As a disposal transaction, it is applicable for Capital Gains tax.

### Loan-Interest
The `Loan-Interest` transaction type records interest payments made on the tokens you have borrowed.

As a disposal transaction, it is applicable for Capital Gains tax.

### Margin-Gain
The `Margin-Gain` transaction type records the realised gain from a margin trade, futures, or other derivative trade.

### Margin-Loss
The `Margin-Loss` transaction type records the realised loss from a margin trade, futures, or other derivative trade.

Payment of the loss is a disposal transaction, it is applicable for Capital Gains tax.

### Margin-Fee
The `Margin-Fee` transaction type can be used to record margin fees, funding fees, and/or trade fees for a margin trade, futures, or other derivative trade.

Payment of the fee is a disposal transaction, it is applicable for Capital Gains tax.

### Margin-Fee-Rebate
The `Margin-Fee-Rebate` transaction type records funding fees which are credited to you. This can happen with perpetual futures.

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

If you do get issues, you can run just the audit report on its own using the `--audit` option.

This produces not only the report, but also an audit log in Excel format.

The audit log contains a worksheet per asset, showing the individual balance changes associated with each transaction record. It also shows the transactions raw blockchain data when available, i.e. tx hash as well as, source and destination addresses. This can be useful for matching withdrawals with deposits.

You can see an example audit report [here](https://github.com/BittyTax/BittyTax/blob/master/data/BittyTax_Audit_Report.pdf) and audit log [here](https://github.com/BittyTax/BittyTax/blob/master/data/BittyTax_Audit_Log.xlsx).

#### Tax Report
By default, tax reports are produced for all years which contain taxable events.

If you only want a report for a specific year you can do this using the `-ty` or `--taxyear` option. 

    bittytax <filename> -ty 2023

Full details of the tax calculations can be seen by turning on the debug output (see [Processing](#processing)).

#### Capital Gains
Cryptoasset disposals are listed in date order and by asset.

For a "Bed and Breakfast" disposal, the date of the buyback is given in brackets.

NFT disposals are shown as "Unpooled" unless they are "No-Gain/No-Loss" disposals.

If a disposal results in a loss, the negative amount is highlighted in red.

Totals are listed per asset (if more than 1 disposal) as well as the totals for that tax year.

The **Summary** section provides enough information for you to complete the "Other property, assets and gains" section within your self assessment tax return, or to give to your [accountant](https://github.com/BittyTax/BittyTax/wiki/Crypto-Tax-Accountants-in-the-UK) to complete.

If the disposal proceeds exceed the HMRC reporting threshold (previously 4 times the annual tax-free allowance) this is shown. HMRC requires you to report this in your self assessment even if the gain was within your annual allowance.

HMRC also requires you to include details of each gain or loss. You can use the `--summary` option in combination with `--taxyear` to generate a PDF report which only includes the capital gains disposals and summary for that specific tax year, this can then be attached to your self assessment. You can see an example summary report [here](https://github.com/BittyTax/BittyTax/blob/master/data/BittyTax_Summary_Report.pdf).

The **Tax Estimate** section is given purely as an estimate. Capital gains tax figures are calculated at both the basic and higher rate, and take into consideration the full tax-free allowance.  

Obviously you would need to take into account other capital gains/losses in the same year, and use the correct tax rate according to your income. Always consult with a [professional accountant](https://github.com/BittyTax/BittyTax/wiki/Crypto-Tax-Accountants-in-the-UK) before filing.

#### Income
Income events are listed in date order and by asset, with totals per asset (if more than 1 event).

Totals are also given per Income Type (`Mining`, `Staking`, `Interest`, `Dividend` and `Income`), as well as the totals for that tax year.

By default, fiat currency transactions are excluded, this setting can be changed in the config file, see [Config](#config).

You should check with an [accountant](https://github.com/BittyTax/BittyTax/wiki/Crypto-Tax-Accountants-in-the-UK) for how this should be reported according to your personal situation.

#### Margin Trading
All margin trading transactions (`Margin-Gain`, `Margin-Loss`, `Margin-Fee` and `Margin-Fee-Rebate`) are totalised.

Totals are given per wallet and per contract (which is taken from the Note field of the transaction record), as well as the totals for that tax year.

These figures are NOT included in the **Summary** or **Tax Estimate**  sections.

You will need to check with an [accountant](https://github.com/BittyTax/BittyTax/wiki/Crypto-Tax-Accountants-in-the-UK) whether these derivative trades should be taxed as other income, or capital gains, [HMRC gives little guidance](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto10150).

#### Price Data
The appendix section contains all the historic price data which bittytax has used in the tax calculations.

This includes both fiat and cryptoasset prices, split by tax year.

It is important to check that the symbol names of your assets have been interpreted correctly, and that the prices look reasonable, otherwise your tax calculations will be incorrect. See [Price Tool](#price-tool) for more information on how price data is retrieved.

Links are provided against each price, pointing to the exact data source API which was used to retrieve the data. 

#### Current Holdings
The appendix section also contains details of your remaining cryptoasset balances. The cost (including fees), the current valuation, and the calculated gain (or loss) are shown.

By default, empty wallets are excluded, this setting can be changed in the config file, see [Config](#config).

The data source used to get the latest price is the same as for the historic price data.

### Processing
You can turn on debug using the `-d` or `--debug` option to see full details of how the transaction records are processed.

1. [Import Transaction Records](#import-transaction-records)
1. [Audit Transaction Records](#audit-transaction-records)
1. [Split Transaction Records](#split-transaction-records)
1. [Pool Same Day](#pool-same-day)
1. [Match "same day" Rule](#match-same-day-rule)
1. [Match "bed and breakfast" Rule](#match-bed-and-breakfast-rule)
1. [Process Unmatched (Section 104)](#process-unmatched-section-104)
1. [Integrity Check](#integrity-check)
1. [Process Income](#process-income)
1. [Process Margin Trades](#process-margin-trades)

#### Import Transaction Records
First the transaction records are imported and validated according to their transaction type, making sure that the correct mandatory and optional fields are included.

In the log, the worksheet name (Excel only) and row number are shown against the raw record data being imported.

Empty rows are allowed, and filtered out during the import. Worksheets with a name prefixed by '--' are also filtered, these can be used for doing your own calculations.

Each record is given a unique Transaction ID (TID), these are allocated in chronological order (using the timestamp) regardless of the file ordering.

```
Excel file: example.xlsx
importing 'Sheet1' rows
...
import: 'Sheet1' row[2] ['Deposit', '870', 'GBP', '', '', '', '', '', '', '', 'LocalBitcoins', '2013-05-24 20:16:46', 'from Bank'] [TID:1]
import: 'Sheet1' row[3] ['Trade', '10', 'BTC', '', '870', 'GBP', '', '', '', '', 'LocalBitcoins', '2013-05-24 20:17:40', ''] [TID:2]
import: 'Sheet1' row[4] ['Withdrawal', '', '', '', '10', 'BTC', '', '', '', '', 'LocalBitcoins', '2013-05-24 20:20:49', 'to Desktop wallet'] [TID:3]
import: 'Sheet1' row[5] ['Deposit', '10', 'BTC', '', '', '', '', '', '', '', 'Desktop wallet', '2013-05-24 20:20:49', 'from LocalBitcoins'] [TID:4]
import: 'Sheet1' row[6] ['Deposit', '2693.8', 'USD', '', '', '', '', '', '', '', 'Bitstamp', '2014-05-29 08:33:00', 'from Bank'] [TID:5]
import: 'Sheet1' row[7] ['Spend', '', '', '', '0.002435', 'BTC', '0.8', '', '', '', 'Desktop wallet', '2014-06-26 11:25:02', ''] [TID:6]
import: 'Sheet1' row[8] ['Gift-Sent', '', '', '', '0.02757', 'BTC', '', '', '', '', 'Desktop wallet', '2014-07-18 13:12:47', ''] [TID:7]
import: 'Sheet1' row[9] ['Trade', '0.41525742', 'BTC', '', '257.53', 'USD', '', '1.29', 'USD', '', 'Bitstamp', '2014-07-23 10:58:00', ''] [TID:8]
import: 'Sheet1' row[10] ['Trade', '0.58474258', 'BTC', '', '362.63', 'USD', '', '1.82', 'USD', '', 'Bitstamp', '2014-07-23 10:58:00', ''] [TID:9]
import: 'Sheet1' row[11] ['Trade', '0.86', 'BTC', '', '521.16', 'USD', '', '2.51', 'USD', '', 'Bitstamp', '2014-07-24 13:08:00', ''] [TID:10]
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
audit: TR Withdrawal 4.40027953 BTC + fee=0.0001 BTC 'Bitstamp' 2014-07-24T21:01:00 UTC 'to Desktop wallet' [TID:13]
audit:   Bitstamp:BTC=0.0001 (-4.40027953)
audit:   Bitstamp:BTC=0 (-0.0001)
```

#### Split Transaction Records
Before any tax calculations can take place, transaction records need to be split into their constitute parts, in terms of cryptoasset buys and cryptoasset sells (each with their own valuation in GBP).

This requires the buy, sell and fee assets in the transaction record first to be given a valuation, that is unless a fixed value has already been specified, or the asset is already in GBP.

Valuations are calculated via one of the historic price date sources, see [Price Tool](#price-tool) for how.

For crypto-to-crypto trades the same valuation is given to both the buy and the sell asset, except where fixed values have been specified.

Note that `Deposit` and `Withdrawal` transactions are not taxable events so no valuation is required.

In the log, any transaction buys (BUY) or sells (SELL) that are created by the split are shown below the transaction record (TR). These transactions have unique TIDs allocated sequentially based on the parent transaction ID, i.e. (34.1, 34.2, 34.3, etc).

If historic price data has been used for the valuation, it is indicated by the `~` symbol, fixed values are show as `=`.

GBP values are displayed with 2 decimal places, although no actual rounding has taken place. Rounding only happens when a taxable event is recorded.

Timestamps are normalised to be in local time (GMT or BST). This is so that tax calculations for the same day will be correct.

##### Fee Handling
Each buy or sell transaction can include a fee. Its value is populated by the fee specified in the transaction record.

If a transaction record involves more than one cryptoasset (i.e. a `Trade` crypto-to-crypto) then the fee's valuation has to be split evenly between the buy and sell transactions.

If the fee asset is also a cryptoasset, then paying the fee counts as a separate disposal. This is recorded by adding an additional `Spend` transaction.

Non-taxable transactions (i.e. `Deposit` and `Withdrawal`) are marked with `*` in the log and have no GBP valuation.

```console
split transaction records
...
split: TR Trade 10 BTC <- 870 GBP 'LocalBitcoins' 2013-05-24T20:17:40 UTC [TID:2]
split:   BUY Trade 10 BTC (=£870.00 GBP) 'LocalBitcoins' 2013-05-24T21:17:40 BST [TID:2.1]
split:   SELL Trade 870 GBP (=£870.00 GBP) 'LocalBitcoins' 2013-05-24T21:17:40 BST [TID:2.2]
...
split: TR Withdrawal 7 BTC + fee=0.0002 BTC 'Desktop wallet' 2017-03-24T22:57:44 UTC 'to Poloniex' [TID:32]
price: 2017-03-24, 1 BTC=751.27 GBP via CryptoCompare (Bitcoin)
price: 2017-03-24, 1 BTC=£751.27 GBP, 0.0002 BTC=£0.15 GBP
split:   SELL* Withdrawal 7 BTC 'Desktop wallet' 2017-03-24T22:57:44 GMT 'to Poloniex' [TID:32.1]
split:   SELL Spend 0.0002 BTC (~£0.15 GBP) 'Desktop wallet' 2017-03-24T22:57:44 GMT 'to Poloniex' [TID:32.2]
split: TR Deposit 7 BTC 'Poloniex' 2017-03-24T22:57:44 UTC 'from Desktop wallet' [TID:33]
split:   BUY* Deposit 7 BTC 'Poloniex' 2017-03-24T22:57:44 GMT 'from Desktop wallet' [TID:33.1]
split: TR Trade 1.00000013 ETH <- 0.03729998 BTC + fee=0.0015 ETH 'Poloniex' 2017-04-12T19:38:26 UTC [TID:34]
price: 2017-04-12, 1 BTC=974.79 GBP via CryptoCompare (Bitcoin)
price: 2017-04-12, 1 BTC=£974.79 GBP, 0.03729998 BTC=£36.36 GBP
split:   BUY Trade 1.00000013 ETH (~£36.36 GBP) + fee=~£0.03 GBP 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.1]
split:   SELL Trade 0.03729998 BTC (~£36.36 GBP) + fee=~£0.03 GBP 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.2]
split:   SELL Spend 0.0015 ETH (~£0.05 GBP) 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.3]
```

### Pool Same Day
HMRC stipulates that ["*All shares of the same class in the same company acquired by the same person on the same day and in the same capacity are treated as though they were acquired by a single transaction*"](https://www.gov.uk/hmrc-internal-manuals/capital-gains-manual/cg51560#IDATX33F). This applies in the same way to disposals.

Tokens of the same cryptoasset acquired on the same day are pooled together into a single buy transaction. The same applies for tokens disposed of on the same day - they are pooled into a single sell transaction.

Only taxable transactions (i.e. acquisitions and disposals) are included within these pools.

The transaction types (`Gift-Spouse`, `Charity-Sent` and `Lost`) are not included within these pools because of their special handling.

NFTs are not pooled or matched as per the [HMRC guidance on pooling](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto22200):

> Non-Fungible Tokens (NFTs) are separately identifiable and so are not pooled and no matching rules are applied.

Pooled transactions are indicated by a transaction count at the end. The transactions contained within the pool are then indented below it, and shown with brackets.

```console
pool same day transactions
pool: BUY Trade 1 BTC (~£364.22 GBP) + fee=~£1.83 GBP 'Bitstamp' 2014-07-23T11:58:00 BST [TID:8.1] (2)
pool:   (BUY Trade 0.41525742 BTC (~£151.25 GBP) + fee=~£0.76 GBP 'Bitstamp' 2014-07-23T11:58:00 BST [TID:8.1])
pool:   (BUY Trade 0.58474258 BTC (~£212.97 GBP) + fee=~£1.07 GBP 'Bitstamp' 2014-07-23T11:58:00 BST [TID:9.1])
pool: BUY Trade 3.40037953 BTC (~£1,211.82 GBP) + fee=~£5.64 GBP 'Bitstamp' 2014-07-24T14:08:00 BST [TID:10.1] (3)
pool:   (BUY Trade 0.86 BTC (~£306.44 GBP) + fee=~£1.48 GBP 'Bitstamp' 2014-07-24T14:08:00 BST [TID:10.1])
pool:   (BUY Trade 0.9 BTC (~£320.87 GBP) + fee=~£1.48 GBP 'Bitstamp' 2014-07-24T14:08:00 BST [TID:11.1])
pool:   (BUY Trade 1.64037953 BTC (~£584.51 GBP) + fee=~£2.69 GBP 'Bitstamp' 2014-07-24T14:09:00 BST [TID:12.1])
```

### Match "same day" Rule
See ["*The "same day" rule TCGA92/S105(1)*"](https://www.gov.uk/hmrc-internal-manuals/capital-gains-manual/cg51560#IDATX33F).

This tax function matches any buy and sell transactions, of the same cryptoasset, that occur on the same day. 

If the buy and sell quantities do not match, the transaction with the larger quantity will be split into two, and the cost and fee apportioned between them.

This allows a gain or a loss to be calculated for the matching transactions, taking into consideration the combined fees. The transaction containing the remainder is then carried forward, and used in further tax calculations.

In the log, you can see which transactions have been "*same day*" matched, if a buy or sell has been split, and the resulting disposal event.

New transactions created by a split are allocated the next TID in sequence.

```console
match same day transactions
...
match: BUY Trade 249.23062521 ETH (~£9,060.76 GBP) + fee=~£11.31 GBP 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.1] (4)
match: SELL Spend 0.62207655 ETH (~£22.62 GBP) 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.3] (4)
match:   split: BUY Trade 0.62207655 ETH (~£22.62 GBP) + fee=~£0.03 GBP 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.4] (4)
match:   split: BUY Trade 248.60854866 ETH (~£9,038.15 GBP) + fee=~£11.28 GBP 'Poloniex' 2017-04-12T20:38:26 BST [TID:34.5] (4)
match:   Disposal(same day) gain=£-0.03 (proceeds=£22.62 - cost=£22.62 - fees=£0.03)
```

### Match "bed and breakfast" Rule
See ["*The "bed and breakfast" rule TCGA92/S106A(5) and (5A)*"](https://www.gov.uk/hmrc-internal-manuals/capital-gains-manual/cg51560#IDATR33F).
 
This tax function matches sells to buybacks of the same cryptoasset which occur within 30 days.

**Important:** you need to include transactions 30 days after the end of tax year (5th April) in order for this tax calculation to be correct.

As with the ["same day"](#match-same-day-rule) rule, if the buy and sell quantities do not match, a transaction will be split.

Transactions are sorted by timestamp, and matched in chronological order.

Any matched "same day" transactions are excluded from this rule.

In the log, you can see which transactions have been matched by the "*bed & breakfast*" rule, and the resulting disposal event.

```console
match bed & breakfast transactions
...
match: SELL Spend 5.32306861 BTC (~£1,483.06 GBP) + fee=~£1.48 GBP '<pooled>' 2016-01-27T22:09:19 GMT '<pooled>' [TID:16.2] (6)
match: BUY Trade 5.54195456 BTC (~£1,475.82 GBP) + fee=~£1.48 GBP 'Poloniex' 2016-01-29T13:51:01 GMT [TID:23.5] (9)
match:   split: BUY Trade 5.32306861 BTC (~£1,417.53 GBP) + fee=~£1.42 GBP 'Poloniex' 2016-01-29T13:51:01 GMT [TID:23.6] (9)
match:   split: BUY Trade 0.21888595 BTC (~£58.29 GBP) + fee=~£0.06 GBP 'Poloniex' 2016-01-29T13:51:01 GMT [TID:23.7] (9)
match:   Disposal(bed & breakfast) gain=£62.63 (proceeds=£1,483.06 - cost=£1,417.53 - fees=£2.90)
```

### Process Unmatched (Section 104)
Any transactions which remain unmatched are processed according to Section 104 Taxation of Capital Gains Act 1992.

Each cryptoasset is held in its own pool, known as a Section 104 holding. The unmatched transactions are processed in chronological order.

As tokens are acquired, the total cost and total fees for that cryptoasset holding increases.

If all tokens in a holding are disposed of, the cost will be the total cost of that cryptoasset holding, and likewise, the fees would be the total fees.

If only some tokens are disposed of, the cost is calculated as a fraction of the total cost. This fraction is calculated by the number of tokens disposed of divided by the total number of tokens held. The fees are also calculated as a fraction in the same way.

The gain or loss is then calculated by subtracting this cost and any fees from the proceeds of the disposal. Fees are included from both the Section 104 holding (acquisition fees) and also the disposal fee.

Transactions which have been "matched", or "transfer" (non-taxable) transactions are excluded from the Section 104 holding, and denoted with // at the start.

As the unmatched transactions are processed, the impact it has on the individual holding is shown in the log.

When a disposal takes place, the gain calculation is then shown below. 

```console
process unmatched transactions
...
section104: BUY Trade 0.21888595 BTC (~£58.29 GBP) + fee=~£0.06 GBP 'Poloniex' 2016-01-29T13:51:01 GMT [TID:23.7] (9)
section104:   BTC=17.58916048 (+0.21888595) cost=£2,943.37 GBP (+£58.29 GBP) fees=£7.47 GBP (+£0.06 GBP)
section104: //SELL Spend 0.01110608 BTC (~£2.96 GBP) 'Poloniex' 2016-01-29T14:12:31 GMT [TID:23.3] (7) <- matched
section104: //SELL* Withdrawal 7 BTC 'Desktop wallet' 2017-03-24T22:57:44 GMT 'to Poloniex' [TID:32.1] <- transfer
section104: SELL Spend 0.0002 BTC (~£0.15 GBP) 'Desktop wallet' 2017-03-24T22:57:44 GMT 'to Poloniex' [TID:32.2]
section104:   BTC=17.58896048 (-0.0002) cost=£2,943.33 GBP (-£0.03 GBP) fees=£7.47 GBP (-£0.00 GBP)
section104:   Disposal(section 104) gain=£0.12 (proceeds=£0.15 - cost=£0.03 - fees=£0.00)
```

### Integrity Check 
The integrity check compares the final balances from the audit against the final balances of the Section 104 pools.

Its purpose is to find issues with transfer transactions which might impact your tax calculations.

The integrity check will only be successful if your transaction records are complete (i.e. there is a matching Deposit for every Withdrawal).

You can bypass this check by using the `--skipint` option.

Possible reasons for failure:

1. Withdrawal has a missing Deposit.
1. A Withdrawal and its corresponding Deposit have mismatching quantities.
1. The Withdrawal quantity is not the net amount (after fee deduction), with the fee specified.
1. The Deposit quantity is not the gross amount (before fee deduction), with the fee specified.
1. Withdrawal/Deposit transactions have been used incorrectly (they should only be used to move existing tokens between your own wallets).

In this example below, there is a difference (-negative) detected for BTC. This means that 0.0002 BTC has gone missing between transfers.

```console
integrity check: failed
WARNING Integrity check failed: audit does not match section 104 pools, please check Withdrawals and Deposits for missing fees

Asset                Audit Balance          Section 104 Pool                Difference
BTC                    14.00369127               14.00389127                   -0.0002
```

An easy way to find any discrepancies is to use the audit log spreadsheet, see [Audit](#audit).

You can use the column filter to select only `Deposit` and `Withdrawal` as the Type. This makes it easy to see any transfer mismatches.

### Process Income
This function searches through all the original transactions, and records any that are applicable for income tax. Currently this is `Mining`, `Staking`, `Interest`, `Dividend` and `Income` transaction types.

### Process Margin Trades
This function searches through all the original transactions, and records any that are for margin trading, i.e. `Margin-Gain`, `Margin-Loss`, `Margin-Fee` and `Margin-Fee-Rebate`.

## Conversion Tool
The bittytax conversion tool `bittytax_conv` takes all of the data files exported from your wallets and exchanges, normalises them into the transaction record format required by bittytax, and consolidates them into a single Excel spreadsheet for you to review, make edits, and add any missing records.

Don't worry if you don't have Microsoft Excel installed. These spreadsheets will work with [LibreOffice](https://www.libreoffice.org) or [OpenOffice](https://www.openoffice.org). You can also use [Google Sheets](https://www.google.co.uk/sheets/about/) or [Numbers for Mac](https://www.apple.com/uk/numbers/), although some conditional formatting is not supported.

Each converted file appears within its own worksheet. Data files of the same format are aggregated together. The transaction records and the original raw data appear side by side, sorted by timestamp, making it easier for you to review and to provide traceability.

The converter takes care of all the cell formatting to ensure that all decimal places are displayed correctly, and if numbers exceed 15-digits of precision (an Excel limitation) they are stored as text to prevent any truncation.

For most wallet files, transactions can only be categorised as deposits or withdrawals. You will need to edit these to reflect your real transactions (i.e. spends, gifts, income, etc.). This is easy with Excel, as the valid options are selectable via a dropdown menu.

**Wallets:**
- AdaLite
- Blockchain.com
- Coinomi
- Electrum
- Eternl
- Exodus
- HandCash
- Helium
- Ledger Live
- MyMonero
- Nault
- Neon Wallet
- Qt Wallet (i.e. Bitcoin Core)
- Trezor
- Volt
- Yoroi
- Zelcore

**Exchanges:**
- [Binance](https://github.com/BittyTax/BittyTax/wiki/Exchange:-Binance)
- Binance.US
- Bitfinex
- Bitpanda
- Bitstamp
- Bittrex
- Bittylicious
- Blockchain.com Exchange
- ByBit
- Cash App
- CEX.IO
- Changelly
- ChangeTip 
- Circle
- Coinbase
- Coinbase Pro
- CoinCorner
- Coinfloor
- CoinList
- Coinmetro
- Crypto.com
- Cryptopia
- Cryptsy
- Deribit
- Easy Crypto
- FTX
- Gate.io
- Gatehub
- Gemini
- Gravity (Bitstocks)
- HitBTC
- Hotbit
- Kinesis
- Kraken
- KuCoin
- LBank
- Liquid
- Mercatox
- MEXC
- OKX
- Paxful
- PayPal
- Poloniex
- qTrade
- Revolut
- Robinhood
- SwissBorg
- TradeOgre
- TradeSatoshi
- Uphold
- Voyager
- WhiteBIT
- Wirex

**Savings & Loans**
- BlockFi
- BnkToTheFuture
- Celsius
- Nexo

**Explorers:**
- Aptoscan
- Blockscout
- BscScan
- Etherscan
- FatStx
- HecoInfo
- Helium Explorer
- Snowtrace
- PolygonScan
- SnowTrace
- Subscan
- Zerion

**Accounting:**
- Accointing
- BitcoinTaxes
- Blockpit
- CoinTracker
- CoinTracking
- Koinly
- StakeTax

### Usage
The help option displays a full list of recognised data file formats, as well as details of all command line arguments.

    bittytax_conv --help

To use the conversion tool (assuming you've already exported your data), just enter the filenames of all your data files, in any order, as command arguments. You can also pass in a directory and it will recursively search all files and folders for processing.

Most terminals allow you to drag and drop files from the desktop into the terminal window, this saves you time by giving you the correct file path without having to enter it manually.

    bittytax_conv <filename> [<filename> ...]

Each file is analysed to try and match it against one of the recognised formats. If successful, an Excel file will be generated with the default filename `BittyTax_Records.xlsx`. Unrecognised files are skipped and a warning displayed.

If you want to change the default filename you can use the `-o` argument followed by the output filename.

    bittytax_conv <filename> [<filename> ...] -o <output filename>

Note, it is important that you always pass the original raw files into the conversion tool. If you open your CSV files in Excel first and make edits, it can mess with the date formats, etc and cause issues with the conversion. 

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

    bittytax_conv --format CSV <filename> | bittytax --audit --nopdf

This will instantly show you what the remaining balance of each asset should be for that wallet or exchange file.

**Recap**

You can also use the conversion tool to convert your wallet or exchange files into the import CSV format used by Recap (see https://help.recap.io/en/articles/2631702-importing-csvs-into-custom-accounts).

    bittytax_conv --format RECAP <filename>

### Notes:
1. Some exchanges only allow the export of trades. This means transaction records of deposits and withdrawals will have to be created manually, otherwise the assets will not balance.
1. Bitfinex - when exporting your data, make sure the "*Date Format*" is set to "*DD-MM-YY*" which is the default.
1. Etherscan - for ERC-20 (Tokens) and ERC-721 (NFTs) exports, it is important that the filename contains your ethereum address (Etherscan does this by default), as it is used to determine if transactions are being sent or received.
1. Kraken - export just the "*Ledgers*" history.

## Price Tool
The bittytax price tool `bittytax_price` allows you to get the latest and historic prices of cryptoassets and foreign currencies. Its use is not strictly required as part of the process of completing your accounts, but provides a useful insight into the prices which bittytax will assign when it comes to value your cryptoassets in UK pounds (or other [local currency](https://github.com/BittyTax/BittyTax#local_currency)).

**Data Sources:**
The following price data sources are available.

- [BittyTaxAPI](https://github.com/BittyTax/BittyTax/wiki/BittyTaxAPI) - foreign currency exchange rates *(primary fiat)*
- [Frankfurter](https://www.frankfurter.app) - foreign currency exchange rates 
- [Crypto Compare](https://min-api.cryptocompare.com) - cryptoasset prices *(primary crypto)*
- [CoinGecko](https://www.coingecko.com/en/api) - cryptoasset prices *(secondary crypto)*
- [Coinpaprika](https://coinpaprika.com/api/) - cryptoasset prices

The priority (primary, secondary, etc) to which data source is used and for which asset is controlled by the `bittytax.conf` config file, (see [Config](#config)). If your cryptoasset cannot be identified by the primary data source, the secondary source will be used, and so on. 

All historic price data is cached within the .bittytax/cache folder in your home directory. This is to prevent repeated lookups and reduce load on the APIs which could fail due to throttling.

### Usage
To get the latest price of an asset, use the `latest` command, followed by the asset symbol name. This can be a cryptoasset (i.e. BTC) or a foreign currency (i.e. USD). An optional quantity can also be specified.

    bittytax_price latest asset [quantity]

If the lookup is successful not only will the price be displayed in the terminal window, but also the data source used and the full name of the asset. This is useful in making sure the asset symbol name you are using in your transaction records is the correct one.

```console
$ bittytax_price latest ETH 0.5
1 ETH=0.03375 BTC via CryptoCompare (Ethereum)
1 BTC=79,565.35 GBP via CryptoCompare (Bitcoin)
1 ETH=£2,685.33 GBP
0.5 ETH=£1,342.67 GBP
```

If you wish to perform a historic data lookup, use the `historic` command instead, followed by the asset symbol name and the date.  The date can be in either `YYYY-MM-DD` or `DD/MM/YYYY` format.

    bittytax_price historic asset date [quantity]

By specifying a quantity to price, you can use the tool to calculate the historic price of a specific transaction. This can be used as a memory jogger if you are looking at old wallet transactions and trying to remember what it was you spent your crypto on!

```console
$ bittytax_price historic BTC 2014-06-24 0.002435
1 BTC=360.59 GBP via CryptoCompare (Bitcoin)
1 BTC=£360.59 GBP
0.002435 BTC=£0.88 GBP
```

Since there is no standardisation of cryptoasset symbols, it's possible that the same symbol will have different meanings across data sources. For example, EDG is Edgeless on CryptoCompare, but can also be Edgeware on CoinPaprika.

A quick way to check this is to use the `list` command, followed by an asset symbol name.

    bittytax_price list [asset]

This command will return any matches it finds for that asset symbol name across all the data sources. Some data sources use an asset ID to differentiate between those with the same symbol name.

The `<-` arrow to the right indicates which data source/asset ID will be automatically selected by the price tool.

```console
$ bittytax_price list EDG
EDG (Edgeless) via CryptoCompare [ID:edg] <-
EDG (Edgeless) via CoinPaprika [ID:edg-edgeless]
EDG (Earth Dog) via CoinPaprika [ID:edg-earth-dog]
EDG (Edgeware) via CoinPaprika [ID:edg-edgeware]
```

If you are having trouble identifying the symbol name to use, you can use the `-s` option, followed by a search term.

```console
$ bittytax_price list -s edgeware
EDG (Edgeware) via CoinPaprika [ID:edg-edgeware]
EDGEW (Edgeware) via CryptoCompare [ID:edgew] <-
```

You can also get a complete list of all the supported assets (in alphabetical order) by not specifying any asset or search term.

If bittytax is not picking up the correct asset price for you, you can change the config so the symbol name uses a different data source and asset ID. See [Config](#config).

The `latest` and `historic` price commands also give you the `-ds` option to override the config and specify the data source directly. It's a quick way to check asset prices are correct before updating your config.

```console
$ bittytax_price historic EDG 2025-01-01 -ds CoinPaprika
1 EDG=0.00000062 BTC via CoinPaprika (Edgeless)
1 BTC=75,338.83 GBP via CryptoCompare (Bitcoin)
1 EDG=£0.05 GBP 
```

You can also set the data source to `ALL`, this will return price data for all data sources which have a match. If the [Price Data](#price-data) appendix in your tax report has any missing data, you can use this method to find prices. Some data sources have price history going back further than others.

```console
$ bittytax_price historic EDG 2025-01-01 -ds ALL
1 EDG=0.00000003 BTC via CryptoCompare (Edgeless) <-
1 BTC=75,338.83 GBP via CryptoCompare (Bitcoin)
1 EDG=£0.00 GBP
1 EDG=0.00000062 BTC via CoinPaprika (Edgeless)
1 BTC=75,338.83 GBP via CryptoCompare (Bitcoin)
1 EDG=£0.05 GBP
```

To get full details of all arguments, use the help option, either on its own or for a specific command.

    bittytax_price [command] --help

### Notes:
1. Both CoinGecko and CoinPaprika have recently changed their non-paid usage plans to only include 12 months of daily historic price data. Retrieving data older than this might result in failure.
1. Not all data source APIs return prices in UK pounds (GBP), for this reason cryptoasset prices are requested in BTC and then converted from BTC into UK pounds (GBP) as a two step process. This may change in the near future for stablecoins, see [#82](https://github.com/BittyTax/BittyTax/issues/82).
1. Some APIs return multiple price points for the same day. CryptoCompare uses the 'close' price. CoinGecko and CoinPaprika use the 'open' price. See [#45]( https://github.com/BittyTax/BittyTax/issues/45).
1. Historical price data is cached for each data source as a separate JSON file in the .bittytax/cache folder within your home directory. Beware if you are changing a symbol name to point to a different data source/asset ID as previous data might be cached.
1. CoinPaprika does not support BTC/GBP historic prices.

## Config
The `bittytax.conf` file resides in the .bittytax folder within your home directory.

The [default](https://github.com/BittyTax/BittyTax/blob/master/src/bittytax/config/bittytax.conf) file created at runtime should cater for most users.

If you need to change anything, the parameters are described below. The file is in YAML format.

If you want to check your config settings, turn on debug.

```
bittytax -d
```

| Parameter | Default | Description |
| --- | --- | --- |
| `local_currency:` | `GBP` | Local currency used for pricing assets |
| `local_timezone:` | `Europe/London` | Local timezone used by the conversion tool |
| `date_is_day_first:` | `True` | Local date format used by the conversion tool |
| `fiat_list:` | `['GBP', 'EUR', 'USD', 'AUD', 'NZD', 'CAD', 'PLN']` | List of fiat symbols used |
| `crypto_list:` | `['BTC', 'ETH', 'XRP', 'LTC', 'BCH', 'BNB', 'USDT', 'USDC']` | List of prioritised cryptoasset symbols |
| `trade_asset_type:` | `2` | Method used to calculate asset value in a trade |
| `trade_allowable_cost_type:` | `2` | Method used to attribute the trade fee |
| `transaction_fee_allowable_cost:` | `True` | Transaction fees are an allowable cost |
| `audit_hide_empty:` | `False` | Hide empty balances/wallets from the audit |
| `show_empty_wallets:` | `False` | Include empty wallets in current holdings report |
| `transfers_include:` | `False` | Include transfer transactions in the tax calculations |
| `transfer_fee_disposal:` | `True` | Transfer fees are a disposal |
| `transfer_fee_allowable_cost:` | `False` | Transfer fees are an allowable cost |
| `fiat_income:` | `False` | Include fiat transactions in the income report |
| `lost_buyback:` | `True` | Lost tokens should be reacquired |
| `large_data:` | `False` | Optimise for large amounts of data |
| `legacy_report:` | `False` | Use legacy PDF report format |
| `data_source_select:` | `{}` | Map asset to a specific data source(s) for prices |
| `data_source_fiat:` | `['BittyTaxAPI']` | Default data source(s) to use for fiat prices |
| `data_source_crypto:` | `['CryptoCompare', 'CoinGecko']` | Default data source(s) to use for cryptoasset prices |
| `usernames:` | `[]` | ChangeTip parser: list of usernames used |
| `coinbase_zero_fees_are_gifts:` | `False` | Coinbase parser: treat zero fees as gifts |
| `binance_multi_bnb_split_even:` | `False` | Binance parser: split BNB amount evenly across tokens converted to BNB at the same time |
| `binance_statements_only:` | `False` | Binance parser: use statements data files for all transaction types |

### local_currency
The local currency used for pricing assets, default is GBP. See [International support](https://github.com/BittyTax/BittyTax/wiki/International-Support).

### local_timezone
The local timezone used by the conversion tool for some data files which have local timestamps, default is 'Europe/London'. See [International support](https://github.com/BittyTax/BittyTax/wiki/International-Support).

### date_is_day_first
The local date format used by the conversion tool for some data files which are in a localised format. See [International support](https://github.com/BittyTax/BittyTax/wiki/International-Support).

- `True` = DD/MM/YYYY (default)
- `False` = MM/DD/YYYY

### fiat_list
Used to differentiate between fiat and cryptoasset symbols. Make sure you configure all fiat currencies which appear within your transaction records here.

### crypto_list
Identifies which cryptoasset takes priority when calculating the value of a crypto-to-crypto trade (see [trade_asset_type](#trade_asset_type)). The priority is taken in sequence, so in an ETH/BTC trade, the value of the BTC would be used in preference to ETH when pricing the trade.

The list should contain the most prevalent cryptoassets which appear in exchange trading pairs. These are predominantly the higher market cap. tokens.

### trade_asset_type
Controls the method used to calculate the asset value of a trade:

- `0` = Buy asset value  
- `1` = Sell asset value  
- `2` = Priority asset value *(default)*

For every trade there are always two assets involved: fiat-to-crypto, crypto-to-fiat or crypto-to-crypto. When bittytax is trying to calculate the value of a trade, it uses this parameter to determine which asset value should be used to price the trade in UK pounds.

For trades involving fiat, it's obvious that we want to price the asset using the fiat value. However, it's not so straight forward for crypto-to-crypto trades.

The recommended setting is `2` (Priority). This means that the asset value chosen will be selected according to the priority order defined by the `fiat_list` and `crypto_list` parameters combined. Fiat will always be chosen first, followed by the most prevalent cryptoasset.

Setting this parameter to `1` or `2` will result in either the buy asset value or the sell asset value always being used, regardless of whether the trades involved fiat or not. 

### trade_allowable_cost_type
Controls the method used to attribute the trade fee (an allowable cost) to the assets in a crypto-to-crypto trade.

- `0` = Buy asset
- `1` = Sell asset
- `2` = Split evenly between the buy and sell asset (default)

The guidance from [HMRC on allowable expenses](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto22150#exchange-fees), indicates that "*the fee is attributable to both assets*" when swapping one token for another.

### transaction_fee_allowable_cost
Controls if transaction fees (the fee paid to miners for storing transactions on the blockchain) are an allowable cost or not.

- `True` = transaction fees are an allowable cost (default)
- `False` = transaction fees are NOT an allowable cost

### audit_hide_empty
Hide empty balances, and the entire wallet (if all balances are empty) from the audit. Can be set to `True` or `False`. Default is `False`.

### show_empty_wallets
Include empty wallets in the current holdings report. Can be set to `True` or `False`. Default is `False`.

### transfers_include
Controls the method used to handle transfer transactions types (`Deposit` and `Withdrawal`) in the tax calculations. 

- `True` = Transfers included
- `False` = Transfers excluded (default)

The pros and cons of each method are listed below:

#### "Transfers included"
1. Disposals NOT allowed between a Withdrawal and a Deposit (this is because the cost basis would be wrong, as the tokens are temporarily removed and then re-added).
1. Fees do NOT need to be specified for transfers; they are implied by the difference between the 2 transfer transactions (i.e. what is lost is the fee).
1. Integrity check will verify that no disposals occur during a transfer.
1. Transfer fees are removed from the section 104 pool at zero cost.
1. Not possible to configure transfer fees as disposal (taxable event).
1. Not possible to configure transfer fees as an allowable cost.

#### "Transfers excluded (default)"
1. Disposals between a Withdrawal and a Deposit are allowed.
1. All transfer fees have to be specified, the Withdrawal quantity and its corresponding Deposit quantity should match, so everything will balance when they are excluded from the tax calculations.
1. Integrity check will verify that the audit balances match the section 104 pools. This is to make sure transfers have been recorded correctly and no transfer fees are missing.
1. Transfer fees can be configured as zero cost.
1. Transfer fees can be configured as a disposal (taxable event).
1. Transfer fees can be configured as an allowable cost.

### transfer_fee_disposal
This parameter is only relevant if transfers are excluded from the tax calculations (i.e. transfer fees have been specified).

- `True` = The transfer fee is a disposal, a taxable event (default)
- `False` = Not a disposal, transfer fee removed from the pool at zero cost

From the [HMRC guidance on what is a disposal](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto22100), "*There is no disposal if the individual retains beneficial ownership of the tokens throughout the transaction, for example moving tokens between public addresses that the individual beneficially controls (commonly described as moving tokens between wallets).*"

Although not explicitly stated, this implies that those tokens used to pay the transfer fee (i.e. paid to the miner to add the transaction to a block), would be disposal, under the rule "*using tokens to pay for goods or services*".

### transfer_fee_allowable_cost
This parameter is only relevant if transfer fees are disposals.

- `True` = Transfer fee is an allowable cost, results in the disposal with zero gain.
- `False` = Transfer fee is NOT an allowable cost (default) 

The [HMRC guidance on allowable expenses](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto22150#exchange-fees) does not specifically cover transfer fees, "*transaction fees paid for having the transaction included on the distributed ledger*" is an allowable cost, but only for a disposal, transfers between your own wallets are not disposals, but paying the fee is? The guidance could be interpreted either way, our default and recommendation is that they are NOT an allowable cost.   

### fiat_income
Include transactions in fiat currency in the income report. Can be set to `True` or `False`. Default is `False`.

### lost_buyback
This controls whether a `Lost` transaction type results in a reacquisition, as per the [HMRC guidance on losing private keys](https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual/crypto22400).

- `True` = Lost tokens are reacquired (default)
- `False` = Lost tokens are removed

This could be used in the future when implementing tax rules for different countries.

### large_data
Make optimisations to BittyTax for working with large amounts of data.

1. Disable the duplicate records check in the Conversion Tool. (this can be very slow for large files)
2. Disable conditional formatting of the Buy/Sell/Fee quantities in the Excel file.

Without conditional formatting, quantities that are integers (whole numbers) will be displayed with a decimal point after them, i.e. `100.`.

Can be set to `True` or `False`. Default is `False`.

### legacy_report
Format the PDF report with legacy styling.

- `True` = legacy PDF report (as per BittyTax v0.5)
- `False` = new colour PDF format

### data_source_select
Maps a specific asset symbol name to a list of data source(s) with asset IDs in priority order.

This parameter overrides the any data sources defined by `data_source_fiat` and `data_source_crypto` (see below).

If, for example you wanted EDG to map to Edgeware from CoinPaprika as the data source, overriding the default which is CryptoCompare. You would change the config as follows.

```yaml
data_source_select: {
    'EDG': ['CoinPaprika:edg-edgeware'],
    }
```

To identify a specific asset ID for a datasource, you can use the `:` colon separator.

You can also define a custom asset symbol. In the example, EDGW is used to avoid a clash with EDG.

```yaml
data_source_select: {
    'EDG': ['CoinPaprika:edg-edgeware'],
    'EDGW': ['CryptoCompare:edg'],
    }
```

### data_source_fiat
Specifies which data source(s), in priority order, will be used for retrieving foreign currency exchange rates.

```yaml
data_source_fiat:
    ['BittyTaxAPI']
```

Supported data sources for fiat are:
- `BittyTaxAPI`
- `Frankfurter`

### data_source_crypto
Specifies which data source(s), in priority order, will be used for retrieving cryptoasset prices.

```yaml
data_source_crypto:
    ['CryptoCompare', 'CoinGecko']
```

Supported data sources for cryptoassets are:
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

### coinbase_zero_fees_are_gifts
This parameter is only used by the conversion tool. It controls how the Coinbase parser will handle a zero fee "Buy" trade.

- `True` = Zero fee "Buy" is a `Gift-Received`
- `False` = Zero fee "Buy" is a `Trade` (default) 

Some old Coinbase transactions show referrals/airdrops as trades, the only way to differentiate these is they have zero fees. This is not fool proof since it's possible (but not common) for a trade to also have zero fees.

### binance_multi_bnb_split_even
This parameter is only used by the conversion tool.

For Binance statements data files, this parameter allows you to split the BNB amount evenly across multiple tokens converted at the same time.

By default, the BNB Buy Quantities will be left blank, which you then have to manually populate using data from the Binance website. If the website data is not available (3 months max), this parameter might be your only option.

Can be set to `True` or `False`. Default is `False`.

You can also override this config setting by using the `--binance_multi_bnb_split_even` argument with the conversion tool.

### binance_statements_only
This parameter is only used by the conversion tool.

It allows Binance statements data files to be used for ALL transaction types.

This can be useful if the individual data files (deposits, withdrawals, trades, etc) are no longer available, see [wiki](https://github.com/BittyTax/BittyTax/wiki/Exchange:-Binance).

Can be set to `True` or `False`. Default is `False`.

You can also override this config setting by using the `--binance_statements_only` argument with the conversion tool.

## Resources
**HMRC Links:**
- https://www.gov.uk/government/collections/cryptoassets
- https://www.gov.uk/hmrc-internal-manuals/cryptoassets-manual
- https://www.gov.uk/hmrc-internal-manuals/vat-finance-manual/vatfin2330
- https://www.gov.uk/government/publications/cryptoassets-taskforce

**HMRC Webinar**
- https://www.youtube.com/watch?v=EzNebqkw13w

## Donations
If you would like to support this project, please consider [sponsoring](https://github.com/sponsors/BittyTax) us. You can also donate via [PayPal] or in [bitcoin]. All donations are gratefully received.

Disclosure: All donations go to Nano Nano Ltd, the creator and maintainer of this project. Nano Nano Ltd is not a charity, or non-profit organisation.

[version-badge]: https://img.shields.io/pypi/v/BittyTax.svg
[license-badge]: https://img.shields.io/pypi/l/BittyTax.svg
[python-badge]: https://img.shields.io/pypi/pyversions/BittyTax.svg
[downloads-badge]: https://img.shields.io/pypi/dm/bittytax
[github-stars-badge]: https://img.shields.io/github/stars/BittyTax/BittyTax?logo=github&color=yellow
[sponsor-badge]: https://img.shields.io/static/v1?label=sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86
[x-badge]: https://img.shields.io/twitter/follow/bitty_tax
[discord-badge]: https://img.shields.io/discord/581493570112847872?logo=discord&label=&logoColor=white&color=7389D8&labelColor=6A7EC2
[paypal-badge]: https://img.shields.io/badge/donate-grey.svg?logo=PayPal
[bitcoin-badge]: https://img.shields.io/badge/donate-grey.svg?logo=bitcoin
[version]: https://pypi.org/project/BittyTax/
[license]: https://github.com/BittyTax/BittyTax/blob/master/LICENSE
[python]: https://wiki.python.org/moin/BeginnersGuide/Download
[downloads]: https://pypistats.org/packages/bittytax
[github-stars]: https://github.com/BittyTax/BittyTax/stargazers
[sponsor]: https://github.com/sponsors/BittyTax
[x]: https://x.com/intent/follow?screen_name=bitty_tax
[discord]: https://discord.gg/NHE3QFt
[PayPal]: https://www.paypal.com/donate?hosted_button_id=HVBQW8TBEHXLC
[bitcoin]: https://donate.bitty.tax 
