"""Validation checks for uploaded sales datasets."""

import pandas as pd


def validate_columns(df: pd.DataFrame, required_cols: list) -> list:
    """Return the required column names that are absent from ``df``.

    Args:
        df: DataFrame whose schema is being checked.
        required_cols: Column names required by the selected workflow.

    Returns:
        Missing column names in the order provided by ``required_cols``.
    """
    missing = [col for col in required_cols if col not in df.columns]
    return missing

def validate_missing(df: pd.DataFrame) -> pd.Series:
    """Return the number of missing values in each DataFrame column.

    Args:
        df: DataFrame to inspect.

    Returns:
        A Series indexed by column name with missing-value counts.
    """
    return df.isnull().sum()

def validate_types(df: pd.DataFrame) -> dict:
    """
    Check whether non-empty sale amounts can be converted to numbers.

    Currency symbols and thousands separators are allowed because the
    cleaning step removes them before analysis.

    Args:
        df: DataFrame to inspect. If ``amount`` is absent, no amount issue
            can be reported.

    Returns:
        A mapping of problematic column names to user-facing issue details.
        An empty mapping indicates that no amount issue was found or the
        required ``amount`` column is absent.
    """
    issues = {}
    if "amount" not in df.columns:
        return issues

    if invalid_amount_mask(df).any():
        issues["amount"] = "Non-numeric values detected"
    elif count_currency_values(df):
        issues["amount"] = "Currency-formatted values require cleaning"

    return issues


def invalid_amount_mask(df: pd.DataFrame) -> pd.Series:
    """Return a mask for non-empty amount values that cannot be parsed.

    Currency symbols and thousands separators supported by cleaning do not
    count as invalid. The DataFrame must contain an ``amount`` column.
    """
    raw_amounts = df["amount"]
    amount_text = (
        raw_amounts
        .astype("string")
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    numeric_amounts = pd.to_numeric(amount_text, errors="coerce")

    return (
        raw_amounts.notna()
        & amount_text.ne("")
        & numeric_amounts.isna()
    )


def invalid_date_mask(df: pd.DataFrame) -> pd.Series:
    """Return a mask for missing or unparseable values in the date column.

    The supported slash and day-month-year formats are normalized before
    parsing, consistently with the cleaning pipeline. The DataFrame must
    contain a ``date`` column.
    """
    date_values = (
        df["date"]
        .astype("string")
        .fillna("")
        .str.replace("/", "-", regex=False)
        .str.strip()
        .str.replace(
            r"^(\d{2})-(\d{2})-(\d{4})$",
            r"\3-\2-\1",
            regex=True
        )
    )

    return pd.to_datetime(date_values, errors="coerce").isna()


def count_invalid_dates(df: pd.DataFrame) -> int:
    """Count date values that the cleaning pipeline would convert to NaT.

    This function expects a ``date`` column; callers should check the sales
    schema before invoking it.

    Args:
        df: DataFrame with raw date values in a ``date`` column.

    Returns:
        Number of missing or unparseable date values.
    """
    return int(invalid_date_mask(df).sum())


def count_duplicates(df: pd.DataFrame) -> int:
    """Count exact duplicate rows, excluding each row's first occurrence.

    Args:
        df: DataFrame to inspect.

    Returns:
        Number of rows duplicated after their first occurrence.
    """
    return int(df.duplicated().sum())


def count_missing_amounts(df: pd.DataFrame) -> int:
    """Count empty cells in the ``amount`` column (0 if the column is absent)."""
    if "amount" not in df.columns:
        return 0
    return int(df["amount"].isna().sum())


def count_currency_values(df: pd.DataFrame) -> int:
    """Count amount cells containing dollar signs or comma separators.

    This function expects an ``amount`` column; callers should check the sales
    schema before invoking it.

    Args:
        df: DataFrame with amount values in an ``amount`` column.

    Returns:
        Number of amount cells containing a dollar sign or comma.
    """
    return int(
        df["amount"]
        .astype(str)
        .str.contains(r"[\$,]")
        .sum()
    )


if __name__ == "__main__":
    df = pd.read_csv("data/sales/sales_sample_10.csv")

    print("Checking required columns...")
    print(validate_columns(df, ["date", "amount", "category", "item"]))

    print("\nChecking missing values...")
    print(validate_missing(df))

    print("\nChecking type issues...")
    print(validate_types(df))
