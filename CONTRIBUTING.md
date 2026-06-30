# Contributing to BittyTax

Thank you for your interest in contributing to BittyTax! This guide covers how to report bugs, request new parsers, suggest features, and submit code changes.

---

## Need Help?

**Please do not open a GitHub issue just to ask a question.** Issues are for confirmed bugs, parser problems, and feature requests — not general support.

If you need help, use one of these instead:

- **[Discord](https://discord.com/invite/NHE3QFt)** — best for quick questions and real-time help
- **[GitHub Discussions](https://github.com/BittyTax/BittyTax/discussions)** — for longer questions, configuration help, or anything you're not sure about

---

## Before You Open an Issue

**First, [search open issues](https://github.com/BittyTax/BittyTax/issues) to check your problem hasn't already been reported.** Your issue may already be tracked or have a workaround in the comments.

Many issues are also caused by known mistakes. Please check the relevant section below before opening a new one — you may find an immediate answer.

### Parser / Unrecognised File

- **Check which file formats are supported.** Run `bittytax_conv --help` to see the full list of supported exchanges, wallets, etc, and the exact header formats expected for each.
- **Do not open and save CSV files in Excel before running the converter.** If you open a CSV in Excel and save it, Excel can reformat dates, truncate decimal values, and alter other data, causing the file to be unrecognised or parsed incorrectly. Always use the original downloaded file.
- **Check for an existing open issue for your exchange.** Exchanges regularly change their export formats. Search [open issues](https://github.com/BittyTax/BittyTax/issues) for your exchange name — there may already be a fix in progress.

### Price Lookup Failures

- **CryptoCompare free API has been discontinued.** If you see HTTP 401 errors, CryptoCompare is no longer available without a paid API key. Configure an alternative data source in your `bittytax.conf`. See [discussion #497](https://github.com/BittyTax/BittyTax/discussions/497).
- **Historic data older than 12 months may fail.** Free tiers of CoinGecko and CoinPaprika limit historical price lookups. Prices already in your local cache will still be used.
- **Same ticker symbol, different token.** If you hold a token whose symbol conflicts with a more well-known asset (e.g. `STRK`, `EDG`), you may be getting prices for the wrong token. Use the `data_source_select` config option to pin the correct asset ID for that symbol.

### Integrity Check Failures

The warning `Integrity check failed: audit does not match section 104 pools` is almost always caused by one of the following:

- **Wrong quantity for Withdrawal.** The `Withdrawal` quantity must be the **net** amount received — i.e. after any fee has been deducted. The fee must be specified separately in the fee fields.
- **Missing matching Deposit.** Every `Withdrawal` from one wallet should have a corresponding `Deposit` in another. Some exchanges only export trades, not transfers — these must be added manually.
- **`Deposit`/`Withdrawal` used for third-party transfers.** These transaction types are only for moving assets **between your own wallets**. Sending to someone else should be `Gift-Sent`, `Spend`, or `Charity-Sent`.
- **On-chain network fees.** The amount deposited on-chain is often less than the amount withdrawn, due to network fees deducted by the blockchain. The `Deposit` quantity should reflect the amount actually received.

### Installation Problems

- **`pycairo` build failure.** See the [Installation](https://github.com/BittyTax/BittyTax/wiki/Installation) wiki page for the svglib workaround.
- **Ubuntu 24.04 or newer.** Use `pipx install bittytax` instead of `pip install bittytax`.
- **`ImportError: attempted relative import`.** You are running a source file directly. Use the installed CLI commands (`bittytax_conv`, `bittytax`, `bittytax_price`) instead.
- **`pip` vs `pipx` confusion.** See the [Installation](https://github.com/BittyTax/BittyTax/wiki/Installation) wiki page.

### Transaction Type Misunderstandings

- **`Staking` is deprecated.** Use `Staking-Reward` instead.
- **`Deposit`/`Withdrawal` vs `Gift-Sent`/`Spend`.** `Deposit` and `Withdrawal` are only for transfers between your own wallets.
- **Deposit quantity is gross; Withdrawal quantity is net.** `Deposit` = amount received (before any platform fee), `Withdrawal` = amount sent minus fee.

---

## Reporting a Bug

Before reporting, please:

1. Upgrade to the latest version of BittyTax — or better yet, the [latest unreleased version from GitHub](https://github.com/BittyTax/BittyTax/wiki/Installation#installing-unreleased-version-from-github) — and check whether the bug still exists.
2. Search [existing issues](https://github.com/BittyTax/BittyTax/issues) to avoid duplicates.

Use the **Bug Report** issue template when opening a new issue. It will prompt you for the information needed to diagnose the problem. If the command produced an error or exception, include the full error message in the issue.

**Privacy:** If you attach a sample CSV, please anonymise it — remove or replace real wallet addresses, transaction IDs, and any personal data before posting. If your file contains data you cannot anonymise, you can email a sample privately to [bittytax@nanonano.co.uk](mailto:bittytax@nanonano.co.uk) — please include your issue number so it can be linked. Do not email for general support questions.

---

## Requesting a New or Updated Parser

If your exchange, wallet, explorer, etc. has changed its CSV export format, or you need support for one that is not yet covered:

1. Check [open issues](https://github.com/BittyTax/BittyTax/issues) first — someone else may have already reported it.
2. Use the **Parser Request** issue template.
3. Include a sample of the new CSV format (header row + a few anonymised data rows) — this is essential for implementing or fixing the parser without requiring an account.
4. Include a link to the export documentation if available.

---

## Feature Requests

For small, well-defined improvements, open an issue using the **Feature Request** template.

For larger ideas or changes that affect tax calculations, please start a [GitHub Discussion](https://github.com/BittyTax/BittyTax/discussions) first so the approach can be agreed before any code is written.

---

## Pull Requests

> **Always raise an issue before submitting a pull request.** Unsolicited PRs without a linked issue will be closed.

### Rules

- **One issue, one PR.** Do not bundle multiple fixes or features into a single PR — each PR must address exactly one issue.
- **Reference the issue.** Include `Closes #123` in your PR description so the issue is automatically closed on merge.
- **No unrelated changes.** Do not fix whitespace, rename variables, reformat code, or refactor anything outside the direct scope of the issue.
- **Python 3.7+ compatibility required.** Do not use language features introduced after Python 3.7 (e.g. walrus operator `:=`, `match` statements, f-string `=` specifier).
- **All CI checks must pass.** See the [Development](https://github.com/BittyTax/BittyTax/wiki/Development) wiki page for the full list of tools and commands to run locally before submitting.
- **Type annotations are required.** All new code must be fully typed — mypy runs in strict mode.
- **Spell check must pass.** New crypto or technical terms that trigger the spell checker should be added to `.pylint_dictionary`.
- **Update `CHANGELOG.md`.** Add an entry under `## [Unreleased]` in the appropriate subsection (`### Fixed`, `### Added`, or `### Changed`), following the existing format:
  ```
  - {Exchange} parser: description. ([#{issue}](https://github.com/BittyTax/BittyTax/issues/{issue}))
  - {Tool}: description. ([#{issue}](https://github.com/BittyTax/BittyTax/issues/{issue}))
  ```
- **Don't force-push after a review has started.** It makes it very difficult to track what changed between reviews. Push new commits instead.
- **Draft PRs are welcome.** If you want early feedback before your PR is ready, open it as a Draft.

### Parser PRs

- **Backward compatibility is required.** If an exchange has changed or added columns to their export, add a **new `DataParser` object** pointing to the same handler function. Never modify the `header` list of an existing `DataParser` — old export formats must continue to work.
- **Manual testing is required.** Before submitting, verify your parser output is correct by running the converter and piping the output through the accounting tool's audit:
  ```
  bittytax_conv --format CSV sample.csv | bittytax --audit --nopdf
  ```
  The audit produces final balances for each asset which you can manually verify against the exchange or wallet. This assumes you have parsed your complete transaction history.
- **Automated tests are optional** but appreciated. See the [Development](https://github.com/BittyTax/BittyTax/wiki/Development) wiki page for the test structure.
- **Include an anonymised sample CSV** in the PR description or as a comment, so the output can be verified without requiring an exchange account.

### Licence

By submitting a pull request, you agree that your contribution will be licensed under the [AGPLv3 licence](LICENSE) that covers this project.
