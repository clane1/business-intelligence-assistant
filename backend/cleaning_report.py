"""Build a plain-text report describing what cleaning changed."""

from datetime import datetime

_RULE = "=" * 40


def _count(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def _duplicates_line(summary: dict) -> str:
    found = summary.get("duplicates_found", 0)
    removed = summary["duplicates_removed"]
    if removed:
        return f"Duplicate rows: {found} found, {removed} removed"
    if found:
        return f"Duplicate rows: {found} found, kept (removal was not selected)"
    return "Duplicate rows: none found"


def _amounts_line(summary: dict) -> str:
    found = summary.get("missing_amounts_found", 0)
    if not found:
        return "Missing amounts: none found"
    if summary.get("missing_amounts_filled"):
        return f"Missing amounts: {found} found, replaced with 0"
    return (
        f"Missing amounts: {found} found, left empty "
        "(excluded from totals and averages)"
    )


def _dates_line(summary: dict) -> str:
    invalid = summary["invalid_dates"]
    if not invalid:
        return "Invalid dates: none found"
    if summary.get("date_rows_removed"):
        return f"Invalid dates: {invalid} found, rows removed"
    return (
        f"Invalid dates: {invalid} found, kept but excluded from sales "
        "trends and date-based insights (amounts still count in totals)"
    )


def build_cleaning_report(
    summary: dict,
    *,
    source_name: str | None = None,
    column_mapping: dict | None = None,
    generated_at: datetime | None = None,
) -> str:
    """Return the cleaning report text.

    Args:
        summary: The dictionary returned by ``clean_with_choices``.
        source_name: Name of the uploaded file, if known.
        column_mapping: Required column -> file column, when the user matched
            columns; omitted from the report when ``None``.
        generated_at: Report timestamp; defaults to the current time.
    """
    generated_at = generated_at or datetime.now()
    rows_before = summary["rows_before"]
    rows_after = summary["rows_after"]

    lines = [
        "Cleaning Report",
        _RULE,
        f"Generated: {generated_at:%Y-%m-%d %H:%M}",
    ]
    if source_name:
        lines.append(f"File: {source_name}")
    if column_mapping:
        lines.append(
            "Columns used: "
            + ", ".join(f"{source} -> {target}" for target, source in column_mapping.items())
        )

    lines += [
        "",
        "Rows",
        f"  Rows before: {rows_before}",
        f"  Rows after: {rows_after}",
        f"  Rows removed: {rows_before - rows_after}",
        "",
        "What was changed",
        f"  {_duplicates_line(summary)}",
        f"  {_amounts_line(summary)}",
        f"  {_dates_line(summary)}",
    ]

    currency = summary.get("currency_values_converted", 0)
    lines.append(
        f"  Amounts with $ or commas: {currency} converted to plain numbers"
        if currency
        else "  Amounts with $ or commas: none found"
    )

    blank_categories = summary["category_rows_removed"]
    lines.append(
        f"  Rows with blank categories: {blank_categories} removed"
        if blank_categories
        else "  Rows with blank categories: none found"
    )

    corrections = summary.get("category_corrections", [])
    if corrections:
        lines.append("  Category spelling corrections:")
        for correction in corrections:
            lines.append(
                f"    {correction['original']} -> {correction['suggestion']} "
                f"({_count(correction['rows'], 'row')})"
            )
    else:
        lines.append("  Category spelling corrections: none applied")

    lines += [
        "",
        "Always applied: empty text fields filled with blanks, dates parsed, "
        "category capitalization and spacing standardized.",
        "The uploaded file was not modified.",
        "",
    ]
    return "\n".join(lines)
