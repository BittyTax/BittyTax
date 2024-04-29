# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

import os

import dateutil.tz
from colorama import Back, Fore, Style

TZ_UTC = dateutil.tz.UTC

PROJECT_URL = "https://github.com/BittyTax/BittyTax"

BITTYTAX_PATH = os.path.expanduser("~/.bittytax")
CACHE_DIR = os.path.join(BITTYTAX_PATH, "cache")

FORMAT_CSV = "CSV"
FORMAT_EXCEL = "EXCEL"
FORMAT_RECAP = "RECAP"

TAX_RULES_UK_INDIVIDUAL = "UK_INDIVIDUAL"
TAX_RULES_UK_COMPANY = [
    "UK_COMPANY_JAN",
    "UK_COMPANY_FEB",
    "UK_COMPANY_MAR",
    "UK_COMPANY_APR",
    "UK_COMPANY_MAY",
    "UK_COMPANY_JUN",
    "UK_COMPANY_JUL",
    "UK_COMPANY_AUG",
    "UK_COMPANY_SEP",
    "UK_COMPANY_OCT",
    "UK_COMPANY_NOV",
    "UK_COMPANY_DEC",
]

WARNING = f"{Back.YELLOW}{Fore.BLACK}WARNING{Back.RESET}{Fore.YELLOW}"
ERROR = f"{Back.RED}{Fore.BLACK}ERROR{Back.RESET}{Fore.RED}"

H1 = f"\n{Fore.CYAN}{Style.BRIGHT}"
_H1 = f"{Style.NORMAL}"

FONT_COLOR_TX_HASH = "7A7A7A"
FONT_COLOR_TX_SRC = "7C7C7C"
FONT_COLOR_TX_DEST = "7D7D7D"
