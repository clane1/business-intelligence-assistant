"""Match a file's own column names to the columns the app requires."""

import re
from difflib import SequenceMatcher

import pandas as pd

from backend.csv_loader import INVENTORY_COLUMNS, SALES_COLUMNS

INVENTORY_OPTIONAL_COLUMNS = ["reorder_level", "last_updated"]

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

INVENTORY_COLUMN_ALIASES = {
    "item": {
        "item", "itemname", "product", "productname", "description", "sku",
        "name", "article",
    },
    "category": {
        "category", "department", "productcategory", "producttype", "type",
        "group", "class",
    },
    "quantity": {
        "quantity", "qty", "units", "stock", "onhand", "quantityonhand",
        "instock", "unitsinstock", "stocklevel", "count",
    },
    "unit_cost": {
        "unitcost", "cost", "unitprice", "price", "costperunit",
        "priceperunit", "purchaseprice",
    },
    "reorder_level": {
        "reorderlevel", "reorderpoint", "minimumstock", "minstock",
        "minlevel", "minimumlevel",
    },
    "last_updated": {
        "lastupdated", "updated", "lastupdate", "dateupdated", "lastcounted",
        "updatedat", "date",
    },
}

SIMILARITY_THRESHOLD = 0.75


class ColumnMappingError(ValueError):
    """Raised when a chosen column mapping cannot be applied."""


def _normalize(name: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).casefold())


def suggest_mapping(
    columns: list,
    targets: list[str] = SALES_COLUMNS,
    aliases: dict[str, set] = COLUMN_ALIASES,
) -> dict[str, str | None]:
    """Suggest which file column provides each target column.

    Exact names win, then known aliases (for example ``Revenue`` for
    ``amount``), then close spellings. Each file column is suggested at most
    once. Targets with no plausible match map to ``None``. Defaults suggest
    the sales columns.
    """
    sources = {_normalize(column): column for column in columns}
    suggestion: dict[str, str | None] = {target: None for target in targets}
    used: set = set()

    def claim(target: str, normalized: str) -> bool:
        source = sources.get(normalized)
        if source is None or source in used:
            return False
        suggestion[target] = source
        used.add(source)
        return True

    for target in targets:
        claim(target, _normalize(target))

    for target in targets:
        if suggestion[target] is None:
            for alias in sorted(aliases[target]):
                if claim(target, alias):
                    break

    for target in targets:
        if suggestion[target] is not None:
            continue
        best_score, best_source = 0.0, None
        for normalized, source in sources.items():
            if source in used:
                continue
            score = max(
                SequenceMatcher(None, normalized, name).ratio()
                for name in aliases[target]
            )
            if score > best_score:
                best_score, best_source = score, source
        if best_source is not None and best_score >= SIMILARITY_THRESHOLD:
            suggestion[target] = best_source
            used.add(best_source)

    return suggestion


def suggest_inventory_mapping(columns: list) -> dict[str, str | None]:
    """Suggest a mapping for the required and optional inventory columns."""
    return suggest_mapping(
        columns,
        INVENTORY_COLUMNS + INVENTORY_OPTIONAL_COLUMNS,
        INVENTORY_COLUMN_ALIASES,
    )


def apply_mapping(
    df: pd.DataFrame,
    mapping: dict[str, str | None],
    required: list[str] = SALES_COLUMNS,
    optional: list[str] = (),
) -> pd.DataFrame:
    """Return a copy of ``df`` holding only the mapped columns, renamed.

    Args:
        df: The uploaded data with its original column names.
        mapping: Target column name -> the file column that provides it.
        required: Targets that must be assigned (sales columns by default).
        optional: Targets that are included only when assigned.

    Raises:
        ColumnMappingError: If a required column is unassigned, a chosen column
            does not exist, or one file column is used for two targets.
    """
    unassigned = [t for t in required if not mapping.get(t)]
    if unassigned:
        raise ColumnMappingError(
            "Choose a column for: " + ", ".join(unassigned) + ". If your "
            "file doesn't have one, add it to the file and upload it again."
        )

    targets = list(required) + [t for t in optional if mapping.get(t)]
    chosen = [mapping[t] for t in targets]
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
    mapped.columns = targets
    return mapped
