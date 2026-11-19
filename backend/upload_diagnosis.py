"""Detect upload settings that don't match the file, with fix instructions."""

import re

import pandas as pd

from backend.csv_loader import EXPENSES_COLUMNS, INVENTORY_COLUMNS, SALES_COLUMNS

DELIMITER_NAMES = {",": "Comma", ";": "Semicolon", "\t": "Tab"}
DATASET_COLUMNS = {
    "Sales": SALES_COLUMNS,
    "Inventory": INVENTORY_COLUMNS,
    "Expenses": EXPENSES_COLUMNS,
}

_DATA_LIKE_HEADER = re.compile(r"^\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|[$]?-?[\d,]+(\.\d+)?)\s*$")


def detect_dataset_mismatch(df: pd.DataFrame, selected: str) -> str | None:
    """Suggest another type only when its complete standard headers match.

    A file matching the selected schema or multiple other schemas is ambiguous
    and receives no suggestion. Headerless data must not be passed here.
    """
    columns = {str(column).strip().casefold() for column in df.columns}
    if set(DATASET_COLUMNS[selected]).issubset(columns):
        return None
    matches = [
        name for name, required in DATASET_COLUMNS.items()
        if name != selected and set(required).issubset(columns)
    ]
    return matches[0] if len(matches) == 1 else None


def dataset_mismatch_message(df: pd.DataFrame, selected: str) -> str | None:
    """Explain a possible mismatch without blocking custom column mapping."""
    match = detect_dataset_mismatch(df, selected)
    if match is None:
        return None
    return (
        f"You selected {selected}, but this file's column names match {match}. "
        f"If this is {match} data, go back to Upload Data, select {match} "
        "under Dataset type, and choose the file again. Changing dataset type "
        f"clears the current upload. If this is {selected} data with different "
        "column names, continue and use Match your columns instead."
    )


def diagnose_upload(
    df: pd.DataFrame,
    delimiter: str,
    headers_included: bool,
    label: str = "sales",
) -> str | None:
    """Return an instruction to fix the upload settings, or ``None`` if fine.

    Checks, in order: a file with no data rows, a file that appears to use a
    different separator than the one selected, and a first row that looks like
    data while it is being treated as column names. Each message names the
    setting to change and says the file must be chosen again. ``label`` is
    the dataset name used in the messages.
    """
    if len(df) == 0:
        return (
            f"This file has column names but no data rows. Add your {label} "
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
            f"The first row looks like {label} data, not column names. Turn off "
            "**The first row contains column names** above, then choose your "
            "file again."
        )

    return None
