"""Expenses validation, cleaning, metrics, and plain-language analysis."""

from dataclasses import replace

import pandas as pd

from backend.cleaning_report import build_expenses_report
from backend.csv_loader import EXPENSES_COLUMNS
from backend.recommendations import (
    CleaningChoices,
    Recommendation,
    build_recommendations,
    clean_with_choices,
)
from backend.transformation import sales_by_time_period

REQUIRED_COLUMNS = EXPENSES_COLUMNS


def _sales_compatible(df: pd.DataFrame) -> pd.DataFrame:
    """Map vendor to the text field used by the shared Sales cleaning logic."""
    compatible = df.rename(columns={"vendor": "item"}).copy()
    compatible["item"] = (
        compatible["item"].fillna("").astype(str).str.strip()
    )
    return compatible


def build_expenses_recommendations(
    df: pd.DataFrame,
) -> list[Recommendation]:
    """Build expense-specific wording for the shared amount/date checks."""
    recommendations = build_recommendations(_sales_compatible(df))
    adjusted = []
    for recommendation in recommendations:
        if recommendation.key == "invalid_dates":
            adjusted.append(
                replace(
                    recommendation,
                    suggested_fix=(
                        "Keep expense amounts but exclude these rows from "
                        "trend analysis"
                    ),
                    impact=(
                        "Kept rows still count in expense totals but not in "
                        "the expense trend. Removing the rows also removes "
                        "their amounts from totals."
                    ),
                )
            )
        elif recommendation.key == "missing_amounts":
            adjusted.append(
                replace(
                    recommendation,
                    impact=(
                        "Affects expense KPIs. If left empty, these expenses "
                        "are ignored in totals and averages."
                    ),
                )
            )
        else:
            adjusted.append(recommendation)
    return adjusted


def clean_expenses(
    df: pd.DataFrame,
    choices: CleaningChoices,
) -> tuple[pd.DataFrame, dict]:
    """Apply shared Sales cleaning rules to the expense schema.

    Vendor is temporarily mapped to the generic text field used by the Sales
    cleaner, then restored. The source DataFrame is not modified.
    """
    cleaned, summary = clean_with_choices(_sales_compatible(df), choices)
    return cleaned.rename(columns={"item": "vendor"}), summary


def expenses_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Return expense totals per category, ordered largest first."""
    return (
        df.groupby("category", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False, kind="stable")
        .reset_index(drop=True)
    )


def expense_trend(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Aggregate readable expense dates at the Sales trend granularity."""
    return sales_by_time_period(df)


def spending_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Return category totals and percentages of positive total spending."""
    totals = expenses_by_category(df)
    total = pd.to_numeric(df["amount"], errors="coerce").fillna(0).sum()
    if total > 0:
        totals["percentage"] = (totals["amount"] / total * 100).round(2)
    else:
        totals["percentage"] = 0.0
    return totals


def expenses_by_vendor(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Return vendors with the largest summed expense amounts."""
    named = df[df["vendor"].fillna("").astype(str).str.strip().ne("")]
    return (
        named.groupby("vendor", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False, kind="stable")
        .head(limit)
        .reset_index(drop=True)
    )


def expenses_kpis(df: pd.DataFrame) -> dict:
    """Calculate total, average, record count, and largest expense category."""
    amounts = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    by_category = expenses_by_category(df)
    largest_category = (
        by_category.iloc[0]["category"]
        if not by_category.empty and amounts.sum() > 0
        else None
    )
    return {
        "total_expenses": float(round(amounts.sum(), 2)),
        "average_expense": float(round(amounts.mean(), 2)) if len(df) else 0.0,
        "expense_records": len(df),
        "largest_expense_category": largest_category,
    }


def _money(amount: float) -> str:
    return f"${amount:,.2f}"


def _period_label(date: pd.Timestamp, frequency: str) -> str:
    if frequency == "month":
        return date.strftime("%B %Y")
    return f"{date:%B} {date.day}, {date.year}"


def generate_expense_insights(df: pd.DataFrame) -> list[str]:
    """Summarize category shares, the expense trend, and largest vendor."""
    insights = []
    kpis = expenses_kpis(df)
    distribution = spending_by_category(df)

    if kpis["total_expenses"] > 0 and not distribution.empty:
        top_category = distribution.iloc[0]
        insights.append(
            f"{top_category['category']} accounts for "
            f"{top_category['percentage']:.0f}% of total expenses."
        )
    else:
        insights.append(
            "Category spending shares are unavailable because total "
            "expenses are not positive."
        )

    trend, frequency = expense_trend(df)
    if trend.empty:
        insights.append(
            "No readable dates were found, so an expense trend is unavailable."
        )
    elif not trend["amount"].gt(0).any():
        insights.append("There are no expenses to compare over time.")
    else:
        highest = trend.loc[trend["amount"].idxmax()]
        date_label = _period_label(highest["date"], frequency)
        if frequency == "week":
            insight = f"Expenses were highest in the week starting {date_label}"
        elif frequency == "month":
            insight = f"Expenses were highest in {date_label}"
        else:
            insight = f"Expenses were highest on {date_label}"
        insights.append(f"{insight} ({_money(highest['amount'])}).")

    vendors = expenses_by_vendor(df, limit=1)
    if not vendors.empty and vendors.iloc[0]["amount"] > 0:
        largest_vendor = vendors.iloc[0]
        insights.append(
            f"{largest_vendor['vendor']} represents the largest spending "
            f"source at {_money(largest_vendor['amount'])}."
        )
    else:
        insights.append("There are no vendor expenses to compare.")

    insights.append(
        f"Total expenses were {_money(kpis['total_expenses'])} across "
        f"{kpis['expense_records']} expense "
        f"{'record' if kpis['expense_records'] == 1 else 'records'}."
    )
    insights.append(
        f"The average expense was {_money(kpis['average_expense'])}."
    )
    return insights


__all__ = [
    "REQUIRED_COLUMNS",
    "CleaningChoices",
    "build_expenses_recommendations",
    "clean_expenses",
    "build_expenses_report",
    "expenses_by_category",
    "expense_trend",
    "spending_by_category",
    "expenses_by_vendor",
    "expenses_kpis",
    "generate_expense_insights",
]