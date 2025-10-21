# Spoofed python-bidi

This is a minimal implementation of `python-bidi` that provides just enough functionality for `xhtml2pdf` to work without requiring the full python-bidi package.

This is only required for Python 3.14 (which is currently NOT supported by the official package), but can still be installed on other Python versions without problem.

BittyTax only uses left-to-right text in PDF reports, bidirectional text is not required.
