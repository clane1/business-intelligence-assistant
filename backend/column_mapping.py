"""Match a file's own column names to the sales columns the app requires."""

import re
from difflib import SequenceMatcher

import pandas as pd

from backend.csv_loader import SALES_COLUMNS

# Normalized names (lowercase letters and digits only) commonly used for each
# required column.
COLUMN_ALIASES = {
    "date": {
        "date", "transactiondate", "saledate", "orderdate", "purchasedate",
        "invoicedate", "timestamp", "day",
    },
    "amount": {
        "amount", "revenue", "sales", "salesamount", "totalsales", "total",
        "totalprice", "price", "value", "saleamount",
    },
    "category": {
        "category", "department", "productcategory", "producttype", "type",
        "segment", "group",
    },
    "item": {
        "item", "product", "productname", "itemname", "description", "sku",
    },
}

SIMILARITY_THRESHOLD = 0.75


class ColumnMappingError(ValueError):
    """Raised when a chosen column mapping cannot be applied."""


def _normalize(name: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).casefold())


def suggest_mapping(columns: list) -> dict[str, str | None]:
    """Suggest which file column provides each required sales column.

    Exact names win, then known aliases (for example ``Revenue`` for
    ``amount``), then close spellings. Each file column is suggested at most
    once. Required columns with no plausible match map to ``None``.
    """
    sources = {_normalize(column): column for column in columns}
    suggestion: dict[str, str | None] = {target: None for target in SALES_COLUMNS}
    used: set = set()

    def claim(target: str, normalized: str) -> bool:
        source = sources.get(normalized)
        if source is None or source in used:
            return False
        suggestion[target] = source
        used.add(source)
        return True

    for target in SALES_COLUMNS:
        claim(target, target)

    for target in SALES_COLUMNS:
        if suggestion[target] is None:
            for alias in sorted(COLUMN_ALIASES[target]):
                if claim(target, alias):
                    break

    for target in SALES_COLUMNS:
        if suggestion[target] is not None:
            continue
        best_score, best_source = 0.0, None
        for normalized, source in sources.items():
            if source in used:
                continue
            score = max(
                SequenceMatcher(None, normalized, name).ratio()
                for name in COLUMN_ALIASES[target]
            )
            if score > best_score:
                best_score, best_source = score, source
        if best_source is not None and best_score >= SIMILARITY_THRESHOLD:
            suggestion[target] = best_source
            used.add(best_source)

    return suggestion


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str | None]) -> pd.DataFrame:
    """Return a copy of ``df`` holding only the required columns, renamed.

    Args:
        df: The uploaded data with its original column names.
        mapping: Required column name -> the file column that provides it.

    Raises:
        ColumnMappingError: If a required column is unassigned, a chosen column
            does not exist, or one file column is used for two required columns.
    """
    unassigned = [t for t in SALES_COLUMNS if not mapping.get(t)]
    if unassigned:
        raise ColumnMappingError(
            "Choose a column for: " + ", ".join(unassigned) + ". If your "
            "file doesn't have one, add it to the file and upload it again."
        )

    chosen = [mapping[t] for t in SALES_COLUMNS]
    unknown = [c for c in chosen if c not in df.columns]
    if unknown:
        raise ColumnMappingError(
            "These columns aren't in your file: " + ", ".join(map(str, unknown)) + "."
        )

    repeated = sorted({str(c) for c in chosen if chosen.count(c) > 1})
    if repeated:
        raise ColumnMappingError(
            "Each file column can only be used once. Used more than once: "
            + ", ".join(repeated) + "."
        )

    mapped = df[chosen].copy()
    mapped.columns = SALES_COLUMNS
    return mapped
