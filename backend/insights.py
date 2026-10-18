"""
insights.py

This module generates simple business insights
from transformed sales data.

The goal is to convert raw KPI calculations
into human-readable observations that can
be displayed in the BI dashboard.
"""

import pandas as pd

# Import functions from transformation.py
from backend.transformation import (
    calculate_kpis,
    sales_by_category,
    sales_by_date,
    category_distribution
)


def generate_insights(df: pd.DataFrame) -> list:
    """
    Generates business insights from a cleaned dataset.

    Parameters:
        df (DataFrame):
            Cleaned sales dataset.

    Returns:
        list:
            A list of business insight strings.
    """

    insights = []

    # -----------------------------
    # KPI DATA
    # -----------------------------

    kpis = calculate_kpis(df)

    total_sales = kpis["total_sales"]
    average_sale = kpis["average_sale"]

    # -----------------------------
    # CATEGORY ANALYSIS
    # -----------------------------

    category_totals = sales_by_category(df)

    if category_totals["amount"].ne(0).any():
        top_category = category_totals.iloc[0]
        insights.append(
            f"{top_category['category']} generated the highest revenue "
            f"(${top_category['amount']:.2f})."
        )

        bottom_category = category_totals.iloc[-1]
        insights.append(
            f"{bottom_category['category']} generated the lowest revenue "
            f"(${bottom_category['amount']:.2f})."
        )
    else:
        insights.append("No non-zero sales were available for category insights.")

    # -----------------------------
    # DAILY SALES ANALYSIS
    # -----------------------------

    daily_totals = sales_by_date(df)

    if daily_totals.empty:
        insights.append("No valid dates were available for daily sales insights.")
    elif not daily_totals["amount"].ne(0).any():
        insights.append("No non-zero sales were available for daily insights.")
    else:
        best_day = daily_totals.loc[
            daily_totals["amount"].idxmax()
        ]
        best_day_date = best_day["date"].strftime("%Y-%m-%d")

        insights.append(
            f"{best_day_date} recorded the highest daily sales "
            f"(${best_day['amount']:.2f})."
        )

        worst_day = daily_totals.loc[
            daily_totals["amount"].idxmin()
        ]
        worst_day_date = worst_day["date"].strftime("%Y-%m-%d")

        insights.append(
            f"{worst_day_date} recorded the lowest daily sales "
            f"(${worst_day['amount']:.2f})."
        )

    # -----------------------------
    # CATEGORY DISTRIBUTION
    # -----------------------------

    distribution = category_distribution(df)

    if total_sales == 0:
        insights.append(
            "Category revenue shares are unavailable because total sales are zero."
        )
    else:
        top_distribution = distribution.loc[
            distribution["percentage"].idxmax()
        ]

        insights.append(
            f"{top_distribution['category']} accounts for "
            f"{top_distribution['percentage']:.2f}% of total revenue."
        )

    # -----------------------------
    # GENERAL KPI OBSERVATIONS
    # -----------------------------

    insights.append(
        f"Total sales were ${total_sales:.2f} across "
        f"{kpis['transaction_count']} transactions."
    )

    insights.append(
        f"The average transaction value was "
        f"${average_sale:.2f}."
    )

    return insights


# ----------------------------------------------------
# TESTING SECTION
# ----------------------------------------------------
#
# This section only runs when the file
# is executed directly.
#
# Example:
# python backend/insights.py
#
# ----------------------------------------------------


if __name__ == "__main__":

    print("Insights module started...")

    # Load sample data
    df = pd.read_csv("data/sample_data.csv")

    # Generate insights from the dataset
    insights = generate_insights(df)

    print("\n=== BUSINESS INSIGHTS ===")

    # Display each insight individually
    for insight in insights:
        print(f"• {insight}")

    print("\nInsights module completed.")