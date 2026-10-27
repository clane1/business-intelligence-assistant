"""Tests for the validation checks and cleaning primitives."""

import unittest

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
    validate_columns,
    validate_missing,
    validate_types,
)


def frame(**columns) -> pd.DataFrame:
    return pd.DataFrame(columns)


class ValidationTests(unittest.TestCase):
    def test_validate_columns_lists_missing_in_required_order(self) -> None:
        df = frame(date=["2024-01-01"], item=["Pen"])

        self.assertEqual(
            validate_columns(df, ["date", "amount", "category", "item"]),
            ["amount", "category"],
        )

    def test_validate_columns_passes_when_all_present(self) -> None:
        df = frame(date=["x"], amount=[1])

        self.assertEqual(validate_columns(df, ["date", "amount"]), [])

    def test_validate_missing_counts_per_column(self) -> None:
        df = frame(date=["2024-01-01", None], amount=[None, None])

        counts = validate_missing(df)

        self.assertEqual(counts["date"], 1)
        self.assertEqual(counts["amount"], 2)

    def test_validate_types_distinguishes_blocking_from_fixable(self) -> None:
        self.assertEqual(
            validate_types(frame(amount=["10", "abc"])),
            {"amount": "Non-numeric values detected"},
        )
        self.assertEqual(
            validate_types(frame(amount=["$1,000.50", "5"])),
            {"amount": "Currency-formatted values require cleaning"},
        )
        self.assertEqual(validate_types(frame(amount=["1", "2.5"])), {})

    def test_validate_types_ignores_missing_amount_column(self) -> None:
        self.assertEqual(validate_types(frame(date=["2024-01-01"])), {})

    def test_empty_amount_cells_are_not_non_numeric(self) -> None:
        self.assertEqual(validate_types(frame(amount=["5", None, ""])), {})

    def test_count_helpers(self) -> None:
        df = frame(
            date=["2024-01-01", "2024-01-01", "bad", None],
            amount=["$5", "$5", None, "7"],
        )

        self.assertEqual(count_duplicates(df), 1)
        self.assertEqual(count_invalid_dates(df), 2)
        self.assertEqual(count_missing_amounts(df), 1)
        self.assertEqual(count_currency_values(df), 2)

    def test_count_missing_amounts_without_amount_column(self) -> None:
        self.assertEqual(count_missing_amounts(frame(date=["x"])), 0)

    def test_slash_and_day_first_dates_are_valid(self) -> None:
        df = frame(date=["2024/01/31", "31-01-2024", "2024-01-31"])

        self.assertEqual(count_invalid_dates(df), 0)

    def test_impossible_dates_are_invalid(self) -> None:
        df = frame(date=["2024/13/40", "31-02-2024", "not-a-date", ""])

        self.assertEqual(count_invalid_dates(df), 4)


class CleaningTests(unittest.TestCase):
    def test_clean_missing_uses_documented_defaults(self) -> None:
        df = frame(
            date=[None], amount=[None], category=[None], item=[None]
        )

        cleaned = clean_missing(df).iloc[0]

        self.assertEqual(cleaned["date"], "")
        self.assertEqual(cleaned["amount"], 0)
        self.assertEqual(cleaned["category"], "")
        self.assertEqual(cleaned["item"], "")

    def test_clean_types_removes_currency_formatting(self) -> None:
        df = frame(amount=["$1,234.50", " 7 ", "abc"])

        cleaned = clean_types(df)["amount"].tolist()

        self.assertEqual(cleaned[0], 1234.5)
        self.assertEqual(cleaned[1], 7)
        self.assertTrue(pd.isna(cleaned[2]))

    def test_clean_dates_parses_supported_formats(self) -> None:
        df = frame(date=["2024/01/31", "31-01-2024", "2024-01-31", "nope"])

        cleaned = clean_dates(df, ["date"])["date"]

        self.assertEqual(
            cleaned.iloc[:3].tolist(), [pd.Timestamp("2024-01-31")] * 3
        )
        self.assertTrue(pd.isna(cleaned.iloc[3]))

    def test_clean_duplicates_keeps_first_occurrence(self) -> None:
        df = frame(a=[1, 1, 2], b=["x", "x", "y"])

        self.assertEqual(len(clean_duplicates(df)), 2)

    def test_normalize_categories_standardizes_and_drops_blanks(self) -> None:
        df = frame(category=["  food ", "FOOD", "", "category", "Home Goods"])

        cleaned = normalize_categories(df, "category")

        self.assertEqual(cleaned["category"].tolist(), ["Food", "Food", "Home Goods"])


if __name__ == "__main__":
    unittest.main()
