"""
Spoofed python-bidi package
This module provides the minimum implementation needed for xhtml2pdf to work
without requiring the full python-bidi package.
"""

from typing import Optional


def get_display(text: str, _base_dir: Optional[str] = None, _upper_is_rtl: bool = False) -> str:
    """
    Spoof of the main python-bidi function that normally reorders text
    for display according to the Unicode Bidirectional Algorithm.

    This simplified version just returns the text unchanged,
    which works fine for left-to-right languages.
    """
    return text


def get_base_level(_text: str, _upper_is_rtl: bool = False) -> int:
    """
    Spoof of the function that determines the base direction of text.
    Always returns 0 (LTR) since we're assuming left-to-right text.
    """
    return 0


# Other functions that might be used, but with simplified implementations
def get_embedding_levels(text: str, _upper_is_rtl: bool = False) -> tuple[list[int], int]:
    """Simplified implementation that assumes all text is LTR"""
    return [0] * len(text), 0


def runs(text: str, _embedding_level: Optional[int] = None) -> list[tuple[int, int]]:
    """Simplified implementation that returns the whole text as one run"""
    if not text:
        return []
    return [(0, len(text))]


def reorder_visually(logical_runs: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Since we're assuming LTR text, no reordering is needed"""
    return logical_runs
