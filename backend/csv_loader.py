"""Apply the sales-data schema to CSV content parsed by :mod:`backend.load_csv`.

Unlike :mod:`backend.load_csv`, this module enforces the sales app's specific
headerless-file contract and provides an error message suitable for display
in the upload workflow.
"""

import pandas as pd

from backend.load_csv import CsvSource, load_csv


SALES_COLUMNS = ["date", "amount", "category", "item"]


class SalesCsvFormatError(ValueError):
    """Raised when a sales CSV's header or column layout is invalid.

    The Streamlit frontends catch this exception to display a file-format
    message and stop the upload workflow before validation.
    """


def load_sales_csv(
    source: CsvSource,
    *,
    delimiter: str,
    headers_included: bool,
) -> pd.DataFrame:
    """Read a sales CSV and apply expected column names when needed.

    Args:
        source: Filesystem path or readable text/binary file-like object.
        delimiter: Character separating columns in the uploaded file.
        headers_included: Whether the file's first row contains column names.

    Returns:
        A DataFrame parsed with the selected delimiter. Headerless input is
        assigned the required ``date``, ``amount``, ``category``, and ``item``
        column names in that order.

    Raises:
        SalesCsvFormatError: If headerless input appears to contain a header
            row or does not parse into exactly four columns.
        OSError: If a filesystem source cannot be read.
        pandas.errors.ParserError: If pandas cannot parse the CSV structure.
    """
    df = load_csv(
        source,
        delimiter=delimiter,
        headers_included=headers_included,
    )

    if not headers_included:
        if (
            len(df.index) > 0
            and [
                str(value).strip().casefold()
                for value in df.iloc[0].tolist()
            ]
            == [column.casefold() for column in SALES_COLUMNS]
        ):
            raise SalesCsvFormatError(
                "This file appears to contain a header row. Turn on the "
                "first-row-contains-column-names option."
            )

        if len(df.columns) != len(SALES_COLUMNS):
            raise SalesCsvFormatError(
                f"This file has {len(df.columns)} column(s), but headerless "
                "sales files need exactly four in this order: date, amount, "
                "category, item. Check that the selected delimiter matches "
                "the file."
            )
        df.columns = SALES_COLUMNS

    return df
