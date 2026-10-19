"""Low-level CSV parsing shared by the sales loader and local scripts.

This module only reads tabular CSV content. It does not validate or rename
sales columns; sales-specific header rules belong in :mod:`backend.csv_loader`.
Read and parsing errors from pandas are intentionally allowed to propagate so
callers can report or handle the actual failure.
"""

from pathlib import Path
from typing import IO

import pandas as pd


CsvSource = str | Path | IO[bytes] | IO[str]


def load_csv(
    source: CsvSource,
    *,
    delimiter: str = ",",
    headers_included: bool = True,
) -> pd.DataFrame:
    """Read CSV content into a DataFrame without applying a domain schema.

    Args:
        source: Filesystem path or readable text/binary file-like object.
        delimiter: Character separating fields in each CSV record.
        headers_included: Whether pandas should treat the first row as column
            names. If false, pandas assigns integer column labels.

    Returns:
        The parsed CSV as a pandas DataFrame.

    Raises:
        OSError: If a filesystem source cannot be read.
        pandas.errors.ParserError: If pandas cannot parse the CSV structure.
    """
    return pd.read_csv(
        source,
        sep=delimiter,
        header=0 if headers_included else None,
    )


if __name__ == "__main__":
    sample_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "sales"
        / "sales_sample_10.csv"
    )
    sample_df = load_csv(sample_path)
    print("CSV loaded successfully.")
    print(sample_df.head())
