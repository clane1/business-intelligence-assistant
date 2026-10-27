"""Turn validation findings into fixes the user can accept or reject."""

from dataclasses import dataclass, field
from difflib import SequenceMatcher

import pandas as pd

from backend.cleaning import (
    clean_dates,
    clean_duplicates,
    clean_missing,
    clean_types,
    normalize_categories,
)
from backend.validation import (
    count_currency_values,
    count_duplicates,
    count_invalid_dates,
    count_missing_amounts,
    invalid_date_mask,
)

REQUIRED_COLUMNS = ["date", "amount", "category", "item"]


@dataclass(frozen=True)
class Recommendation:
    """A detected issue with its suggested fix and the effect of applying it."""

    key: str
    title: str
    suggested_fix: str
    impact: str
    count: int
    preview: str = ""
    examples: tuple[str, ...] = ()


@dataclass(frozen=True)
class CleaningChoices:
    """The fixes the user accepted. Defaults match the suggested fixes."""

    remove_duplicates: bool = True
    fill_missing_amounts: bool = True
    remove_invalid_date_rows: bool = False
    # Maps a normalized (title-case) category to the spelling the user accepted.
    category_corrections: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CategoryCorrection:
    """A likely misspelled category and the more common spelling it resembles."""

    original: str
    suggestion: str
    count: int
    preview: str


SIMILARITY_THRESHOLD = 0.75


def _normalized_categories(df: pd.DataFrame) -> pd.Series:
    """Normalize category text the way cleaning does, keeping row alignment."""
    return (
        df["category"].fillna("").astype(str).str.strip().str.casefold().str.title()
    )


def suggest_category_corrections(df: pd.DataFrame) -> list[CategoryCorrection]:
    """Suggest fixes for category labels that look like typos of common ones.

    A label is only flagged when it is rarer than a very similar label, so
    legitimate but uncommon categories are not merged. Differences in case or
    surrounding spaces are not flagged; cleaning already handles those.
    """
    if "category" not in df.columns:
        return []

    normalized = _normalized_categories(df)
    normalized = normalized[
        normalized.ne("") & normalized.ne("Category")
    ]
    counts = normalized.value_counts()

    corrections = []
    for label, count in counts.items():
        candidates = [
            (SequenceMatcher(None, label.casefold(), other.casefold()).ratio(), other)
            for other, other_count in counts.items()
            if other != label and other_count > count
        ]
        candidates = [c for c in candidates if c[0] >= SIMILARITY_THRESHOLD]
        if not candidates:
            continue

        _, suggestion = max(candidates)
        mask = _normalized_categories(df).eq(label)
        corrections.append(CategoryCorrection(
            original=label,
            suggestion=suggestion,
            count=int(count),
            preview=_preview(df, mask, "category"),
        ))

    return corrections


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def _examples(
    df: pd.DataFrame,
    mask: pd.Series,
    column: str,
    limit: int = 5,
) -> tuple[str, ...]:
    """List up to ``limit`` flagged raw values with their one-based row numbers."""
    positions = [i for i, flagged in enumerate(mask) if flagged]
    examples = []
    for i in positions[:limit]:
        value = df.iloc[i][column]
        shown = "(blank)" if pd.isna(value) else str(value)
        examples.append(f"{shown} (row {i + 1})")
    if len(positions) > limit:
        examples.append(f"and {len(positions) - limit} more")
    return tuple(examples)


def _preview(
    df: pd.DataFrame,
    mask: pd.Series,
    column: str | None = None,
    limit: int = 5,
) -> str:
    """Describe up to ``limit`` flagged rows using one-based CSV data-row numbers.

    With ``column``, each row shows its raw value (e.g. ``row 4: 'not-a-date'``);
    otherwise only row numbers are listed (e.g. ``Rows 18, 43, 92``).
    """
    positions = [i for i, flagged in enumerate(mask) if flagged]
    shown = positions[:limit]

    if column is None:
        text = "Rows " + ", ".join(str(i + 1) for i in shown)
    else:
        parts = []
        for i in shown:
            value = df.iloc[i][column]
            parts.append(
                f"row {i + 1}: {'(blank)' if pd.isna(value) else repr(value)}"
            )
        text = "; ".join(parts)

    if len(positions) > limit:
        text += f"; and {len(positions) - limit} more"
    return text


def build_recommendations(df: pd.DataFrame) -> list[Recommendation]:
    """Return one recommendation per issue found in ``df``.

    Issues that are not present produce no recommendation. The DataFrame is
    not modified. Date and amount checks are skipped when the column is absent.
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

    missing_amounts = count_missing_amounts(df)
    if missing_amounts:
        recommendations.append(Recommendation(
            key="missing_amounts",
            title=f"{_plural(missing_amounts, 'missing amount')} found",
            suggested_fix="Replace missing amounts with 0",
            impact=(
                "Affects KPI calculations. If left empty, these sales are "
                "ignored in totals and averages."
            ),
            count=missing_amounts,
            preview=_preview(df, df["amount"].isna()),
        ))

    if "date" in df.columns:
        invalid_dates = count_invalid_dates(df)
        if invalid_dates:
            recommendations.append(Recommendation(
                key="invalid_dates",
                title=f"{_plural(invalid_dates, 'invalid date')} found",
                suggested_fix=(
                    "Keep sales values but exclude from trend analysis"
                ),
                impact=(
                    "Kept rows still count in totals but not in the sales "
                    "trend. Removing the rows also removes their sales from "
                    "totals."
                ),
                count=invalid_dates,
                preview=_preview(df, invalid_date_mask(df), "date"),
                examples=_examples(df, invalid_date_mask(df), "date"),
            ))

    return recommendations


def clean_with_choices(
    df: pd.DataFrame,
    choices: CleaningChoices,
) -> tuple[pd.DataFrame, dict]:
    """Clean ``df`` applying only the fixes the user accepted.

    Always applied: filling empty text fields, converting currency-formatted
    amounts, parsing dates, and normalizing categories. ``df`` is not modified.

    Returns:
        The cleaned DataFrame and a summary dictionary of what changed.
    """
    df = df.copy()
    rows_before = len(df)
    invalid_dates = count_invalid_dates(df)
    duplicates_found = count_duplicates(df)

    date_rows_removed = 0
    if choices.remove_invalid_date_rows and invalid_dates:
        df = df[~invalid_date_mask(df)].copy()
        date_rows_removed = invalid_dates

    missing_amounts = count_missing_amounts(df)
    currency_values = count_currency_values(df)
    missing_cells = int(df[REQUIRED_COLUMNS].isna().sum().sum())

    raw_amounts = df["amount"].copy()
    df = clean_missing(df)
    if not choices.fill_missing_amounts:
        df["amount"] = raw_amounts
    df = clean_types(df)
    df = clean_dates(df, ["date"])

    rows_before_dedup = len(df)
    if choices.remove_duplicates:
        df = clean_duplicates(df)
    duplicates_removed = rows_before_dedup - len(df)

    rows_before_category = len(df)
    df = normalize_categories(df, "category")
    rows_after_category = len(df)

    corrections = choices.category_corrections
    categories_corrected = int(df["category"].isin(corrections).sum())
    category_corrections_applied = [
        {
            "original": original,
            "suggestion": suggestion,
            "rows": int(df["category"].eq(original).sum()),
        }
        for original, suggestion in corrections.items()
    ]
    if corrections:
        df = df.assign(category=df["category"].replace(corrections))

    summary = {
        "rows_before": rows_before,
        "rows_after": len(df),
        "duplicates_removed": duplicates_removed,
        "category_rows_removed": rows_before_category - rows_after_category,
        "categories_corrected": categories_corrected,
        "missing_cells_filled": (
            missing_cells
            - (0 if choices.fill_missing_amounts else missing_amounts)
        ),
        "missing_amounts_left": (
            0 if choices.fill_missing_amounts else missing_amounts
        ),
        "missing_amounts_found": missing_amounts,
        "missing_amounts_filled": (
            missing_amounts if choices.fill_missing_amounts else 0
        ),
        "duplicates_found": duplicates_found,
        "currency_values_converted": currency_values,
        "category_corrections": category_corrections_applied,
        "invalid_dates": invalid_dates,
        "date_rows_removed": date_rows_removed,
    }
    return df, summary
