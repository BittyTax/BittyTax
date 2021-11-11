# Change Log
## [Unreleased]

## Version [0.5.0] Beta (2021-11-11)
Important:-

1. A new Note field has been added to the end of the transaction record format (column M), this is used to add a description to a transaction. It is recommended that you add the additional Note column to all your existing transaction records.

2. The `Charity-Sent` transaction type has been changed from a normal disposal (same as a `Gift-Sent`) to being a "*No Gain/No Loss*" disposal, the same as a `Gift-Spouse`. If you have used this transaction type previously we recommend you re-generate your tax reports as you may have overpaid capital gains tax.

3. The ExchangeRatesAPI and RatesAPI data sources are no longer available. Please update your `bittytax.conf` file to use the new BittyTaxAPI as shown below, this file resides in your .bittytax folder within your home directory.

```
data_source_fiat:
    ['BittyTaxAPI']
```

### Fixed
- Accounting tool: "xlrd.biffh.XLRDError: Excel xlsx file; not supported" Exception. ([#36](https://github.com/BittyTax/BittyTax/issues/36))
- Coinbase parser: added support for Convert transactions. ([#46](https://github.com/BittyTax/BittyTax/issues/46))
- Coinbase parser: mis-classifying trade as gift-received. ([#47](https://github.com/BittyTax/BittyTax/issues/47))
- Accounting tool: unexpected treatment of withdrawal fees (transfers_include=False). ([#56](https://github.com/BittyTax/BittyTax/issues/56))
- Accounting tool: assets which only have matched disposals are not shown in holdings report. ([#60](https://github.com/BittyTax/BittyTax/issues/60))
- Coinbase Pro parser: fills export, buy quantity missing fee.
- Price tool: list command returns error. ([#86](https://github.com/BittyTax/BittyTax/issues/86))
- Price tool: -ds option returns "KeyError: 'price'" exception.
- Conversion tool: strip whitespace from header.
- Accounting tool: Charity-Sent should be a "No Gain/No Loss" disposal. ([#77](https://github.com/BittyTax/BittyTax/issues/77))
- Accounting tool: The "ten day" rule for companies, should match the buy to sell, not sell to buy-back. ([#131](https://github.com/BittyTax/BittyTax/issues/131))
- Kraken parser: Trading pair split broken for XTZ/GBP. ([#124](https://github.com/BittyTax/BittyTax/issues/124))
- Binance parser: Removed "Unexpected Coin content" error. ([#132](https://github.com/BittyTax/BittyTax/issues/132)) 
- Trezor parser: Timestamp is GMT+1.
- Etherscan parser: "Sell Quantity" should be zero for failed withdrawals.
- BscScan parser: "Sell Quantity" should be zero for failed withdrawals.
- HecoInfo parser: "Sell Quantity" should be zero for failed withdrawals.
- Nexo parser: Timestamp is CET. ([#188](https://github.com/BittyTax/BittyTax/issues/188))
### Added
- Etherscan parser: added internal transactions export.
- Binance parser: added cash deposit and withdrawal exports.
- Binance parser: added statements export.
- Bitfinex parser: new "Trades" data file format added. ([#41](https://github.com/BittyTax/BittyTax/issues/41))
- Bittrex parser: new deposits data file format added.
- Coinbase parser: new config "coinbase_zero_fees_are_gifts" added.
- Accounting/Conversion tool: support for milli/microsecond timestamps.
- Accounting tool: export option for transaction records with prices.
- Price/Accounting tool: support for duplicate symbol names. ([#34](https://github.com/BittyTax/BittyTax/issues/34))
- Price tool: search option (-s) added to list command.
- Price tool: data source (-ds) option added to list command.
- Accounting tool: config for allowable cost attribution.
- Accounting tool: integrity check (disposals between transfers).
- Accounting tool: warning given if disposal detected between transfers.
- Accounting tool: integrity check (audit balances against section 104 pools).
- Accounting tool: skip integrity check (--skipint) option added.
- Accounting tool: new Note field added to transaction record format.
- Accounting tool: note field added to income report.
- Conversion tool: note field added to the Excel and CSV output.
- Accounting tool: new config "transfer_fee_disposal" added (transfers_include=False). ([#56](https://github.com/BittyTax/BittyTax/issues/56))
- Accounting tool: Excel files with worksheet names prefixed with '--' are ignored by the import.
- Accounting tool: tax rates and allowance for 2021/22.
- Accounting tool: tax rules for UK companies.
- Accounting tool: tax rules option (--taxrules) added.
- Local currency support.
- Accounting tool: new config "transfer_fee_allowable_cost" added.
- Conversion tool: allow wildcards in filenames.
- Conversion tool: added dictionary to DataRow.
- Conversion tool: "Savings & Loans" parser category added.
- Conversion tool: convert_currency method added to DataParser.
- Conversion tool: added parser for BlockFi.
- Conversion tool: added parser for Celsius.
- Conversion tool: added parser for Coinomi wallet.
- Conversion tool: added parser for Blockchain.com wallet.
- Conversion tool: convert multiple Excel worksheets.
- KuCoin parser: added new trade history exports.
- KuCoin parser: added deposit/withdrawal exports.
- HitBTC parser: added new trade history export.
- Electrum parser: new data file format added.
- Accounting tool: added dictionary to TransactionRow.
- New data source "Frankfurter" added for fiat exchange rates.
- Ledger Live parser: new data file format added.
- New data source "BittyTaxAPI" added for fiat exchange rates.
- Coinfloor parser: new "trades" data file format added.
- Gravity parser: new data file format added.
- Etherscan parser: new "Transactions" data file format added.
- Conversion tool: added parser for BscScan explorer.
- Conversion tool: specify the local currency of the "Value" headers.
- Conversion tool: added parser for Exodus wallet.
- Conversion tool: added parser for Zerion explorer.
- Conversion tool: added parser for Helium wallet and explorer.
- Conversion tool: added parser for Accointing accounting data.
- Bitfinex parser: new "movements" data file format added.
- Accounting tool: new transaction types Lost and Airdrop added.
- Binance parser: added trades statement export format.
- Conversion tool: added parser for HecoInfo explorer.
- Conversion tool: added parser for Trezor Suite.
- Binance parser: added new statement export format.
- Nexo parser: added new export format.
- Conversion tool: added merge parser for Etherscan.
- Conversion tool: added merge parser for BscScan.
- Conversion tool: added merge parser for HecoInfo.
- BscScan parser: new "Transactions" data file format added.
- HecoInfo parser: new "Transactions" data file format added.
- KuCoin parser: added new trade history export.
- Coinbase parser: new "Transaction history" data file format added.
### Changed
- Conversion tool: UnknownAddressError exception changed to generic DataFilenameError.
- Binance parser: use filename to determine if deposits or withdrawals.
- Binance parser: updated quote assets via new script.
- Crypto.com parser: added new "Supercharger" transaction types. ([#38](https://github.com/BittyTax/BittyTax/issues/38))
- Coinbase parser: added Coinbase Earn/Rewards Income transactions.
- Coinbase parser: get value (from spot price) where possible.
- Bittrex parser: added market buy/sell transactions.
- Ledger Live parser: fees now optional, as missing from ERC-20 wallets.
- Bitstamp parser: fees now optional.
- Accounting tool: same day pooling debug now only shows the pooled transactions.
- Accounting tool: section 104 debug also shows matched transactions.
- Crypto.com parser: added "campaign_reward" transaction type. ([#64](https://github.com/BittyTax/BittyTax/issues/64))
- Elecrum parser: Note field is mapped from 'label'.
- HandCash parser: Note field is mapped from 'note'.
- Qt Wallet parser: Note field is mapped from 'Label'.
- Trezor parser: Note field is mapped from 'Address Label'.
- Accounting tool: get value for fee if matching buy/sell asset has zero quantity or no price.
- Accounting tool: don't drop zero quantity buy/sell if fee value present.
- Accounting tool: ordering of all transactions when transfers_include=False.
- Ledger Live parser: added "FEES" and "REVEAL" operation types. ([#79](https://github.com/BittyTax/BittyTax/issues/79))
- Binance parser: added "Referrer rebates" operation type.
- Command line arguments now used locally instead of stored globally.
- Price tool: PriceData requires data source list to initialise.
- Conversion tool: all parsers updated to use DataRow dictionary.
- Crypto.com parser: added "crypto_to_van_sell_order" transaction type.
- Nexo parser: check for unconfirmed transactions.
- Qt Wallet parser: added "Masternode Reward" type.
- Qt Wallet parser: added support for VeriCoin-Qt wallet.
- Bittrex parser: filter unauthorised/cancelled withdrawals. ([#108](https://github.com/BittyTax/BittyTax/issues/108))
- Coinbase parser: added EUR and USD accounts.
- Conversion tool: refactored parsers to use kwargs.
- Conversion tool: better error handling for IOError.
- Increase data source API timeout to 30 seconds.
- Accounting tool: use fixed value (when specified) for counter asset prices.
- Accounting tool: don't store fixed value for transfers.
- Accounting tool: refactored import_records.py to use dictionary.
- Binance parser: added "POS savings interest" and "Savings Interest" operations. ([#137](https://github.com/BittyTax/BittyTax/issues/137))
- Binance parser: added "Super BNB Mining" operation.
- Crypto.com parser: added "supercharger_reward_to_app_credited" transaction type.
- Crypto.com parser: improved 'Native Amount' handling.
- Crypto.com parser: added "council_node_deposit_created" transaction type.
- Etherscan parser: add "Method" as a note.
- BscScan parser: add "Method" as a note.
- HecoInfo parser: add "Method" as a note.
- Config: transfers_include to False.
- Config: transfer_fee_allowable_cost to True.
### Removed
- Accounting tool: skip audit (-s or --skipaudit) option removed.
- Accounting tool: updated transactions debug removed.
- Config: ExchangeRatesAPI removed. ([#102](https://github.com/BittyTax/BittyTax/issues/102))

## Version [0.4.3] Beta (2020-12-04)
Important:- if upgrading, please remove your price data cache file for CryptoCompare: `~/.bittytax/cache/CryptoCompare.json` (see Issue [#29](https://github.com/BittyTax/BittyTax/issues/29))
### Fixed
- UserWarning: Must have at least one data row in in add_table().
- AttributeError: 'module' object has no attribute 'UTC'. ([#27](https://github.com/BittyTax/BittyTax/issues/27))
- Crypto.com parser: fix date parser.
- Incorrect price data for stablecoins via CryptoCompare. ([#29](https://github.com/BittyTax/BittyTax/issues/29))
### Added
- Conversion tool: added parser for CGTCalculator.
- Conversion tool: added parser for Nexo.
- Conversion tool: added parser for Kraken.
- HitBTC parser: new data file format added.
### Changed
- Hotbit parser: Negative fees are now set to zero.
- Accounting tool: Drop buy/sell/fee transactions of zero quantity.
- Crypto.com parser: Add support for referral_gift transaction type.

## Version [0.4.2] Beta (2020-10-30)
### Fixed
- Cell conversion of imported Excel data safer for python 2.
- Circle parser: filter out other currency symbols '£€$'.
- Cryptsy parser: sell/buy quantities already had fee included.
- Cryptopia parser: calculations rounded to 8 decimal places.
- Tqdm workaround (https://github.com/tqdm/tqdm/issues/777).
- Ledger Live parser: unrecognised operation type 'IN'.
- TradeSatoshi parser: calculations rounded to 8 decimal places.
- Trezor parser: "self" payment exception.
- Electrum parser: timestamp is in local time.
- KeyError: 'bpi' exception. ([#21](https://github.com/BittyTax/BittyTax/issues/21))
- Python 3.x compatibility. ([#20](https://github.com/BittyTax/BittyTax/issues/20))
- Conversion tool: Python 2, UnicodeDecodeError exception.
### Added
- Conversion tool: added parser for CoinTracking.info accounting data.
- Conversion tool: added parser for Gravity (Bitstocks) exchange.
- Etherscan parser: added ERC-20 tokens and ERC-721 NFTs exports.
- Bittrex parser: new data file format added.
- Coinbase Pro parser: new "Account Statement" data file format added.
- Coinbase parser: new "Transaction history" data file format added.
- Coinfloor parser: new "Deposit and Withdrawal" data file format added.
- Ledger Live parser: new data file format added.
- GateHub parser: new data file format added.
- Trezor parser: try and get symbol name from filename.
- Electrum parser: new data file format added (ElectrumSV).
- Conversion tool: added parser for Hotbit exchange.
- Conversion tool: added parser for Liquid exchange.
- Conversion tool: added parser for Energy Web explorer.
- Qt Wallet parser: recognise Namecoin operations.
- Qt Wallet parser: warning when skipping unconfirmed transactions.
- Conversion tool: added extra debug.
- Uphold parser: new data file format added.
- Poloniex parser: new "trades" data file format added.
- Poloniex parser: new "distributions" data file format added.
- Conversion tool: added colour bands to Excel output file.
- Binance parser: new "deposit" and "withdrawal" data file formats added.
- Accounting tool: new transaction types added (Staking, Interest, Dividend).
- Conversion tool: added parser for Crypto.com app.
- Accounting tool: added disclaimer to footer of PDF.
- Accounting tool: validate tax year argument.
- Price tool: added data source (-ds) argument.
- Accounting tool: new transaction type Gift-Spouse added.
- Coinbase Pro parser: new "Fills Statement" data file format added.
- Price tool: added list asset command.
### Changed
- Sort wallet names in audit debug as case-insensitive.
- Data source names in config are now case-insensitive.
- Accounting/Price tool: display error message if data source name unrecognised.
- Price tool: display error message if date is invalid.
- Conversion tool: set default font size in Excel workbook.
- Accounting/Price tool: don't display warning if the price data cache file does not exist.
- Qt Wallet parser: "payment to yourself" becomes withdrawal with just fee.
- HandCash parser: identify transactions to other users as gifts.
- Qt Wallet parser: get symbol name from "Amount" if available.
- Qt Wallet parser: -ca option takes precedence over any symbol name found in the data file.
- Conversion tool: Excel currency format changed to improve compatibility.
- Price tool: added commands for latest and historic prices.
- Price tool: quantity is now an optional argument, -q or --quantity is not required.

## Version [0.4.1] Beta (2020-07-25)
### Fixed
- Prevent a division by zero when calculating the fee proceeds.
- Exception UnboundLocalError: local variable 'url' referenced before assignment.
- Tax year end was excluding 5th April.
### Added
- Conversion tool: added parser for Interactive Investor stocks and shares.
### Changed
- Conversion tool: colour highlight element in row for parser failures.
- Accounting tool: colour highlight element in row for import failures.

## Version [0.4.0] Beta (2020-07-18)
### Added
- Accounting tool: colour output and progress bars/spinner.
- Conversion tool: colour output.
- Price tool: colour output.
### Changed
- Accounting tool: use latest price when a historic price is not available.

## Version [0.3.3] Beta (2020-06-29)
### Fixed
- Exception if transaction records input file contains less than the expected 12 columns. ([#5](https://github.com/BittyTax/BittyTax/issues/5))
- Historic or fixed fee indicator is incorrect when transaction is pooled. ([#7](https://github.com/BittyTax/BittyTax/issues/7))
- Tax-free allowance for 2021 missing. ([#13](https://github.com/BittyTax/BittyTax/issues/13))
- Circle Parser: added "fork" transaction type. ([#11](https://github.com/BittyTax/BittyTax/issues/11))
- Trezor Parser: wallets without labelling. ([#10](https://github.com/BittyTax/BittyTax/issues/10))
- Bitfinex Parser: calculations rounded to 8 decimal places. ([#14](https://github.com/BittyTax/BittyTax/issues/14))
- Conversion tool: python 2 raised exception if file format was unrecognised or file missing. ([#9](https://github.com/BittyTax/BittyTax/issues/9))
- Accounting tool: handle exception if input file is missing. ([#15](https://github.com/BittyTax/BittyTax/issues/15))
- Accounting tool: python 2 handle utf-8 characters in Excel file.
### Added
- Conversion tool: added parser for HandCash wallet.
### Changed
- Trezor Parser: fees are now included separately.

## Version [0.3.2] Beta (2020-04-11)
### Fixed
- Missing packages in setup.py.

## Version [0.3.0] Beta (2020-04-11)
### Fixed
- Proceeds 4x warning was missing from PDF.
### Added
- Conversion tool: Improved exception handling.
- Accounting tool: Identify if asset values are fixed or from historic price data.
- Accounting tool: PDF report output.
### Changed
- Accounting tool: Timestamps normalised to local time only for Buy/Sell transactions.
- Accounting tool: Made fees optional for Buy/Sell transactions.

## Version [0.2.1] Beta (2020-03-07)
### Fixed
- Tax summary: Gains in the year should exclude losses.
- Bittrex parser: Adjust quantity for partially filled orders.
### Added
- HitBTC exchange data files.
- KuCoin trades data file.
- Improved fee handling, including 3rd asset fees.
### Changed
- Conversion tool: Changed Excel spreadsheet style and added file properties.

## Version [0.2.0] Beta (2019-10-30)
### Fixed
- Bitfinex parser: wallet name typo.
- Conversion tool: use repr when parsing numbers in excel files to ensure no precision is lost.
- Coinbase: updated with new TransactionsReport header.
- Gatehub parser: exchange transactions with missing component incorrectly handled when --append option used.
### Added
- Audit: output transaction record in debug.
- Bittrex: new data file format for deposits and withdrawals added.
- Conversion tool: Support for Excel as output file format.
- Conversion tool: New --duplicates argument added to remove duplicate input rows across data files.
- Conversion tool: New -o argument added to specify an output filename for Excel or CSV files
- Accounting tool: Importing transaction records from an Excel file.
### Changed
- Remove trailing zeros from CSV output and other places in logging.
- TID's (Transaction ID) are now allocated in time order sequence.

## Version [0.1.4] Beta (2019-08-28)
### Fixed
- Audit function failure due to missing sort methods.
- More robust error handling for data source historic prices.
- Poloniex Withdrawals parser failure.
- Setup.py failing for Windows.
- Set encoding of stdout/sdterr to be utf-8.
- Re-raising exception failure in Python 3.
### Changed
- Conversion tool: The append option now appends the original data as extra columns in the CSV output.

## Version [0.1.3] Beta (2019-08-14)
### Fixed
- Bitstamp parser: added missing type 'Ripple deposit'.
- Coinbase Pro parser: filter "fee" transactions.
- Validate symbol is not missing for latest price response from data source.
- Poloniex parser: workaround to fix rounding issues found in recent trading history exports.
- Data parser: only match headers which are of the same number of fields.
### Added
- Bittrex: new data file format for trades added.
- TradeSatoshi: new data file format for deposits and withdrawals added.
- Conversion tool can now support data files with different CSV delimiters.
- Conversion tool has debug option.
- Conversion tool raises warning if 15-digit precision exceeded (Excel limit).
- Conversion tool: added option to output in Recap import CSV format.
### Removed
- Negative balance warning in a Section 104 holding.
- Logging removed from within config module.
### Changed
- Logging is now initialised by each tool, instead of within the `config.py` module.
- Conversion tool now outputs logging to `stderr` so it will be filtered when piping into `bittytax`.
- The `pricedata.py` module has been renamed `valueasset.py`, and main function moved to new `price.py` module.
- Package layout restructured, added subfolders for price and conv tools.
- Refactored code for "all_handler" data parsers.

## Version [0.1.2] Beta (2019-06-30)
### Fixed
- Fix for 'get_average_cost' exception when debug enabled.
- Same-day buy pools should the use the timestamp of earliest transaction, not the latest, this prevents the possibility of a negative balance.
- Circle parser: added missing transaction types, 'internal_switch_currency' and 'switch_currency'.
### Added
- Exchange data files: Wirex, Binance.
- Poloniex parser: added new withdrawalHistory.csv data format.
- Bitfinex exchange data files.

## Version [0.1.1] Beta (2019-05-29)
### Fixed
- Default bittytax.conf file was not being created when BittyTax was installed from a package, config file is now created at runtime if one does not already exist.

## Version [0.1.0] Beta (2019-05-23)
This is the initial beta release. Although it has been throughly tested, it's possible that your specific wallet/exchange data file contains data which was not programmed for. Please raise an issue if you find any problems.
### Added
- Command line tools for cryptoasset accounting, auditing and UK tax calculations (Capital Gains/Income Tax).
- Wallet data files supported: Electrum, Ledger Live, Qt Wallet, Trezor.
- Exchange data files supported: Bitstamp, Bittrex, ChangeTip, Circle, Coinbase, Coinbase Pro, Coinfloor, Cryptopia, Cryptsy, Gatehub, OKEx, Poloniex, TradeSatoshi, Uphold.
- Explorer data files supported: Etherscan.

[Unreleased]: https://github.com/BittyTax/BittyTax/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/BittyTax/BittyTax/compare/v0.4.3...v0.5.0
[0.4.3]: https://github.com/BittyTax/BittyTax/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/BittyTax/BittyTax/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/BittyTax/BittyTax/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/BittyTax/BittyTax/compare/v0.3.3...v0.4.0
[0.3.3]: https://github.com/BittyTax/BittyTax/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/BittyTax/BittyTax/compare/v0.3.0...v0.3.2
[0.3.0]: https://github.com/BittyTax/BittyTax/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/BittyTax/BittyTax/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/BittyTax/BittyTax/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/BittyTax/BittyTax/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/BittyTax/BittyTax/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/BittyTax/BittyTax/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/BittyTax/BittyTax/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/BittyTax/BittyTax/releases/tag/v0.1.0
