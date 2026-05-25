# bittytax_cache

A standalone command-line tool for inspecting and managing the BittyTax local price cache.

The cache lives at `~/.bittytax/cache/` (or `$BITTYTAX_DATA_DIR/.bittytax/cache/`) and stores historical price data fetched by BittyTax from external datasources such as CoinGecko, CryptoCompare, and CoinPaprika.

## Usage

```
cd tools
python bittytax_cache.py <command> [options]
```

## Commands

| Command | Description |
|---|---|
| [`info`](#info) | Summarise cache contents |
| [`show`](#show) | Display cached prices for a specific pair |
| [`export`](#export) | Export the cache to a JSON file |
| [`import`](#import) | Import a previously exported cache file |
| [`backup`](#backup) | Export the full cache to a dated compressed file |
| [`purge`](#purge) | Remove specific price entries |
| [`trim`](#trim) | Remove entries outside a date window |
| [`verify`](#verify) | Check cache files for structural errors |
| [`refresh-ttl`](#refresh-ttl) | Reset the TTL timestamp on ids/assets files |

---

## Cache structure

Each datasource produces up to three files:

| File | Contents |
|---|---|
| `<DS>.json` | Price cache — historical daily prices per trading pair |
| `<DS>_ids.json` | Asset ID list — maps symbols to datasource-specific IDs |
| `<DS>_assets.json` | Asset list — additional metadata (used by some datasources) |

The ids/assets files carry a `timestamp` field. BittyTax considers them stale after **24 hours** and fetches a fresh copy on the next run. Use [`refresh-ttl`](#refresh-ttl) to extend the timestamp without a network call.

### Asset IDs

Inside the price cache each trading pair may have one or more **asset_id buckets** — one per distinct token that shares the same symbol. For most assets there is only one bucket (e.g. `bitcoin` for `BTC`). Pairs involving tokens with duplicate symbols will have multiple buckets. All commands that touch price data accept an optional `--id` argument to target a specific bucket.

### Entry types

Within each bucket, entries are keyed by `YYYY-MM-DD` date. An entry with `"price": null` is a **no-price** sentinel — it records that the datasource was queried for that date but returned no data. A date absent from the bucket entirely is a **missing** day within the recorded range.

---

## info

Summarise every datasource present in the cache: file sizes, pair counts, date ranges, and ids/assets TTL status.

```
python bittytax_cache.py info [-ds DATASOURCE]
```

| Option | Description |
|---|---|
| `-ds DATASOURCE` | Limit output to a single datasource |

### Output explained

```
Cache directory: C:\Users\Scott\.bittytax\cache

CryptoCompare.json  (9,621,419 bytes)  19 pairs, 33,491 total entries
  BTC/GBP
    btc (Bitcoin)    2014-07-18 → 2026-04-26  (4,001 entries: 272 missing)
  STRD/BTC
    strd (Stride)    2020-11-04 → 2026-04-26  (2,000 entries: 1,352 no-price, 3 missing)

CryptoCompare_ids.json  (1,916,610 bytes)  timestamp: 2026-05-17T22:35:42  [FRESH]  19,551 entries
```

- **no-price** — dates present in the cache but for which no price was available.
- **missing** — calendar days within the recorded date range that have no entry at all.
- **[FRESH] / [EXPIRED by N days]** — TTL status of the ids/assets file.

### Examples

```
# Full summary of all datasources
python bittytax_cache.py info

# Summary for CoinGecko only
python bittytax_cache.py info -ds CoinGecko
```

---

## show

Display the actual cached prices for a specific trading pair.

```
python bittytax_cache.py show PAIR [-ds DATASOURCE] [--id ASSET_ID]
                                   [--from DATE] [--to DATE] [--date DATE]
```

| Option | Description |
|---|---|
| `PAIR` | Trading pair, e.g. `BTC/GBP` or `ETH/BTC` |
| `-ds DATASOURCE` | Limit to a single datasource |
| `--id ASSET_ID` | Show only the named asset_id bucket |
| `--from DATE` | Show entries from this date (inclusive, `YYYY-MM-DD`) |
| `--to DATE` | Show entries up to this date (inclusive, `YYYY-MM-DD`) |
| `--date DATE` | Show entries for a single date (shorthand for `--from` + `--to`) |

### Examples

```
# All sources, all dates
python bittytax_cache.py show BTC/GBP

# A specific date range from one source
python bittytax_cache.py show BTC/GBP -ds CryptoCompare --from 2020-01-01 --to 2020-01-03

# A single date
python bittytax_cache.py show ETH/BTC --date 2024-04-05

# One asset_id bucket for a multi-bucket pair
python bittytax_cache.py show LUNA/BTC --id terra-luna-2
```

### Example output

```
CryptoCompare  BTC/GBP
  btc (Bitcoin)
    2020-01-01  5,429.18
    2020-01-02  5,300.02
    2020-01-03  5,604.27
```

---

## export

Export price data (and optionally ids/assets files) to a JSON file. Filters can be used to export a subset.

```
python bittytax_cache.py export OUTPUT_FILE [-ds DATASOURCE] [--asset SYMBOL]
                                           [--from DATE] [--to DATE] [--compress]
```

| Option | Description |
|---|---|
| `OUTPUT_FILE` | Output filename. Conventionally `.json` or `.json.gz` |
| `-ds DATASOURCE` | Export only this datasource |
| `--asset SYMBOL` | Export only pairs starting with this symbol (e.g. `BTC`) |
| `--from DATE` | Export entries from this date (inclusive, `YYYY-MM-DD`) |
| `--to DATE` | Export entries up to this date (inclusive, `YYYY-MM-DD`) |
| `--compress` | Write gzip-compressed output (appends `.gz` if not already present) |

The export format is **JSON**, preserving the `asset_id` layer so that data can be re-imported accurately. The file always contains a `datasources` section (prices). The `ids` and `assets` sections are included only when the corresponding `_ids.json` or `_assets.json` files exist on disk for the datasources being exported — some datasources have neither. Filtering with `-ds` restricts which datasources are scanned, which indirectly affects whether these sections appear.

> **Note:** If the output file already exists, you will be prompted to confirm before it is overwritten. In non-interactive use (e.g. pipes or scripts) the prompt is skipped and the export is aborted — delete or rename the file first.

> **Note:** Pairs that are still in the legacy format (dates at the top level, no `asset_id` buckets) are **skipped** during export with a warning message. Run `bittytax` (or `bittytax_price`) to look up prices for those assets first — this causes BittyTax to migrate them to the new format automatically.

### Examples

```
# Full uncompressed export
python bittytax_cache.py export my_cache.json

# Compressed export for BTC pairs only
python bittytax_cache.py export btc_cache.json --asset BTC --compress

# One datasource, one year of data
python bittytax_cache.py export coingecko_2024.json -ds CoinGecko --from 2024-01-01 --to 2024-12-31
```

---

## import

Merge a previously exported file back into the local cache.

```
python bittytax_cache.py import INPUT_FILE [--overwrite] [--dry-run]
```

| Option | Description |
|---|---|
| `INPUT_FILE` | JSON or `.json.gz` file produced by `export` or `backup` |
| `--overwrite` | Replace existing entries (default: skip duplicates) |
| `--dry-run` | Preview what would be imported without modifying the cache |

- Price entries are merged one date at a time. Existing entries are skipped unless `--overwrite` is specified.
- Ids/assets files are imported at the whole-file level and skipped if they already exist, unless `--overwrite` is used.
- If an imported ids/assets file has an expired TTL a warning is printed with a suggestion to run [`refresh-ttl`](#refresh-ttl).

### Examples

```
# Dry-run to preview
python bittytax_cache.py import my_cache.json.gz --dry-run

# Merge, skipping existing entries
python bittytax_cache.py import my_cache.json.gz

# Full restore, replacing everything
python bittytax_cache.py import my_cache.json.gz --overwrite
```

---

## backup

Export the entire cache to a dated compressed file in the current directory (or a specified directory).

```
python bittytax_cache.py backup [--dir DIR]
```

| Option | Description |
|---|---|
| `--dir DIR` | Directory to write the backup file (default: current directory) |

The output filename is always `bittytax_cache_YYYY-MM-DD.json.gz`.

This is equivalent to:
```
python bittytax_cache.py export bittytax_cache_YYYY-MM-DD.json.gz --compress
```

### Examples

```
# Backup to current directory
python bittytax_cache.py backup

# Backup to a specific folder
python bittytax_cache.py backup --dir D:\Backups
```

---

## purge

Remove specific price entries from the cache. At least one of `-ds`, `--asset`, or `--pair` must be supplied to prevent accidental deletion of everything.

```
python bittytax_cache.py purge [-ds DATASOURCE] [--asset SYMBOL] [--pair PAIR]
                               [--id ASSET_ID] [--from DATE] [--to DATE] [--dry-run]
```

| Option | Description |
|---|---|
| `-ds DATASOURCE` | Restrict to this datasource |
| `--asset SYMBOL` | Restrict to pairs beginning with this symbol (e.g. `BTC`) |
| `--pair PAIR` | Restrict to this exact pair (e.g. `BTC/GBP`) |
| `--id ASSET_ID` | Restrict to a specific asset_id bucket |
| `--from DATE` | Remove entries from this date (inclusive, `YYYY-MM-DD`) |
| `--to DATE` | Remove entries up to this date (inclusive, `YYYY-MM-DD`) |
| `--dry-run` | Preview what would be removed without modifying the cache |

When `--from` and `--to` are both omitted, **all** entries in the matching scope are removed.

If a pair has multiple asset_id buckets and `--id` is not specified, a notice is printed and all buckets are purged. Use `--id` to target just one.

### Examples

```
# Preview what would be removed for BTC pairs in 2026
python bittytax_cache.py purge --asset BTC --from 2026-01-01 --dry-run

# Remove all CoinGecko prices for ETH/BTC after a specific date
python bittytax_cache.py purge -ds CoinGecko --pair ETH/BTC --from 2026-01-01
```

---

## trim

Remove entries that fall **outside** a desired date window. Useful for switching datasources at a tax year boundary or keeping the cache lean after finalising old years.

```
python bittytax_cache.py trim [-ds DATASOURCE] [--asset SYMBOL]
                              [--before DATE] [--after DATE] [--dry-run]
```

| Option | Description |
|---|---|
| `-ds DATASOURCE` | Restrict to this datasource |
| `--asset SYMBOL` | Restrict to pairs beginning with this symbol |
| `--before DATE` | Remove entries **strictly before** this date (`YYYY-MM-DD`) |
| `--after DATE` | Remove entries **strictly after** this date (`YYYY-MM-DD`) |
| `--dry-run` | Preview what would be removed without modifying the cache |

At least one of `--before` or `--after` is required.

Both options can be combined to keep only a specific window, e.g. keep only 2024:
```
python bittytax_cache.py trim --after 2024-12-31 --before 2024-01-01
```

### Examples

```
# Remove all CoinGecko data from 2026 onwards (to re-fetch from a different source)
python bittytax_cache.py trim -ds CoinGecko --after 2025-12-31 --dry-run
python bittytax_cache.py trim -ds CoinGecko --after 2025-12-31

# Remove data outside a single tax year for one asset
python bittytax_cache.py trim --asset BTC --before 2024-04-06 --after 2025-04-05
```

---

## verify

Scan cache files for JSON parse errors and structural problems such as missing keys or unexpected data formats. Useful after manual edits or if BittyTax behaves unexpectedly.

```
python bittytax_cache.py verify [-ds DATASOURCE]
```

| Option | Description |
|---|---|
| `-ds DATASOURCE` | Restrict to this datasource |

Checks performed:
- Each file parses as valid JSON with a dict root.
- Price entries are keyed by valid `YYYY-MM-DD` dates and each entry contains a `price` key.
- Ids/assets files contain `timestamp` and the expected `ids`/`assets` key.

### Examples

```
# Verify all cache files
python bittytax_cache.py verify

# Verify only CoinGecko files
python bittytax_cache.py verify -ds CoinGecko
```

---

## refresh-ttl

Reset the `timestamp` field in ids/assets files to the current time, making them appear fresh to BittyTax. This avoids an unnecessary network refetch after a restore or when operating without internet access.

```
python bittytax_cache.py refresh-ttl [-ds DATASOURCE]
```

| Option | Description |
|---|---|
| `-ds DATASOURCE` | Restrict to this datasource |

### Examples

```
# Refresh all ids/assets files
python bittytax_cache.py refresh-ttl

# Refresh only CoinGecko
python bittytax_cache.py refresh-ttl -ds CoinGecko
```

---

## Common workflows

### Inspect what is cached
```
python bittytax_cache.py info
```

### Look at a suspicious price
```
python bittytax_cache.py show ETH/BTC -ds CoinGecko --from 2024-03-14 --to 2024-03-16
```

### Remove one bad price so BittyTax re-fetches it
```
python bittytax_cache.py purge -ds CoinGecko --pair ETH/BTC --from 2024-03-15 --to 2024-03-15
```

### Switch datasource from tax year start
Remove all CryptoCompare data on or after 6 April 2026, so the next run fetches from a different source:
```
python bittytax_cache.py trim -ds CryptoCompare --after 2026-04-05 --dry-run
python bittytax_cache.py trim -ds CryptoCompare --after 2026-04-05
```

### Back up before a major change
```
python bittytax_cache.py backup --dir D:\Backups
```

### Restore a backup on a new machine
```
bittytax_cache import bittytax_cache_2026-05-17.json.gz
bittytax_cache refresh-ttl
```
