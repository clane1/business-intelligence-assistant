"""Inventory dataset support: validation, recommendations, cleaning and analysis.

Required columns are ``item``, ``category``, ``quantity`` and ``unit_cost``.
``reorder_level`` and ``last_updated`` are optional; when ``reorder_level`` is
present the dashboard also reports low-stock items. Inventory value is always
``quantity * unit_cost``.

The structure mirrors the sales workflow: validation never changes data,
:func:`build_inventory_recommendations` turns findings into fixes the user can
accept or reject, and :func:`clean_inventory` applies only the accepted ones.
Negative quantities and costs are flagged for review rather than silently
corrected.
"""

from dataclasses import dataclass, field

import pandas as pd

from backend.cleaning import clean_duplicates, normalize_categories
from backend.csv_loader import INVENTORY_COLUMNS
from backend.recommendations import Recommendation, _examples, _plural, _preview
from backend.validation import count_duplicates

REQUIRED_COLUMNS = INVENTORY_COLUMNS
NUMERIC_COLUMNS = ["quantity", "unit_cost"]


# ----------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------

def _numeric_text(series: pd.Series) -> pd.Series:
    """Parse text such as ``"$1,200.50"`` into numbers; unreadable becomes NaN."""
    text = (
        series.astype("string")
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(text, errors="coerce").astype("float64")


def invalid_number_mask(df: pd.DataFrame, column: str) -> pd.Series:
    """Mask non-empty values in ``column`` that cannot be read as numbers.

    Dollar signs and thousands separators are accepted, as cleaning removes
    them. Empty cells are not invalid; they are reported as missing.
    """
    raw = df[column]
    blank = raw.astype("string").str.strip().eq("").fillna(False).astype(bool)
    return (raw.notna() & ~blank & _numeric_text(raw).isna()).astype(bool)


def count_missing(df: pd.DataFrame, column: str) -> int:
    """Count empty cells in ``column`` (0 if the column is absent)."""
    if column not in df.columns:
        return 0
    return int(df[column].isna().sum())


def count_negative(df: pd.DataFrame, column: str) -> int:
    """Count readable numbers below zero in ``column`` (0 if absent)."""
    if column not in df.columns:
        return 0
    return int((_numeric_text(df[column]) < 0).sum())


def count_currency_symbols(df: pd.DataFrame, column: str = "unit_cost") -> int:
    """Count cells in ``column`` that contain a dollar sign or comma."""
    if column not in df.columns:
        return 0
    return int(df[column].astype(str).str.contains(r"[\$,]").sum())


def count_unreadable_reorder_levels(df: pd.DataFrame) -> int:
    """Count non-empty ``reorder_level`` values that are not numbers."""
    if "reorder_level" not in df.columns:
        return 0
    return int(invalid_number_mask(df, "reorder_level").sum())


def blocking_problems(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Return a mask per numeric column whose values stop cleaning.

    Only columns with at least one non-numeric value are included.
    """
    problems = {}
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            mask = invalid_number_mask(df, column)
            if mask.any():
                problems[column] = mask
    return problems


# ----------------------------------------------------------------------
# Recommendations
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class InventoryChoices:
    """The fixes the user accepted. Defaults match the suggested fixes."""

    remove_duplicates: bool = True
    fill_missing_quantity: bool = True
    fill_missing_unit_cost: bool = True
    remove_negative_quantity_rows: bool = False
    remove_negative_unit_cost_rows: bool = False
    # Maps a normalized (title-case) category to the spelling the user accepted.
    category_corrections: dict[str, str] = field(default_factory=dict)


def build_inventory_recommendations(df: pd.DataFrame) -> list[Recommendation]:
    """Return one recommendation per inventory issue found in ``df``.

    Issues that are not present produce no recommendation. The DataFrame is
    not modified. Checks for absent columns are skipped.
    """
    recommendations = []

    duplicates = count_duplicates(df)
    if duplicates:
        recommendations.append(Recommendation(
            key="duplicates",
            title=f"{_plural(duplicates, 'duplicate row')} found",
            suggested_fix="Remove duplicate rows",
            impact=f"{len(df)} rows → {len(df) - duplicates} rows",
            count=duplicates,
            preview=_preview(df, df.duplicated()),
        ))

    missing_quantity = count_missing(df, "quantity")
    if missing_quantity:
        recommendations.append(Recommendation(
            key="missing_quantity",
            title=f"{_plural(missing_quantity, 'missing quantity')} found",
            suggested_fix="Replace missing quantities with 0",
            impact=(
                "Affects unit totals and inventory value. If left empty, "
                "these rows are ignored in totals."
            ),
            count=missing_quantity,
            preview=_preview(df, df["quantity"].isna()),
        ))

    missing_cost = count_missing(df, "unit_cost")
    if missing_cost:
        recommendations.append(Recommendation(
            key="missing_unit_cost",
            title=f"{_plural(missing_cost, 'missing unit cost')} found",
            suggested_fix="Replace missing unit costs with 0",
            impact=(
                "Items with a unit cost of 0 add no value to the inventory "
                "total, so total inventory value may be understated."
            ),
            count=missing_cost,
            preview=_preview(df, df["unit_cost"].isna()),
        ))

    for column, key, singular, plural in (
        ("quantity", "negative_quantity", "negative quantity", "negative quantities"),
        ("unit_cost", "negative_unit_cost", "negative unit cost", "negative unit costs"),
    ):
        negatives = count_negative(df, column)
        if negatives:
            mask = _numeric_text(df[column]) < 0
            recommendations.append(Recommendation(
                key=key,
                title=f"{negatives} {singular if negatives == 1 else plural} found",
                suggested_fix="Review before analysis",
                impact=(
                    "Kept rows reduce totals. Negative values can be returns "
                    "or data-entry mistakes, so the app does not change "
                    "them unless you choose to remove the rows."
                ),
                count=negatives,
                preview=_preview(df, mask, column),
                examples=_examples(df, mask, column),
            ))

    return recommendations


# ----------------------------------------------------------------------
# Cleaning
# ----------------------------------------------------------------------

def clean_inventory(
    df: pd.DataFrame,
    choices: InventoryChoices,
) -> tuple[pd.DataFrame, dict]:
    """Clean inventory data applying only the fixes the user accepted.

    Always applied: stripping item names, converting ``$`` and comma-formatted
    numbers, standardizing categories (blank-category rows are dropped), and
    reading ``reorder_level`` as numbers. ``df`` is not modified.

    Returns:
        The cleaned DataFrame and a summary dictionary of what changed.
    """
    df = df.copy()
    rows_before = len(df)
    duplicates_found = count_duplicates(df)
    missing_quantity = count_missing(df, "quantity")
    missing_cost = count_missing(df, "unit_cost")
    currency_values = count_currency_symbols(df)
    negative_quantity = count_negative(df, "quantity")
    negative_cost = count_negative(df, "unit_cost")

    df["item"] = df["item"].fillna("").astype(str).str.strip()
    df["category"] = df["category"].fillna("")
    for column in NUMERIC_COLUMNS:
        df[column] = _numeric_text(df[column])
    if "reorder_level" in df.columns:
        df["reorder_level"] = _numeric_text(df["reorder_level"])

    if choices.fill_missing_quantity:
        df["quantity"] = df["quantity"].fillna(0)
    if choices.fill_missing_unit_cost:
        df["unit_cost"] = df["unit_cost"].fillna(0)

    negative_rows_removed = 0
    if choices.remove_negative_quantity_rows:
        keep = ~(df["quantity"] < 0)
        negative_rows_removed += int((~keep).sum())
        df = df[keep]
    if choices.remove_negative_unit_cost_rows:
        keep = ~(df["unit_cost"] < 0)
        negative_rows_removed += int((~keep).sum())
        df = df[keep]

    rows_before_dedup = len(df)
    if choices.remove_duplicates:
        df = clean_duplicates(df)
    duplicates_removed = rows_before_dedup - len(df)

    rows_before_category = len(df)
    df = normalize_categories(df, "category")
    category_rows_removed = rows_before_category - len(df)

    corrections = choices.category_corrections
    categories_corrected = int(df["category"].isin(corrections).sum())
    applied = [
        {
            "original": original,
            "suggestion": suggestion,
            "rows": int(df["category"].eq(original).sum()),
        }
        for original, suggestion in corrections.items()
    ]
    if corrections:
        df = df.assign(category=df["category"].replace(corrections))

    has_reorder_level = "reorder_level" in df.columns
    summary = {
        "rows_before": rows_before,
        "rows_after": len(df),
        "duplicates_found": duplicates_found,
        "duplicates_removed": duplicates_removed,
        "missing_quantity_found": missing_quantity,
        "missing_quantity_filled": (
            missing_quantity if choices.fill_missing_quantity else 0
        ),
        "missing_unit_cost_found": missing_cost,
        "missing_unit_cost_filled": (
            missing_cost if choices.fill_missing_unit_cost else 0
        ),
        "negative_quantity_found": negative_quantity,
        "negative_unit_cost_found": negative_cost,
        "negative_rows_removed": negative_rows_removed,
        "remove_negative_quantity_rows": choices.remove_negative_quantity_rows,
        "remove_negative_unit_cost_rows": choices.remove_negative_unit_cost_rows,
        "unit_costs_converted": currency_values,
        "category_rows_removed": category_rows_removed,
        "categories_corrected": categories_corrected,
        "category_corrections": applied,
        "has_reorder_level": has_reorder_level,
        "low_stock_items": (
            low_stock_item_count(df) if has_reorder_level else None
        ),
    }
    return df.reset_index(drop=True), summary


# ----------------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------------

def with_value(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with ``value`` = ``quantity * unit_cost`` (empty counts as 0)."""
    result = df.copy()
    result["value"] = (
        pd.to_numeric(result["quantity"], errors="coerce").fillna(0)
        * pd.to_numeric(result["unit_cost"], errors="coerce").fillna(0)
    )
    return result


def _named_items(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["item"].astype(str).str.strip() != ""]


def inventory_kpis(df: pd.DataFrame) -> dict:
    """Calculate the four inventory KPIs.

    Returns:
        ``total_value`` (sum of quantity x unit cost), ``total_units``,
        ``unique_items`` (distinct non-blank item names) and ``top_category``
        (category with the highest inventory value, or ``None`` when no
        category has any value).
    """
    valued = with_value(df)
    by_category = value_by_category(df)
    top_category = (
        by_category.iloc[0]["category"] if by_category["value"].gt(0).any() else None
    )
    return {
        "total_value": float(round(valued["value"].sum(), 2)),
        "total_units": float(
            pd.to_numeric(df["quantity"], errors="coerce").fillna(0).sum()
        ),
        "unique_items": int(_named_items(df)["item"].nunique()),
        "top_category": top_category,
    }


def value_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Inventory value per category, highest first."""
    return (
        with_value(df).groupby("category", as_index=False)["value"].sum()
        .sort_values("value", ascending=False, kind="stable")
        .reset_index(drop=True)
    )


def units_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Units in stock per category, highest first."""
    valued = df.assign(
        quantity=pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    )
    return (
        valued.groupby("category", as_index=False)["quantity"].sum()
        .sort_values("quantity", ascending=False, kind="stable")
        .reset_index(drop=True)
    )


def top_value_items(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """The ``limit`` items with the highest total value, summed across rows."""
    return (
        with_value(_named_items(df)).groupby("item", as_index=False)["value"].sum()
        .sort_values("value", ascending=False, kind="stable")
        .head(limit)
        .reset_index(drop=True)
    )


def low_stock_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Rows where quantity is at or below a known reorder level.

    Returns an empty frame when there is no ``reorder_level`` column.
    """
    if "reorder_level" not in df.columns:
        return df.iloc[0:0]
    quantity = pd.to_numeric(df["quantity"], errors="coerce")
    reorder = pd.to_numeric(df["reorder_level"], errors="coerce")
    return df[reorder.notna() & (quantity <= reorder)]


def low_stock_item_count(df: pd.DataFrame) -> int:
    """Number of distinct items at or below their reorder level."""
    rows = _named_items(low_stock_rows(df))
    return int(rows["item"].nunique())


def _money(value: float) -> str:
    return f"${value:,.2f}"


def generate_inventory_insights(df: pd.DataFrame) -> list[str]:
    """Generate plain-language observations from cleaned inventory data.

    Covers category share of value, the highest-value item, the category with
    the most units, low stock (when reorder levels exist) and value
    concentration across the top three categories. Comparisons that cannot be
    made (for example when total value is zero) are explained instead of
    invented.
    """
    insights = []
    kpis = inventory_kpis(df)
    total_value = kpis["total_value"]
    by_value = value_by_category(df)

    if total_value > 0 and kpis["top_category"] is not None:
        share = by_value.iloc[0]["value"] / total_value * 100
        insights.append(
            f"{kpis['top_category']} represents {share:.0f}% of total "
            "inventory value."
        )
        top_items = top_value_items(df, 1)
        if not top_items.empty and top_items.iloc[0]["value"] > 0:
            insights.append(
                f"{top_items.iloc[0]['item']} inventory has the highest "
                f"total value at {_money(top_items.iloc[0]['value'])}."
            )
    else:
        insights.append(
            "Inventory value comparisons are unavailable because total "
            "inventory value is $0. Check that unit costs and quantities are "
            "filled in."
        )

    units = units_by_category(df)
    if not units.empty and units.iloc[0]["quantity"] > 0:
        insights.append(
            f"{units.iloc[0]['category']} contains the largest number of "
            "units in stock."
        )

    if "reorder_level" in df.columns:
        low = low_stock_item_count(df)
        if low == 0:
            insights.append("No items are at or below their reorder level.")
        else:
            insights.append(
                f"{low} item{' is' if low == 1 else 's are'} currently at or "
                "below their reorder level."
            )

    if total_value > 0 and len(by_value) > 3:
        top_three = by_value.head(3)["value"].sum() / total_value * 100
        insights.append(
            f"The top three categories account for {top_three:.0f}% of total "
            "inventory value."
        )

    return insights
