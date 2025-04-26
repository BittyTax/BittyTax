# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2023

import os

import dateutil.tz
from colorama import Back, Fore, Style

TZ_UTC = dateutil.tz.UTC

PROJECT_URL = "https://github.com/BittyTax/BittyTax"

BITTYTAX_PATH = os.path.expanduser("~/.bittytax")
CACHE_DIR = os.path.join(BITTYTAX_PATH, "cache")

CONV_FORMAT_CSV = "CSV"
CONV_FORMAT_EXCEL = "EXCEL"
CONV_FORMAT_RECAP = "RECAP"

WARNING = f"{Back.YELLOW}{Fore.BLACK}WARNING{Back.RESET}{Fore.YELLOW}"
ERROR = f"{Back.RED}{Fore.BLACK}ERROR{Back.RESET}{Fore.RED}"

H1 = f"\n{Fore.CYAN}{Style.BRIGHT}"
_H1 = f"{Style.NORMAL}"

FONT_COLOR_TX_HASH = "7A7A7A"
FONT_COLOR_TX_SRC = "7C7C7C"
FONT_COLOR_TX_DEST = "7D7D7D"

EXCEL_PRECISION = 15
