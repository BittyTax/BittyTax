"""
Script to calculate and log Deribit funding fees for ETH and USDC for a given tax year.

- Scans all CSV files in the specified folder containing "ETH" or "USDC" in the filename.
- For ETH: Sums the "Funding" column for rows within the tax year date range.
- For USDC: Sums the "Funding" column and, where "type" is "negative_balance_fee",
  also sums the "cashflow" column for rows within the tax year date range.
- Results are logged to a file and printed to the terminal.
- All actions are logged, and errors are trapped and reported.

PEP 8 compliant.
"""

import os
import csv
import logging
from datetime import datetime

def setup_logger(log_path, logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    fh = logging.FileHandler(log_path)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    return logger

def parse_date(date_str):
    """Parse date in various formats, including '11 Nov 2024 18:23:37' and '16 Sept 2024 15:43:29'."""
    # Fix non-standard abbreviation "Sept" to "Sep"
    date_str = date_str.replace("Sept", "Sep")
    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d %b %Y %H:%M:%S",  # e.g., 11 Nov 2024 18:23:37
        "%d %B %Y %H:%M:%S",  # e.g., 16 September 2024 15:43:29
    ):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: {date_str}")

def is_number(s):
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False

def process_files(folder, asset, tax_year_begin, tax_year_end, logger):
    total = 0.0
    start_date = datetime(tax_year_begin, 4, 6)
    end_date = datetime(tax_year_end, 4, 5)
    files = [
        f for f in os.listdir(folder)
        if f.endswith('.csv') and asset in f
    ]
    logger.info(f"Processing {asset} files: {files}")
    for fname in files:
        path = os.path.join(folder, fname)
        try:
            with open(path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        row_date = parse_date(row["Date"])
                    except Exception:
                        logger.warning(
                            f"Skipping row with invalid date in {fname}: "
                            f"{row.get('Date')}"
                        )
                        continue
                    if not (start_date <= row_date <= end_date):
                        continue
                    if asset == "ETH":
                        if is_number(row.get("Funding", "")):
                            total += float(row["Funding"])
                    elif asset == "USDC":
                        if is_number(row.get("Funding", "")):
                            total += float(row["Funding"])
                        if (
                            row.get("type", "") == "negative_balance_fee"
                            and is_number(row.get("cashflow", ""))
                        ):
                            total += float(row["cashflow"])
        except Exception as e:
            logger.error(f"Error processing file {fname}: {e}")
    return total

def main():
    folder = (
        r"C:\Users\agarn\OneDrive\Documents\CryptoTax\2024_2025\Deribit"
    )
    tax_year_begin = 2023
    tax_year_end = 2026

    log_path_eth = os.path.join(
        folder,
        f"ETH_fundingfees_tax_year_{tax_year_begin}_{tax_year_end}.log"
    )
    log_path_usdc = os.path.join(
        folder,
        f"USDC_fundingfees_tax_year_{tax_year_begin}_{tax_year_end}.log"
    )

    logger_eth = setup_logger(log_path_eth, "funding_fees_eth")
    logger_usdc = setup_logger(log_path_usdc, "funding_fees_usdc")

    logger_eth.info("Starting ETH funding fee calculation")
    eth_total = process_files(
        folder, "ETH", tax_year_begin, tax_year_end, logger_eth
    )
    logger_eth.info(
        f"Total ETH funding fees for {tax_year_begin}-{tax_year_end}: "
        f"{eth_total}"
    )

    logger_usdc.info("Starting USDC funding fee calculation")
    usdc_total = process_files(
        folder, "USDC", tax_year_begin, tax_year_end, logger_usdc
    )
    logger_usdc.info(
        f"Total USDC funding fees for {tax_year_begin}-{tax_year_end}: "
        f"{usdc_total}"
    )

if __name__ == "__main__":
    main()

