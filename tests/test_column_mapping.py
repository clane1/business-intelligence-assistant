"""Tests for matching uploaded column names to the required sales columns."""

import unittest

import pandas as pd

from backend.column_mapping import (
    ColumnMappingError,
    apply_mapping,
    suggest_mapping,
)


class ColumnMappingTests(unittest.TestCase):
    def test_suggests_aliases_for_real_world_headers(self) -> None:
        mapping = suggest_mapping(
            ["Transaction Date", "Revenue", "Department", "Product", "Region"]
        )

        self.assertEqual(
            mapping,
            {
                "date": "Transaction Date",
                "amount": "Revenue",
                "category": "Department",
                "item": "Product",
            },
        )

    def test_ignores_case_spacing_and_punctuation(self) -> None:
        mapping = suggest_mapping(["TransactionDate", "sale_amount", "CATEGORY", "Item "])

        self.assertEqual(mapping["date"], "TransactionDate")
        self.assertEqual(mapping["amount"], "sale_amount")
        self.assertEqual(mapping["category"], "CATEGORY")
        self.assertEqual(mapping["item"], "Item ")

    def test_suggests_close_misspellings(self) -> None:
        mapping = suggest_mapping(["date", "amout", "category", "item"])

        self.assertEqual(mapping["amount"], "amout")

    def test_exact_names_win_over_aliases(self) -> None:
        mapping = suggest_mapping(["date", "amount", "category", "item", "Revenue"])

        self.assertEqual(mapping["amount"], "amount")

    def test_unmatched_columns_are_none_and_never_reused(self) -> None:
        mapping = suggest_mapping(["date", "Revenue"])

        self.assertIsNone(mapping["category"])
        self.assertIsNone(mapping["item"])
        self.assertEqual(
            len([v for v in mapping.values() if v is not None]),
            len({v for v in mapping.values() if v is not None}),
        )

    def test_apply_mapping_renames_orders_and_drops_extras(self) -> None:
        raw = pd.DataFrame(
            {
                "Region": ["N"],
                "Product": ["Mouse"],
                "Revenue": [25.0],
                "Department": ["Electronics"],
                "Transaction Date": ["2024-01-01"],
            }
        )
        mapped = apply_mapping(
            raw,
            {
                "date": "Transaction Date",
                "amount": "Revenue",
                "category": "Department",
                "item": "Product",
            },
        )

        self.assertEqual(list(mapped.columns), ["date", "amount", "category", "item"])
        self.assertEqual(mapped.iloc[0].tolist(), ["2024-01-01", 25.0, "Electronics", "Mouse"])
        self.assertIn("Region", raw.columns)

    def test_apply_mapping_rejects_missing_and_repeated_columns(self) -> None:
        raw = pd.DataFrame({"a": [1], "b": [2]})

        with self.assertRaises(ColumnMappingError):
            apply_mapping(raw, {"date": "a", "amount": "b", "category": None, "item": "a"})
        with self.assertRaises(ColumnMappingError):
            apply_mapping(raw, {"date": "a", "amount": "b", "category": "a", "item": "b"})
        with self.assertRaises(ColumnMappingError):
            apply_mapping(raw, {"date": "a", "amount": "b", "category": "x", "item": "y"})


if __name__ == "__main__":
    unittest.main()
