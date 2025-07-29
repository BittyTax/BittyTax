import sys
from typing import Any, Optional, TextIO

from tqdm import tqdm

from .config import config
from .constants import TERMINAL_POWERSHELL_GUI


def disable_tqdm() -> bool:
    # Disable progress bar if debug is on, or it's not a terminal, or not using the Powershell GUI
    return bool(
        config.debug or not sys.stdout.isatty() and config.terminal != TERMINAL_POWERSHELL_GUI
    )


def bt_tqdm_write(s: str, end: str = "\n", file: Optional[TextIO] = None) -> None:
    if config.terminal == TERMINAL_POWERSHELL_GUI:
        file = sys.__stderr__

    tqdm.write(s, end=end, file=file)


def bt_print(
    *args: Any,
    sep: str = " ",
    end: str = "\n",
    file: Optional[TextIO] = sys.__stdout__,
    flush: bool = False,
) -> None:
    if config.terminal == TERMINAL_POWERSHELL_GUI:
        file = sys.__stderr__

    text = sep.join(map(str, args)) + end
    if file is not None:
        file.write(text)
        if flush:
            file.flush()
