import pandas as pd

def clean_missing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fills missing values with defaults.
    For now: numeric -> 0, strings -> empty string.
    """
    return df.fillna({
        "date": "",
        "amount": 0,
        "category": "",
        "item": ""
    })

def clean_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts columns to the correct data types.
    - removes currency symbols
    - amount -> numeric
    """
    df["amount"] = (
        df["amount"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.strip()
    )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    return df


def clean_dates(df: pd.DataFrame, date_cols: list) -> pd.DataFrame:
    """
    Normalizes mixed date formats before converting to datetime.
    """
    for col in date_cols:
        # Convert slashes to dashes
        df[col] = df[col].astype(str).str.replace("/", "-", regex=False).str.strip()

        # Handle ambiguous DD-MM-YYYY formats manually
        df[col] = df[col].str.replace(
            r"^(\d{2})-(\d{2})-(\d{4})$",
            r"\3-\1-\2",
            regex=True
        )

        # Now safely convert to datetime
        df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def clean_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Removes duplicate rows.
    """
    return df.drop_duplicates()

def normalize_categories(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Normalizes category labels:
    - lowercase
    - strip spaces
    """
    df[col] = df[col].astype(str).str.lower().str.strip()
    return df

if __name__ == "__main__":
    print("Cleaning started...")

    df = pd.read_csv("data/messy_data.csv")

    df = clean_missing(df)
    df = clean_types(df)
    df = clean_dates(df, ["date"])
    df = clean_duplicates(df)
    df = normalize_categories(df, "category")

    print("Cleaning complete.\n")
    print(df.head())
