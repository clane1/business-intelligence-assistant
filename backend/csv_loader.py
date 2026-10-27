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
        SalesCsvFormatError: If the file is empty, is not readable text, has
            rows that cannot be parsed into a table, or, for headerless input,
            appears to contain a header row or does not parse into exactly
            four columns.
        OSError: If a filesystem source cannot be read.
    """
    try:
        df = load_csv(
            source,
            delimiter=delimiter,
            headers_included=headers_included,
        )
    except pd.errors.EmptyDataError as error:
        raise SalesCsvFormatError(
            "This file is empty. Choose a CSV file that contains your sales "
            "data."
        ) from error
    except UnicodeDecodeError as error:
        raise SalesCsvFormatError(
            "This file can't be read as text. Make sure it's a CSV file; if "
            "it came from a spreadsheet, use Save As and choose "
            "\"CSV UTF-8\", then choose the new file."
        ) from error
    except pd.errors.ParserError as error:
        raise SalesCsvFormatError(
            "This file couldn't be read as a table. Some rows have more "
            "columns than others. Check the file for stray separators or "
            "unclosed quotes, and check that the right separator is "
            f"selected. Details: {error}"
        ) from error

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
                "sales files need four in this order: date, amount, category, "
                "item. Either the separator setting doesn't match your file, "
                "or a required value is missing. Because the file has no "
                "headers, the app can't identify which field is missing. "
                "Check the separator first; if it's right, add the missing "
                "column to your file and choose it again."
            )
        df.columns = SALES_COLUMNS

    return df
