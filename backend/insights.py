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
    sales_by_time_period,
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
        if len(category_totals) == 1:
            category = category_totals.iloc[0]["category"]
            insights.append(
                f"All recorded sales came from {category}; "
                "no category comparison is available."
            )
        else:
            top_category = category_totals.iloc[0]
            insights.append(
                f"Sales were highest for {top_category['category']} "
                f"(${top_category['amount']:.2f})."
            )

            bottom_category = category_totals.iloc[-1]
            insights.append(
                f"Sales were lowest for {bottom_category['category']} "
                f"(${bottom_category['amount']:.2f})."
            )
    else:
        insights.append("There are no sales amounts to compare by category.")

    # -----------------------------
    # DATE-BASED SALES ANALYSIS
    # -----------------------------

    period_totals, frequency = sales_by_time_period(df)

    if period_totals.empty:
        insights.append(
            "No readable dates were found, so a sales trend is unavailable."
        )
    elif not period_totals["amount"].ne(0).any():
        insights.append("There are no sales amounts to compare over time.")
    else:
        best_period = period_totals.loc[
            period_totals["amount"].idxmax()
        ]
        worst_period = period_totals.loc[
            period_totals["amount"].idxmin()
        ]
        if frequency == "month":
            best_period_label = best_period["date"].strftime("%B %Y")
            worst_period_label = worst_period["date"].strftime("%B %Y")
            best_period_insight = (
                f"Sales were highest in {best_period_label} "
                f"(${best_period['amount']:.2f})."
            )
            worst_period_insight = (
                f"Sales were lowest in {worst_period_label} "
                f"(${worst_period['amount']:.2f})."
            )
        elif frequency == "week":
            best_period_label = (
                f"{best_period['date']:%B} {best_period['date'].day}, "
                f"{best_period['date'].year}"
            )
            worst_period_label = (
                f"{worst_period['date']:%B} {worst_period['date'].day}, "
                f"{worst_period['date'].year}"
            )
            best_period_insight = (
                f"The week starting {best_period_label} had the most sales "
                f"(${best_period['amount']:.2f})."
            )
            worst_period_insight = (
                f"The week starting {worst_period_label} had the least sales "
                f"(${worst_period['amount']:.2f})."
            )
        else:
            best_period_label = (
                f"{best_period['date']:%B} {best_period['date'].day}, "
                f"{best_period['date'].year}"
            )
            worst_period_label = (
                f"{worst_period['date']:%B} {worst_period['date'].day}, "
                f"{worst_period['date'].year}"
            )
            best_period_insight = (
                f"Sales were highest on {best_period_label} "
                f"(${best_period['amount']:.2f})."
            )
            worst_period_insight = (
                f"Sales were lowest on {worst_period_label} "
                f"(${worst_period['amount']:.2f})."
            )

        insights.append(best_period_insight)
        insights.append(worst_period_insight)

    # -----------------------------
    # CATEGORY DISTRIBUTION
    # -----------------------------

    distribution = category_distribution(df)

    if total_sales == 0:
        insights.append(
            "Category shares are unavailable because total sales are zero."
        )
    else:
        top_distribution = distribution.loc[
            distribution["percentage"].idxmax()
        ]

        insights.append(
            f"{top_distribution['category']} accounts for "
            f"{top_distribution['percentage']:.2f}% of total sales."
        )

    # -----------------------------
    # GENERAL KPI OBSERVATIONS
    # -----------------------------

    record_label = (
        "sales record"
        if kpis["transaction_count"] == 1
        else "sales records"
    )
    insights.append(
        f"Total sales were ${total_sales:.2f} across "
        f"{kpis['transaction_count']} {record_label}."
    )

    insights.append(
        f"The average sale was ${average_sale:.2f}."
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
    df = pd.read_csv("data/sales/sales_sample_10.csv")

    # Generate insights from the dataset
    insights = generate_insights(df)

    print("\n=== BUSINESS INSIGHTS ===")

    # Display each insight individually
    for insight in insights:
        print(f"• {insight}")

    print("\nInsights module completed.")