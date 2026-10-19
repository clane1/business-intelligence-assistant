"""Clean uploaded sales data before it is used for analysis."""

import pandas as pd


def clean_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Fill supported sales fields with the application's default values.

    Missing dates and text fields become empty strings; missing amounts become
    zero. Other columns are left unchanged.

    Args:
        df: DataFrame to fill. This operation returns a filled DataFrame.

    Returns:
        A DataFrame with missing values in supported fields replaced.
    """
    return df.fillna({
        "date": "",
        "amount": 0,
        "category": "",
        "item": ""
    })

def clean_types(df: pd.DataFrame) -> pd.DataFrame:
    """Remove supported currency formatting and convert amounts to numbers.

    Amounts that cannot be converted become missing numeric values; callers
    normally run :func:`clean_missing` before this transformation.

    Args:
        df: DataFrame containing an ``amount`` column. The column is updated
            in place.

    Returns:
        The input DataFrame with numeric ``amount`` values.
    """
    df["amount"] = (
        df["amount"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    return df


def clean_dates(df: pd.DataFrame, date_cols: list) -> pd.DataFrame:
    """Normalize supported date formats and convert selected columns.

    Slash separators are changed to dashes, and ``DD-MM-YYYY`` values are
    interpreted as day-month-year before parsing. Unreadable values become
    ``NaT``; no dates are inferred or invented.

    Args:
        df: DataFrame whose selected date columns will be updated in place.
        date_cols: Names of columns to normalize and parse.

    Returns:
        The input DataFrame with selected columns converted to datetime.
    """
    for col in date_cols:
        # Convert slashes to dashes
        df[col] = df[col].astype(str).str.replace("/", "-", regex=False).str.strip()

        # Handle ambiguous DD-MM-YYYY formats manually
        df[col] = df[col].str.replace(
            r"^(\d{2})-(\d{2})-(\d{4})$",
            r"\3-\2-\1",
            regex=True
        )

        # Now safely convert to datetime
        df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def clean_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Return the DataFrame with exact duplicate rows removed.

    Args:
        df: DataFrame to deduplicate.

    Returns:
        A DataFrame containing only the first occurrence of each row.
    """
    return df.drop_duplicates()

def normalize_categories(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Standardize category labels and remove blank or repeated header rows.

    Text is stripped, case-folded, then title-cased for display. Rows whose
    selected value is blank or repeats the column name are excluded.

    Args:
        df: DataFrame to normalize. Its category column is updated in place.
        col: Name of the category column.

    Returns:
        A filtered DataFrame with normalized category labels.
    """
    df[col] = (
        df[col]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    # Remove repeated CSV headers and empty category rows before analysis.
    df = df[df[col] != col.casefold()]
    df = df[df[col] != ""]
    df[col] = df[col].str.title()

    return df

if __name__ == "__main__":
    print("Cleaning started...")

    df = pd.read_csv("data/sales/sales_messy_11.csv")

    df = clean_missing(df)
    df = clean_types(df)
    df = clean_dates(df, ["date"])
    df = clean_duplicates(df)
    df = normalize_categories(df, "category")

    print("Cleaning complete.\n")
    print(df.head())
