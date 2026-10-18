"""Aggregate cleaned sales data into dashboard metrics and chart tables."""

import pandas as pd


def calculate_kpis(df: pd.DataFrame) -> dict:
    """
    Calculates key performance indicators (KPIs)
    from the cleaned dataset.

    Returns:
        total_sales
        average_sale
        transaction_count
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
    """
    Groups sales by category.

    This is useful for:
    - bar charts
    - category analysis
    - identifying top-performing categories
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
    """
    Calculates total sales for each date.

    This will later be used for:
    - line charts
    - trend analysis
    - forecasting
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


def category_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the percentage contribution
    of each category to total revenue.

    Useful for:
    - pie charts
    - dashboard summaries
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
    df = pd.read_csv("data/sample_data.csv")

    print("\n=== KPI SUMMARY ===")
    print(calculate_kpis(df))

    print("\n=== SALES BY CATEGORY ===")
    print(sales_by_category(df))

    print("\n=== SALES BY DATE ===")
    print(sales_by_date(df))

    print("\n=== CATEGORY DISTRIBUTION ===")
    print(category_distribution(df))

    print("\nTransformation module completed.")