"""Validation checks for uploaded sales datasets."""

import pandas as pd


def validate_columns(df: pd.DataFrame, required_cols: list) -> list:
    """
    Checks whether all required columns exist in the DataFrame.
    Returns a list of missing columns.
    """
    missing = [col for col in required_cols if col not in df.columns]
    return missing

def validate_missing(df: pd.DataFrame) -> pd.Series:
    """
    Returns a count of missing values per column.
    """
    return df.isnull().sum()

def validate_types(df: pd.DataFrame) -> dict:
    """
    Checks whether sale amounts can be converted to numbers.

    Currency symbols and thousands separators are allowed because the
    cleaning step removes them before analysis.
    Returns a dictionary of problematic columns.
    """
    issues = {}
    if "amount" not in df.columns:
        return issues

    raw_amounts = df["amount"]
    amount_text = (
        raw_amounts
        .astype("string")
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    numeric_amounts = pd.to_numeric(
        amount_text,
        errors="coerce"
    )

    invalid_amounts = (
        raw_amounts.notna()
        & amount_text.ne("")
        & numeric_amounts.isna()
    )
    if invalid_amounts.any():
        issues["amount"] = "Non-numeric values detected"
    elif count_currency_values(df):
        issues["amount"] = "Currency-formatted values require cleaning"

    return issues


def count_invalid_dates(df: pd.DataFrame) -> int:
    """
    Counts date values that the cleaning pipeline cannot parse.
    """
    # Normalize the supported input formats before parsing, just like clean_dates.
    date_values = (
        df["date"]
        .astype("string")
        .fillna("")
        .str.replace("/", "-", regex=False)
        .str.strip()
        .str.replace(
            r"^(\d{2})-(\d{2})-(\d{4})$",
            r"\3-\1-\2",
            regex=True
        )
    )

    return int(
        pd.to_datetime(date_values, errors="coerce")
        .isna()
        .sum()
    )


def count_duplicates(df: pd.DataFrame) -> int:
    """
    Counts repeated rows after the first occurrence in the dataset.
    """
    return int(df.duplicated().sum())


def count_currency_values(df: pd.DataFrame) -> int:
    """
    Counts values containing currency symbols that will require cleaning.
    """
    return int(
        df["amount"]
        .astype(str)
        .str.contains(r"\$")
        .sum()
    )


if __name__ == "__main__":
    df = pd.read_csv("data/sample_data.csv")

    print("Checking required columns...")
    print(validate_columns(df, ["date", "amount", "category", "item"]))

    print("\nChecking missing values...")
    print(validate_missing(df))

    print("\nChecking type issues...")
    print(validate_types(df))
