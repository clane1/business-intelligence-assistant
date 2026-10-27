"""Apply the sales-data schema to CSV content parsed by :mod:`backend.load_csv`.

Unlike :mod:`backend.load_csv`, this module enforces the sales app's specific
headerless-file contract and provides an error message suitable for display
in the upload workflow.
"""

import pandas as pd

from backend.load_csv import CsvSource, load_csv


SALES_COLUMNS = ["date", "amount", "category", "item"]
INVENTORY_COLUMNS = ["item", "category", "quantity", "unit_cost"]

_NUMBER_WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


class CsvFormatError(ValueError):
    """Raised when a CSV's header or column layout is invalid.

    The Streamlit frontends catch this exception to display a file-format
    message and stop the upload workflow before validation.
    """


# Kept so existing code that catches the sales-specific name still works.
SalesCsvFormatError = CsvFormatError


def load_sales_csv(
    source: CsvSource,
    *,
    delimiter: str,
    headers_included: bool,
) -> pd.DataFrame:
    """Read a sales CSV and apply expected column names when needed.

    See :func:`load_dataset_csv`; this applies the sales column order
    ``date``, ``amount``, ``category``, ``item`` to headerless files.
    """
    return load_dataset_csv(
        source,
        delimiter=delimiter,
        headers_included=headers_included,
        columns=SALES_COLUMNS,
        label="sales",
    )


def load_inventory_csv(
    source: CsvSource,
    *,
    delimiter: str,
    headers_included: bool,
) -> pd.DataFrame:
    """Read an inventory CSV; headerless files must hold the four required columns.

    Optional inventory columns (``reorder_level``, ``last_updated``) need a
    header row, because their position can't be guessed.
    """
    return load_dataset_csv(
        source,
        delimiter=delimiter,
        headers_included=headers_included,
        columns=INVENTORY_COLUMNS,
        label="inventory",
    )


def load_dataset_csv(
    source: CsvSource,
    *,
    delimiter: str,
    headers_included: bool,
    columns: list[str],
    label: str,
) -> pd.DataFrame:
    """Read a CSV and apply the expected column names when needed.

    Args:
        source: Filesystem path or readable text/binary file-like object.
        delimiter: Character separating columns in the uploaded file.
        headers_included: Whether the file's first row contains column names.
        columns: Required column names, in the order a headerless file
            must provide them.
        label: Dataset name used in messages (for example ``"sales"``).

    Returns:
        A DataFrame parsed with the selected delimiter. Headerless input is
        assigned ``columns`` in order.

    Raises:
        CsvFormatError: If the file is empty, is not readable text, has
            rows that cannot be parsed into a table, or, for headerless input,
            appears to contain a header row or does not parse into exactly
            ``len(columns)`` columns.
        OSError: If a filesystem source cannot be read.
    """
    try:
        df = load_csv(
            source,
            delimiter=delimiter,
            headers_included=headers_included,
        )
    except pd.errors.EmptyDataError as error:
        raise CsvFormatError(
            f"This file is empty. Choose a CSV file that contains your {label} "
            "data."
        ) from error
    except UnicodeDecodeError as error:
        raise CsvFormatError(
            "This file can't be read as text. Make sure it's a CSV file; if "
            "it came from a spreadsheet, use Save As and choose "
            "\"CSV UTF-8\", then choose the new file."
        ) from error
    except pd.errors.ParserError as error:
        raise CsvFormatError(
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
            == [column.casefold() for column in columns]
        ):
            raise CsvFormatError(
                "This file appears to contain a header row. Turn on the "
                "first-row-contains-column-names option."
            )

        if len(df.columns) != len(columns):
            needed = _NUMBER_WORDS.get(len(columns), str(len(columns)))
            raise CsvFormatError(
                f"This file has {len(df.columns)} column(s), but headerless "
                f"{label} files need {needed} in this order: "
                f"{', '.join(columns)}. Either the separator setting doesn't "
                "match your file, or a required value is missing. Because the "
                "file has no headers, the app can't identify which field is "
                "missing. Check the separator first; if it's right, add the "
                "missing column to your file and choose it again."
            )
        df.columns = columns

    return df
