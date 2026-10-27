"""Detect upload settings that don't match the file, with fix instructions."""

import re

import pandas as pd

DELIMITER_NAMES = {",": "Comma", ";": "Semicolon", "\t": "Tab"}

_DATA_LIKE_HEADER = re.compile(r"^\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|[$]?-?[\d,]+(\.\d+)?)\s*$")


def diagnose_upload(
    df: pd.DataFrame,
    delimiter: str,
    headers_included: bool,
) -> str | None:
    """Return an instruction to fix the upload settings, or ``None`` if fine.

    Checks, in order: a file with no data rows, a file that appears to use a
    different separator than the one selected, and a first row that looks like
    data while it is being treated as column names. Each message names the
    setting to change and says the file must be chosen again.
    """
    if len(df) == 0:
        return (
            "This file has column names but no data rows. Add your sales "
            "rows to the file and choose it again."
        )

    if len(df.columns) == 1:
        sample = " ".join(
            [str(df.columns[0])] + [str(v) for v in df.iloc[:3, 0].tolist()]
        )
        for candidate, name in DELIMITER_NAMES.items():
            if candidate != delimiter and candidate in sample:
                return (
                    f"Everything was read as a single column, and the file "
                    f"looks like it uses a {name.lower()} to separate columns. "
                    f"Change **What separates the columns?** to **{name}** "
                    "above, then choose your file again."
                )

    if headers_included and any(
        _DATA_LIKE_HEADER.match(str(column)) for column in df.columns
    ):
        return (
            "The first row looks like sales data, not column names. Turn off "
            "**The first row contains column names** above, then choose your "
            "file again."
        )

    return None
