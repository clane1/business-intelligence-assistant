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
    Checks for columns that should be numeric but contain non-numeric values.
    Returns a dictionary of problematic columns.
    """
    issues = {}
    for col in df.columns:
        if df[col].dtype == object:
            try:
                pd.to_numeric(df[col])
            except:
                issues[col] = "Non-numeric values detected"
    return issues

if __name__ == "__main__":
    df = pd.read_csv("data/sample_data.csv")

    print("Checking required columns...")
    print(validate_columns(df, ["date", "amount", "category", "item"]))

    print("\nChecking missing values...")
    print(validate_missing(df))

    print("\nChecking type issues...")
    print(validate_types(df))
