# -*- coding: utf-8 -*-
# Standalone BittyTax cache management tool
# (c) Nano Nano Ltd 2026

import argparse
import gzip
import json
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

from bittytax.constants import CACHE_DIR
from bittytax.price.datasource import DataSourceBase
from bittytax.version import __version__

IDS_TTL: timedelta = DataSourceBase.IDS_TTL

# ---------------------------------------------------------------------------
# Helpers: detect known data-source names from cache filenames
# ---------------------------------------------------------------------------


def _ds_names_in_cache(ds_filter: Optional[str] = None) -> List[str]:
    """Return sorted list of data-source names present in the cache directory."""
    if not os.path.isdir(CACHE_DIR):
        return []
    names: set[str] = set()
    for fname in os.listdir(CACHE_DIR):
        if fname.endswith(".json"):
            stem = fname[:-5]
            if stem.endswith("_ids"):
                names.add(stem[:-4])
            elif stem.endswith("_assets"):
                names.add(stem[:-7])
            else:
                names.add(stem)
    if ds_filter:
        names = {n for n in names if n.lower() == ds_filter.lower()}
    return sorted(names)


# ---------------------------------------------------------------------------
# Helpers: price-cache JSON format (new and legacy)
# ---------------------------------------------------------------------------


def _is_date_key(key: str) -> bool:
    """Quick check for ISO date format YYYY-MM-DD."""
    return len(key) == 10 and key[4] == "-" and key[7] == "-"


def _iter_asset_entries(pair_data: dict) -> List[Tuple[str, str, dict]]:
    """
    Yield (asset_id, name, prices_dict) for each asset bucket in a pair entry.
    Handles both legacy format {YYYY-MM-DD: {price, url}} and new format
    {asset_id: {name, prices: {YYYY-MM-DD: {price, url}}}}.
    """
    if not pair_data:
        return []
    first_key = next(iter(pair_data))
    if _is_date_key(first_key):
        return [("", "", pair_data)]
    results = []
    for asset_id, asset_entry in pair_data.items():
        name = asset_entry.get("name", "")
        prices = asset_entry.get("prices", {})
        results.append((asset_id, name, prices))
    return results


def _count_stats(
    prices_dict: dict,
) -> Tuple[int, int, int, int, Optional[str], Optional[str]]:
    """
    Return (total_entries, priced, no_price, missing, min_date_str, max_date_str).
    'missing' = calendar days absent within [min_date, max_date].
    """
    dates_present = set(prices_dict.keys())
    if not dates_present:
        return 0, 0, 0, 0, None, None

    min_d = min(dates_present)
    max_d = max(dates_present)

    priced = sum(1 for v in prices_dict.values() if v.get("price") is not None)
    no_price = len(prices_dict) - priced

    try:
        d_min = datetime.strptime(min_d, "%Y-%m-%d").date()
        d_max = datetime.strptime(max_d, "%Y-%m-%d").date()
        total_days = (d_max - d_min).days + 1
        missing = total_days - len(dates_present)
    except ValueError:
        missing = 0

    return len(dates_present), priced, no_price, missing, min_d, max_d


def _load_raw_cache(ds_name: str) -> dict:
    filename = os.path.join(CACHE_DIR, ds_name + ".json")
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, ValueError):
        print(f"WARNING Could not load {filename}", file=sys.stderr)
        return {}


def _save_raw_cache(ds_name: str, data: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    filename = os.path.join(CACHE_DIR, ds_name + ".json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, sort_keys=True)


def _load_raw_ids(ds_name: str) -> dict:
    filename = os.path.join(CACHE_DIR, ds_name + "_ids.json")
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, ValueError):
        return {}


def _load_raw_assets(ds_name: str) -> dict:
    filename = os.path.join(CACHE_DIR, ds_name + "_assets.json")
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, ValueError):
        return {}


def _ttl_status(timestamp_str: str) -> str:
    try:
        ts = datetime.fromisoformat(timestamp_str)
        age = datetime.now() - ts
        if age <= IDS_TTL:
            return "[FRESH]"
        overdue = age - IDS_TTL
        days = overdue.days
        return f"[EXPIRED by {days} day{'s' if days != 1 else ''}]"
    except ValueError:
        return "[UNKNOWN]"


def _parse_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"date must be YYYY-MM-DD, got: {value!r}") from e


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_info(args: argparse.Namespace) -> None:  # pylint: disable=too-many-locals
    ds_filter: Optional[str] = args.ds if hasattr(args, "ds") else None
    ds_names = _ds_names_in_cache(ds_filter)

    if not ds_names:
        print(f"Cache directory: {CACHE_DIR}")
        print("No cache files found.")
        return

    print(f"Cache directory: {CACHE_DIR}\n")

    for ds_name in ds_names:
        price_file = os.path.join(CACHE_DIR, ds_name + ".json")
        ids_file = os.path.join(CACHE_DIR, ds_name + "_ids.json")
        assets_file = os.path.join(CACHE_DIR, ds_name + "_assets.json")

        # --- Price cache ---
        if os.path.exists(price_file):
            size = os.path.getsize(price_file)
            raw = _load_raw_cache(ds_name)
            total_entries = 0
            for pair_data in raw.values():
                for _, _, prices_dict in _iter_asset_entries(pair_data):
                    total_entries += len(prices_dict)

            print(
                f"{ds_name}.json  ({size:,} bytes)  "
                f"{len(raw)} pair{'s' if len(raw) != 1 else ''}, "
                f"{total_entries:,} total entries"
            )

            for pair in sorted(raw):
                pair_data = raw[pair]
                entries = _iter_asset_entries(pair_data)
                if not entries:
                    print(f"  {pair}  (empty)")
                    continue
                print(f"  {pair}")
                for asset_id, name, prices_dict in entries:
                    label = asset_id if asset_id else "(legacy)"
                    if name:
                        label = f"{label} ({name})"
                    total, _, no_price, missing, min_d, max_d = _count_stats(prices_dict)
                    if total == 0:
                        print(f"    {label:<50}  (no entries)")
                        continue
                    stats_parts = [f"{total:,} entries"]
                    detail = []
                    if no_price:
                        detail.append(f"{no_price:,} no-price")
                    if missing:
                        detail.append(f"{missing:,} missing")
                    if detail:
                        stats_parts.append(": " + ", ".join(detail))
                    stats_str = "".join(stats_parts)
                    print(f"    {label:<50}  {min_d} \u2192 {max_d}  ({stats_str})")
            print()

        # --- Ids cache ---
        if os.path.exists(ids_file):
            size = os.path.getsize(ids_file)
            raw = _load_raw_ids(ds_name)
            ts = raw.get("timestamp", "unknown")
            count = len(raw.get("ids", {}))
            status = _ttl_status(ts) if ts != "unknown" else "[UNKNOWN]"
            print(
                f"{ds_name}_ids.json  ({size:,} bytes)  "
                f"timestamp: {ts}  {status}  {count:,} entries"
            )

        # --- Assets cache ---
        if os.path.exists(assets_file):
            size = os.path.getsize(assets_file)
            raw = _load_raw_assets(ds_name)
            ts = raw.get("timestamp", "unknown")
            count = len(raw.get("assets", {}))
            status = _ttl_status(ts) if ts != "unknown" else "[UNKNOWN]"
            print(
                f"{ds_name}_assets.json  ({size:,} bytes)  "
                f"timestamp: {ts}  {status}  {count:,} entries"
            )

        if os.path.exists(ids_file) or os.path.exists(assets_file):
            print()


def cmd_export(args: argparse.Namespace) -> None:  # pylint: disable=too-many-locals
    ds_filter: Optional[str] = getattr(args, "ds", None)
    asset_filter: Optional[str] = getattr(args, "asset", None)
    date_from: Optional[str] = getattr(args, "date_from", None)
    date_to: Optional[str] = getattr(args, "date_to", None)
    output_file: str = args.output_file
    compress: bool = args.compress

    ds_names = _ds_names_in_cache(ds_filter)
    if not ds_names:
        print("No cache files found.")
        return

    export: dict = {
        "bittytax_version": __version__,
        "exported_at": datetime.now().isoformat(),
        "datasources": {},
        "ids": {},
        "assets": {},
    }

    total_price_entries = 0
    total_pairs = 0

    for ds_name in ds_names:
        raw = _load_raw_cache(ds_name)
        if raw:
            ds_export: dict = {}
            for pair, pair_data in raw.items():
                if asset_filter and not pair.upper().startswith(asset_filter.upper() + "/"):
                    continue
                # Skip true legacy flat-format (dates at top level of pair_data)
                if pair_data and _is_date_key(next(iter(pair_data))):
                    print(
                        f"WARNING {ds_name} {pair}: skipping legacy format data "
                        f"\u2014 run bittytax to migrate asset IDs before exporting.",
                        file=sys.stderr,
                    )
                    continue
                pair_export: dict = {}
                for asset_id, name, prices_dict in _iter_asset_entries(pair_data):
                    filtered_prices: dict = {}
                    for date_str, entry in prices_dict.items():
                        if date_from and date_str < date_from:
                            continue
                        if date_to and date_str > date_to:
                            continue
                        filtered_prices[date_str] = entry
                    if filtered_prices:
                        pair_export[asset_id] = {"name": name, "prices": filtered_prices}
                        total_price_entries += len(filtered_prices)
                if pair_export:
                    ds_export[pair] = pair_export
                    total_pairs += 1
            if ds_export:
                export["datasources"][ds_name] = ds_export

        ids_raw = _load_raw_ids(ds_name)
        if ids_raw:
            export["ids"][ds_name] = ids_raw

        assets_raw = _load_raw_assets(ds_name)
        if assets_raw:
            export["assets"][ds_name] = assets_raw

    if not export["ids"]:
        del export["ids"]
    if not export["assets"]:
        del export["assets"]

    if compress and not output_file.endswith(".gz"):
        output_file += ".gz"

    if os.path.exists(output_file):
        try:
            answer = input(f"File '{output_file}' already exists. Overwrite? [y/N] ")
        except EOFError:
            answer = ""
        if answer.strip().lower() != "y":
            print("Aborted.")
            return

    if compress:
        with gzip.open(output_file, "wt", encoding="utf-8") as f:
            json.dump(export, f, indent=4)
    else:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=4)

    file_size = os.path.getsize(output_file)
    ds_count = len(export.get("datasources", {}))
    ids_count = len(export.get("ids", {}))
    assets_count = len(export.get("assets", {}))
    print(
        f"Exported {total_price_entries:,} price entries across {total_pairs} pairs "
        f"from {ds_count} datasource(s); "
        f"{ids_count} ids file(s), {assets_count} assets file(s) "
        f"\u2192 {output_file} ({file_size:,} bytes)"
    )


def cmd_import(args: argparse.Namespace) -> None:  # pylint: disable=too-many-locals
    input_file: str = args.input_file
    overwrite: bool = args.overwrite
    dry_run: bool = getattr(args, "dry_run", False)

    try:
        if input_file.endswith(".gz"):
            with gzip.open(input_file, "rt", encoding="utf-8") as f:
                import_data = json.load(f)
        else:
            with open(input_file, "r", encoding="utf-8") as f:
                import_data = json.load(f)
    except (IOError, ValueError) as e:
        print(f"ERROR Could not read {input_file}: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(import_data, dict) or not any(
        k in import_data for k in ("datasources", "ids", "assets")
    ):
        print(
            "ERROR Unrecognised file format — expected a bittytax_cache export file.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not dry_run:
        os.makedirs(CACHE_DIR, exist_ok=True)

    added = 0
    skipped = 0

    # --- Price data ---
    for ds_name, pair_data in import_data.get("datasources", {}).items():
        existing = _load_raw_cache(ds_name)
        modified = False

        for pair, asset_id_data in pair_data.items():
            if pair not in existing:
                existing[pair] = {}

            existing_pair = existing[pair]
            existing_is_flat = bool(existing_pair) and _is_date_key(next(iter(existing_pair)))

            for asset_id, asset_entry in asset_id_data.items():
                prices = asset_entry.get("prices", {})
                name = asset_entry.get("name", "")

                if existing_is_flat:
                    for date_str, entry in prices.items():
                        if date_str in existing_pair and not overwrite:
                            skipped += 1
                        else:
                            if not dry_run:
                                existing_pair[date_str] = entry
                                modified = True
                            added += 1
                else:
                    if asset_id not in existing_pair:
                        existing_pair[asset_id] = {"name": name, "prices": {}}
                    existing_prices = existing_pair[asset_id].setdefault("prices", {})
                    for date_str, entry in prices.items():
                        if date_str in existing_prices and not overwrite:
                            skipped += 1
                        else:
                            if not dry_run:
                                existing_prices[date_str] = entry
                                modified = True
                            added += 1

        if modified:
            _save_raw_cache(ds_name, existing)

    prefix = "[DRY RUN] " if dry_run else ""
    verb_added = "would be added" if dry_run else "added"
    print(f"{prefix}Price data: {added:,} entries {verb_added}, {skipped:,} skipped")

    # --- Ids files ---
    ids_written = 0
    ids_skipped = 0
    for ds_name, ids_data in import_data.get("ids", {}).items():
        ids_file = os.path.join(CACHE_DIR, ds_name + "_ids.json")
        if os.path.exists(ids_file) and not overwrite:
            ids_skipped += 1
            continue
        ts = ids_data.get("timestamp", "unknown")
        status = _ttl_status(ts) if ts != "unknown" else "[UNKNOWN]"
        warn = (
            f"  WARNING: {status} \u2014 run refresh-ttl to extend" if "EXPIRED" in status else ""
        )
        if not dry_run:
            with open(ids_file, "w", encoding="utf-8") as f:
                json.dump(ids_data, f, indent=4)
            print(f"  {ds_name}_ids.json imported (timestamp: {ts} {status}){warn}")
        else:
            print(
                f"  [DRY RUN] {ds_name}_ids.json would be imported "
                f"(timestamp: {ts} {status}){warn}"
            )
        ids_written += 1

    # --- Assets files ---
    assets_written = 0
    assets_skipped = 0
    for ds_name, assets_data in import_data.get("assets", {}).items():
        assets_file = os.path.join(CACHE_DIR, ds_name + "_assets.json")
        if os.path.exists(assets_file) and not overwrite:
            assets_skipped += 1
            continue
        ts = assets_data.get("timestamp", "unknown")
        status = _ttl_status(ts) if ts != "unknown" else "[UNKNOWN]"
        warn = (
            f"  WARNING: {status} \u2014 run refresh-ttl to extend" if "EXPIRED" in status else ""
        )
        if not dry_run:
            with open(assets_file, "w", encoding="utf-8") as f:
                json.dump(assets_data, f, indent=4)
            print(f"  {ds_name}_assets.json imported (timestamp: {ts} {status}){warn}")
        else:
            print(
                f"  [DRY RUN] {ds_name}_assets.json would be imported "
                f"(timestamp: {ts} {status}){warn}"
            )
        assets_written += 1

    skipped_msg = ""
    if ids_skipped or assets_skipped:
        skipped_msg = (
            f" ({ids_skipped} ids, {assets_skipped} assets skipped — "
            f"use --overwrite to replace)"
        )
    verb_written = "would be written" if dry_run else "written"
    print(
        f"{prefix}Ids/assets: {ids_written} ids file(s), "
        f"{assets_written} assets file(s) {verb_written}"
        f"{skipped_msg}"
    )


def cmd_trim(args: argparse.Namespace) -> None:
    ds_filter: Optional[str] = getattr(args, "ds", None)
    asset_filter: Optional[str] = getattr(args, "asset", None)
    before: Optional[str] = getattr(args, "before", None)
    after: Optional[str] = getattr(args, "after", None)
    dry_run: bool = getattr(args, "dry_run", False)

    if not before and not after:
        print("ERROR: at least one of --before or --after is required.", file=sys.stderr)
        sys.exit(1)

    ds_names = _ds_names_in_cache(ds_filter)
    if not ds_names:
        print("No cache files found.")
        return

    total_removed = 0

    for ds_name in ds_names:
        raw = _load_raw_cache(ds_name)
        if not raw:
            continue

        ds_removed = 0
        modified = False

        for pair, pair_data in raw.items():
            if asset_filter and not pair.upper().startswith(asset_filter.upper() + "/"):
                continue
            for _, _, prices_dict in _iter_asset_entries(pair_data):
                to_remove = [
                    d for d in prices_dict if (before and d < before) or (after and d > after)
                ]
                if to_remove:
                    ds_removed += len(to_remove)
                    if not dry_run:
                        for d in to_remove:
                            del prices_dict[d]
                        modified = True

        if ds_removed:
            prefix = "[DRY RUN] " if dry_run else ""
            verb = "would be removed" if dry_run else "removed"
            print(f"{prefix}{ds_name}: {ds_removed:,} entries {verb}")
            total_removed += ds_removed

        if modified:
            _save_raw_cache(ds_name, raw)

    if total_removed == 0:
        print("No entries matched the filter criteria.")
    elif dry_run:
        print(f"\nTotal: {total_removed:,} entries would be removed (no changes made)")
    else:
        print(f"\nTotal: {total_removed:,} entries removed")


def cmd_show(args: argparse.Namespace) -> None:  # pylint: disable=too-many-locals
    pair: str = args.pair.upper()
    ds_filter: Optional[str] = getattr(args, "ds", None)
    id_filter: Optional[str] = getattr(args, "id", None)
    date_from: Optional[str] = getattr(args, "date_from", None)
    date_to: Optional[str] = getattr(args, "date_to", None)
    date_only: Optional[str] = getattr(args, "date", None)

    if date_only:
        date_from = date_only
        date_to = date_only

    ds_names = _ds_names_in_cache(ds_filter)
    if not ds_names:
        print("No cache files found.")
        return

    found = False
    for ds_name in ds_names:
        raw = _load_raw_cache(ds_name)
        if pair not in raw:
            continue

        entries = _iter_asset_entries(raw[pair])
        if not entries:
            continue

        if id_filter:
            entries = [(aid, name, pd) for aid, name, pd in entries if aid == id_filter]
            if not entries:
                continue

        print(f"{ds_name}  {pair}")
        for asset_id, name, prices_dict in entries:
            label = asset_id if asset_id else "(legacy)"
            if name:
                label = f"{label} ({name})"
            print(f"  {label}")
            dates = sorted(prices_dict.keys())
            if date_from:
                dates = [d for d in dates if d >= date_from]
            if date_to:
                dates = [d for d in dates if d <= date_to]
            if not dates:
                print("    (no entries in range)")
            else:
                rows: List[Tuple[str, str]] = []
                for d in dates:
                    entry = prices_dict[d]
                    price = entry.get("price")
                    if price is None:
                        rows.append((d, "no-price"))
                    else:
                        try:
                            rows.append((d, f"{Decimal(str(price)):,}"))
                        except InvalidOperation:
                            rows.append((d, str(price)))
                int_w = max(len(p.split(".")[0]) if "." in p else len(p) for _, p in rows)
                dec_w = max(len(p.split(".")[1]) if "." in p else 0 for _, p in rows)
                for d, price_str in rows:
                    if "." in price_str:
                        int_part, dec_part = price_str.split(".", 1)
                        aligned = f"{int_part:>{int_w}}.{dec_part:<{dec_w}}"
                    elif price_str == "no-price":
                        aligned = f"{'no-price':>{int_w + 1 + dec_w}}"
                    else:
                        # Integer value: pad right with spaces for missing dot+decimals
                        padding = (" " * (1 + dec_w)) if dec_w else ""
                        aligned = f"{price_str:>{int_w}}{padding}"
                    print(f"    {d}  {aligned}")
        found = True
        print()

    if not found:
        print(f"No cache entries found for pair {pair!r}.")


def cmd_purge(args: argparse.Namespace) -> None:  # pylint: disable=too-many-locals
    ds_filter: Optional[str] = getattr(args, "ds", None)
    asset_filter: Optional[str] = getattr(args, "asset", None)
    pair_filter: Optional[str] = args.pair.upper() if getattr(args, "pair", None) else None
    id_filter: Optional[str] = getattr(args, "id", None)
    date_from: Optional[str] = getattr(args, "date_from", None)
    date_to: Optional[str] = getattr(args, "date_to", None)
    dry_run: bool = getattr(args, "dry_run", False)

    if not ds_filter and not asset_filter and not pair_filter:
        print(
            "ERROR: specify at least one of -ds, --asset, or --pair to avoid accidental wipeout.",
            file=sys.stderr,
        )
        sys.exit(1)

    ds_names = _ds_names_in_cache(ds_filter)
    if not ds_names:
        print("No cache files found.")
        return

    total_removed = 0

    for ds_name in ds_names:
        raw = _load_raw_cache(ds_name)
        if not raw:
            continue

        ds_removed = 0
        modified = False

        for pair, pair_data in raw.items():
            if asset_filter and not pair.upper().startswith(asset_filter.upper() + "/"):
                continue
            if pair_filter and pair.upper() != pair_filter:
                continue

            entries = _iter_asset_entries(pair_data)
            if not entries:
                continue

            if len(entries) > 1 and not id_filter:
                ids = [aid for aid, _, _ in entries if aid]
                print(
                    f"NOTE: {ds_name} {pair} has {len(entries)} asset_id buckets "
                    f"({', '.join(ids)}) \u2014 purging all. Use --id to target one."
                )

            for asset_id, _name, prices_dict in entries:
                if id_filter and asset_id != id_filter:
                    continue

                if date_from is None and date_to is None:
                    to_remove = list(prices_dict.keys())
                else:
                    to_remove = [
                        d
                        for d in prices_dict
                        if (not date_from or d >= date_from) and (not date_to or d <= date_to)
                    ]

                if to_remove:
                    ds_removed += len(to_remove)
                    if not dry_run:
                        for d in to_remove:
                            del prices_dict[d]
                        modified = True

        if ds_removed:
            prefix = "[DRY RUN] " if dry_run else ""
            verb = "would be removed" if dry_run else "removed"
            print(f"{prefix}{ds_name}: {ds_removed:,} entries {verb}")
            total_removed += ds_removed

        if modified:
            _save_raw_cache(ds_name, raw)

    if total_removed == 0:
        print("No entries matched the filter criteria.")
    elif dry_run:
        print(f"\nTotal: {total_removed:,} entries would be removed (no changes made)")
    else:
        print(f"\nTotal: {total_removed:,} entries removed")


def cmd_verify(args: argparse.Namespace) -> None:
    ds_filter: Optional[str] = getattr(args, "ds", None)
    ds_names = _ds_names_in_cache(ds_filter)

    if not ds_names:
        print("No cache files found.")
        return

    issues = 0
    files_checked = 0

    for ds_name in ds_names:
        price_file = os.path.join(CACHE_DIR, ds_name + ".json")
        ids_file = os.path.join(CACHE_DIR, ds_name + "_ids.json")
        assets_file = os.path.join(CACHE_DIR, ds_name + "_assets.json")

        for fpath in (price_file, ids_file, assets_file):
            if not os.path.exists(fpath):
                continue
            files_checked += 1
            fname = os.path.basename(fpath)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (IOError, ValueError) as e:
                print(f"ERROR {fname}: {e}")
                issues += 1
                continue

            if not isinstance(data, dict):
                print(f"ERROR {fname}: root is not a dict")
                issues += 1
                continue

            if fpath == price_file:
                for pair, pair_data in data.items():
                    if not isinstance(pair_data, dict):
                        print(f"  {fname}: {pair} \u2014 pair data is not a dict")
                        issues += 1
                        continue
                    for asset_id, _name, prices_dict in _iter_asset_entries(pair_data):
                        bucket = f"{pair}/{asset_id}" if asset_id else pair
                        for date_str, entry in prices_dict.items():
                            if not _is_date_key(date_str):
                                print(f"  {fname}: {bucket} \u2014 unexpected key {date_str!r}")
                                issues += 1
                            elif not isinstance(entry, dict):
                                print(f"  {fname}: {bucket} {date_str} \u2014 entry is not a dict")
                                issues += 1
                            elif "price" not in entry:
                                print(f"  {fname}: {bucket} {date_str} \u2014 missing 'price' key")
                                issues += 1
            else:
                key = "ids" if fpath == ids_file else "assets"
                if "timestamp" not in data:
                    print(f"  {fname}: missing 'timestamp' key")
                    issues += 1
                if key not in data:
                    print(f"  {fname}: missing '{key}' key")
                    issues += 1

    if files_checked == 0:
        print("No cache files found.")
    elif issues == 0:
        print(f"Verified {files_checked} file(s): no issues found.")
    else:
        print(f"\nVerified {files_checked} file(s): {issues} issue(s) found.")


def cmd_refresh_ttl(args: argparse.Namespace) -> None:
    ds_filter: Optional[str] = getattr(args, "ds", None)
    ds_names = _ds_names_in_cache(ds_filter)
    now_str = datetime.now().isoformat()
    touched = 0

    for ds_name in ds_names:
        for suffix in ("_ids", "_assets"):
            fpath = os.path.join(CACHE_DIR, ds_name + suffix + ".json")
            if not os.path.exists(fpath):
                continue
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                old_ts = data.get("timestamp", "unknown")
                data["timestamp"] = now_str
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                print(f"{ds_name + suffix}.json  {old_ts} \u2192 {now_str}")
                touched += 1
            except (IOError, ValueError) as e:
                print(f"WARNING Could not update {fpath}: {e}", file=sys.stderr)

    if touched == 0:
        print("No ids/assets cache files found.")
    else:
        print(f"\n{touched} file(s) updated.")


def cmd_backup(args: argparse.Namespace) -> None:
    backup_dir: str = getattr(args, "dir", None) or "."
    filename = os.path.join(backup_dir, f"bittytax_cache_{datetime.now():%Y-%m-%d}.json.gz")
    export_args = argparse.Namespace(
        output_file=filename,
        ds=None,
        asset=None,
        date_from=None,
        date_to=None,
        compress=True,
    )
    cmd_export(export_args)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _add_ds_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-ds",
        dest="ds",
        metavar="DATASOURCE",
        help="filter to a specific data source (e.g. CoinGecko)",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bittytax_cache",
        description="Manage the BittyTax local price cache.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_info = subparsers.add_parser("info", help="show cache contents")
    _add_ds_arg(p_info)
    p_info.set_defaults(func=cmd_info)

    p_show = subparsers.add_parser("show", help="display cached prices for a specific pair")
    p_show.add_argument("pair", help="trading pair (e.g. BTC/GBP)")
    _add_ds_arg(p_show)
    p_show.add_argument(
        "--id",
        dest="id",
        metavar="ASSET_ID",
        help="filter to a specific asset_id bucket (e.g. bitcoin)",
    )
    p_show.add_argument(
        "--from",
        dest="date_from",
        metavar="DATE",
        type=_parse_date,
        help="show entries from this date (YYYY-MM-DD)",
    )
    p_show.add_argument(
        "--to",
        dest="date_to",
        metavar="DATE",
        type=_parse_date,
        help="show entries up to this date (YYYY-MM-DD)",
    )
    p_show.add_argument(
        "--date",
        dest="date",
        metavar="DATE",
        type=_parse_date,
        help="show entries for a single date (YYYY-MM-DD)",
    )
    p_show.set_defaults(func=cmd_show)

    p_export = subparsers.add_parser("export", help="export cached price data to a JSON file")
    p_export.add_argument("output_file", help="output filename (JSON)")
    _add_ds_arg(p_export)
    p_export.add_argument(
        "--asset",
        metavar="SYMBOL",
        type=str.upper,
        help="only export entries for this asset symbol (e.g. BTC)",
    )
    p_export.add_argument(
        "--from",
        dest="date_from",
        metavar="DATE",
        type=_parse_date,
        help="only export entries from this date (YYYY-MM-DD)",
    )
    p_export.add_argument(
        "--to",
        dest="date_to",
        metavar="DATE",
        type=_parse_date,
        help="only export entries up to this date (YYYY-MM-DD)",
    )
    p_export.add_argument(
        "--compress",
        action="store_true",
        help="write output as gzip-compressed JSON (appends .gz if not already present)",
    )
    p_export.set_defaults(func=cmd_export)

    p_import = subparsers.add_parser("import", help="import cached price data from a JSON file")
    p_import.add_argument("input_file", help="input filename (JSON)")
    p_import.add_argument(
        "--overwrite",
        action="store_true",
        help="overwrite existing cache entries (default: skip duplicates)",
    )
    p_import.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="preview what would be imported without modifying the cache",
    )
    p_import.set_defaults(func=cmd_import)

    p_backup = subparsers.add_parser(
        "backup",
        help="export entire cache to a dated compressed file",
        description=(
            "Export the full cache to bittytax_cache_YYYY-MM-DD.json.gz "
            "in the current directory."
        ),
    )
    p_backup.add_argument(
        "--dir",
        metavar="DIR",
        help="directory to write the backup file (default: current directory)",
    )
    p_backup.set_defaults(func=cmd_backup)

    p_trim = subparsers.add_parser(
        "trim",
        help="remove cached price entries by date range",
        description=(
            "Remove price entries from the cache. "
            "--before DATE removes entries strictly before that date; "
            "--after DATE removes entries strictly after that date. "
            "Both can be combined to keep only a specific window."
        ),
    )
    _add_ds_arg(p_trim)
    p_trim.add_argument(
        "--asset",
        metavar="SYMBOL",
        type=str.upper,
        help="only trim entries for this asset symbol (e.g. BTC)",
    )
    p_trim.add_argument(
        "--before",
        metavar="DATE",
        type=_parse_date,
        help="remove entries strictly before this date (YYYY-MM-DD)",
    )
    p_trim.add_argument(
        "--after",
        metavar="DATE",
        type=_parse_date,
        help="remove entries strictly after this date (YYYY-MM-DD)",
    )
    p_trim.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="preview what would be removed without modifying the cache",
    )
    p_trim.set_defaults(func=cmd_trim)

    p_purge = subparsers.add_parser(
        "purge",
        help="remove specific cached price entries",
        description=(
            "Remove price entries from the cache by datasource, asset, pair, asset_id, "
            "and/or date range. At least one of -ds, --asset, or --pair is required."
        ),
    )
    _add_ds_arg(p_purge)
    p_purge.add_argument(
        "--asset",
        metavar="SYMBOL",
        type=str.upper,
        help="remove entries for this asset symbol (e.g. BTC)",
    )
    p_purge.add_argument(
        "--pair",
        metavar="PAIR",
        help="remove entries for this exact pair (e.g. BTC/GBP)",
    )
    p_purge.add_argument(
        "--id",
        dest="id",
        metavar="ASSET_ID",
        help="restrict to a specific asset_id bucket (e.g. bitcoin)",
    )
    p_purge.add_argument(
        "--from",
        dest="date_from",
        metavar="DATE",
        type=_parse_date,
        help="remove entries from this date (YYYY-MM-DD)",
    )
    p_purge.add_argument(
        "--to",
        dest="date_to",
        metavar="DATE",
        type=_parse_date,
        help="remove entries up to this date (YYYY-MM-DD)",
    )
    p_purge.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="preview what would be removed without modifying the cache",
    )
    p_purge.set_defaults(func=cmd_purge)

    p_verify = subparsers.add_parser(
        "verify",
        help="check cache files for structural errors",
    )
    _add_ds_arg(p_verify)
    p_verify.set_defaults(func=cmd_verify)

    p_refresh = subparsers.add_parser(
        "refresh-ttl",
        help="reset the TTL timestamp on ids/assets cache files to now",
    )
    _add_ds_arg(p_refresh)
    p_refresh.set_defaults(func=cmd_refresh_ttl)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
