"""Aggregate cleaned sales data into dashboard metrics and chart tables."""

import pandas as pd


def calculate_kpis(df: pd.DataFrame) -> dict:
    """Calculate total sales, mean sale amount, and number of records.

    Non-numeric amounts are treated as zero for the total and average. The
    record count includes every row in the provided DataFrame.

    Args:
        df: Cleaned sales data with an ``amount`` column.

    Returns:
        A dictionary with ``total_sales``, ``average_sale``, and
        ``transaction_count`` keys.
    """

    # Force amount column to numeric
    amount_values = pd.to_numeric(
        df["amount"],
        errors="coerce"
    )

    # Treat unparseable amounts as zero so they do not break the KPI totals.
    amount_values = amount_values.fillna(0)

    total_sales = float(
        round(amount_values.sum(), 2)
    )

    average_sale = float(
        round(amount_values.mean(), 2)
    )

    transaction_count = len(df)

    kpis = {
        "total_sales": total_sales,
        "average_sale": average_sale,
        "transaction_count": transaction_count
    }

    return kpis

def sales_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Sum amount by category, ordered from highest to lowest sales.

    Args:
        df: Cleaned sales data with ``category`` and numeric ``amount`` fields.

    Returns:
        A DataFrame with one row per category and its summed amount.
    """

    category_totals = (
        # Group records by category
        df.groupby("category")["amount"]

        # Sum sales for each category
        .sum()

        # Convert grouped data back into a table
        .reset_index()

        # Sort highest revenue first
        .sort_values("amount", ascending=False)
    )

    return category_totals


def sales_by_date(df: pd.DataFrame) -> pd.DataFrame:
    """Sum sales by exact date and return the results chronologically.

    Args:
        df: Sales data with ``date`` and numeric ``amount`` fields.

    Returns:
        A DataFrame with one row per date and its summed amount.
    """

    daily_totals = (
        # Group rows by date
        df.groupby("date")["amount"]

        # Sum sales per day
        .sum()

        # Convert result into a DataFrame
        .reset_index()

        # Sort by date
        .sort_values("date")
    )

    return daily_totals


def sales_by_time_period(
    df: pd.DataFrame
) -> tuple[pd.DataFrame, str]:
    """
    Aggregate valid dated sales at a granularity suited to the date span.

    Spans of at most 31 days use daily totals, spans up to 180 days use
    Monday-starting weekly totals, and longer spans use monthly totals.
    Records with unreadable dates are excluded from this date-based result.

    Args:
        df: Sales data containing ``date`` and numeric ``amount`` columns.

    Returns:
        A pair containing a chronologically ordered ``date``/``amount``
        DataFrame and its frequency (``day``, ``week``, or ``month``). If no
        valid dates remain, the DataFrame is empty and the frequency is
        ``day``.
    """
    dated_sales = df.loc[:, ["date", "amount"]].copy()
    dated_sales["date"] = pd.to_datetime(
        dated_sales["date"],
        errors="coerce"
    )
    dated_sales = dated_sales.dropna(subset=["date"])

    if dated_sales.empty:
        return pd.DataFrame(columns=["date", "amount"]), "day"

    date_span_days = (
        dated_sales["date"].max() - dated_sales["date"].min()
    ).days

    if date_span_days <= 31:
        frequency = "day"
        dated_sales["date"] = dated_sales["date"].dt.normalize()
    elif date_span_days <= 180:
        frequency = "week"
        dated_sales["date"] = (
            dated_sales["date"]
            .dt.to_period("W-SUN")
            .dt.start_time
        )
    else:
        frequency = "month"
        dated_sales["date"] = (
            dated_sales["date"]
            .dt.to_period("M")
            .dt.start_time
        )

    period_totals = (
        dated_sales.groupby("date", as_index=False)["amount"]
        .sum()
        .sort_values("date")
        .reset_index(drop=True)
    )

    return period_totals, frequency


def category_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate each category's sales total and share of total sales.

    When total sales are zero, every percentage is zero to avoid division by
    zero and misleading undefined shares.

    Args:
        df: Cleaned sales data with ``category`` and numeric ``amount`` fields.

    Returns:
        A DataFrame with each category's amount and percentage of sales.
    """

    # Total revenue across the whole dataset
    total_sales = df["amount"].sum()

    distribution = (
        df.groupby("category")["amount"]
        .sum()
        .reset_index()
    )

    if total_sales == 0:
        distribution["percentage"] = 0.0
    else:
        distribution["percentage"] = (
            distribution["amount"] / total_sales * 100
        ).round(2)

    return distribution


if __name__ == "__main__":

    print("Transformation module started...")

    # Load sample data for testing
    df = pd.read_csv("data/sales/sales_sample_10.csv")

    print("\n=== KPI SUMMARY ===")
    print(calculate_kpis(df))

    print("\n=== SALES BY CATEGORY ===")
    print(sales_by_category(df))

    print("\n=== SALES BY DATE ===")
    print(sales_by_date(df))

    print("\n=== CATEGORY DISTRIBUTION ===")
    print(category_distribution(df))

    print("\nTransformation module completed.")