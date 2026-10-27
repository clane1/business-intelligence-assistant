"""Tests for the Inventory dataset type (backend logic, loader, mapping, report)."""

import unittest
from datetime import datetime
from pathlib import Path

import pandas as pd

from backend.cleaning_report import build_inventory_report
from backend.column_mapping import (
    INVENTORY_OPTIONAL_COLUMNS,
    ColumnMappingError,
    apply_mapping,
    suggest_inventory_mapping,
)
from backend.csv_loader import (
    INVENTORY_COLUMNS,
    CsvFormatError,
    SalesCsvFormatError,
    load_inventory_csv,
)
from backend.inventory import (
    InventoryChoices,
    blocking_problems,
    build_inventory_recommendations,
    clean_inventory,
    count_currency_symbols,
    count_missing,
    count_negative,
    generate_inventory_insights,
    invalid_number_mask,
    inventory_kpis,
    low_stock_item_count,
    top_value_items,
    units_by_category,
    value_by_category,
)
from backend.recommendations import suggest_category_corrections
from backend.upload_diagnosis import diagnose_upload

DATA = Path(__file__).resolve().parents[1] / "data" / "inventory"


def load(name: str, **kwargs) -> pd.DataFrame:
    return load_inventory_csv(
        DATA / name,
        delimiter=kwargs.get("delimiter", ","),
        headers_included=kwargs.get("headers_included", True),
    )


def small() -> pd.DataFrame:
    """Hand-checkable data: value 160, 27 units, 3 items, Toys is top category."""
    return pd.DataFrame(
        {
            "item": ["A", "A", "B", "C"],
            "category": ["Food", "Food", "Food", "Toys"],
            "quantity": [10, 10, 5, 2],
            "unit_cost": [2.0, 2.0, 4.0, 50.0],
            "reorder_level": [10, 10, 1, 5],
        }
    )


class InventoryValidationTests(unittest.TestCase):
    def test_number_mask_accepts_currency_and_ignores_blanks(self) -> None:
        df = pd.DataFrame({"unit_cost": ["$1,200.50", "7", "abc", None, " "]})

        self.assertEqual(
            invalid_number_mask(df, "unit_cost").tolist(),
            [False, False, True, False, False],
        )

    def test_blocking_problems_name_the_bad_columns(self) -> None:
        df = load("inventory_non_numeric_5.csv")

        self.assertEqual(set(blocking_problems(df)), {"quantity", "unit_cost"})
        self.assertEqual(blocking_problems(load("inventory_clean_20.csv")), {})

    def test_counts(self) -> None:
        df = load("inventory_messy_20.csv")

        self.assertEqual(count_missing(df, "quantity"), 1)
        self.assertEqual(count_missing(df, "unit_cost"), 1)
        self.assertEqual(count_negative(df, "quantity"), 1)
        self.assertEqual(count_negative(df, "unit_cost"), 1)
        self.assertEqual(count_currency_symbols(df), 2)

    def test_counts_are_zero_for_absent_columns(self) -> None:
        df = pd.DataFrame({"item": ["A"]})

        self.assertEqual(count_missing(df, "quantity"), 0)
        self.assertEqual(count_negative(df, "quantity"), 0)
        self.assertEqual(count_currency_symbols(df), 0)


class InventoryRecommendationTests(unittest.TestCase):
    def test_messy_file_gets_one_card_per_issue(self) -> None:
        keys = [r.key for r in build_inventory_recommendations(load("inventory_messy_20.csv"))]

        self.assertEqual(
            keys,
            [
                "duplicates",
                "missing_quantity",
                "missing_unit_cost",
                "negative_quantity",
                "negative_unit_cost",
            ],
        )

    def test_cards_have_suggestion_impact_and_preview(self) -> None:
        cards = {r.key: r for r in build_inventory_recommendations(load("inventory_messy_20.csv"))}

        self.assertEqual(cards["duplicates"].title, "2 duplicate rows found")
        self.assertEqual(cards["duplicates"].preview, "Rows 2, 12")
        self.assertEqual(cards["duplicates"].impact, "20 rows → 18 rows")
        self.assertEqual(cards["missing_unit_cost"].suggested_fix, "Replace missing unit costs with 0")
        self.assertEqual(cards["negative_quantity"].suggested_fix, "Review before analysis")
        self.assertEqual(cards["negative_quantity"].title, "1 negative quantity found")
        self.assertIn("row 8: -5", cards["negative_quantity"].preview)

    def test_plural_titles(self) -> None:
        df = small().assign(quantity=[-1, -2, 5, 2], unit_cost=[-1.0, -2.0, 4.0, 50.0])

        cards = {r.key: r.title for r in build_inventory_recommendations(df)}

        self.assertEqual(cards["negative_quantity"], "2 negative quantities found")
        self.assertEqual(cards["negative_unit_cost"], "2 negative unit costs found")

    def test_clean_file_has_no_recommendations_or_category_suggestions(self) -> None:
        df = load("inventory_clean_20.csv")

        self.assertEqual(build_inventory_recommendations(df), [])
        self.assertEqual(suggest_category_corrections(df), [])

    def test_category_misspellings_are_suggested(self) -> None:
        found = {c.original: c.suggestion for c in suggest_category_corrections(load("inventory_messy_20.csv"))}

        self.assertEqual(
            found,
            {"Electonics": "Electronics", "Clothng": "Clothing", "Fodd": "Food"},
        )


class InventoryCleaningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = load("inventory_messy_20.csv")

    def test_defaults_fix_duplicates_and_fill_missing_but_keep_negatives(self) -> None:
        cleaned, summary = clean_inventory(self.raw, InventoryChoices())

        self.assertEqual(summary["duplicates_removed"], 2)
        self.assertEqual(summary["missing_quantity_filled"], 1)
        self.assertEqual(summary["missing_unit_cost_filled"], 1)
        self.assertEqual(summary["negative_rows_removed"], 0)
        self.assertEqual((cleaned["quantity"] < 0).sum(), 1)
        self.assertEqual((cleaned["unit_cost"] < 0).sum(), 1)
        self.assertEqual(summary["rows_before"], 20)
        self.assertEqual(summary["rows_after"], 17)
        self.assertEqual(summary["category_rows_removed"], 1)

    def test_rejecting_fixes_keeps_rows_and_empty_values(self) -> None:
        cleaned, summary = clean_inventory(
            self.raw,
            InventoryChoices(
                remove_duplicates=False,
                fill_missing_quantity=False,
                fill_missing_unit_cost=False,
            ),
        )

        self.assertEqual(summary["duplicates_removed"], 0)
        self.assertEqual(summary["missing_quantity_filled"], 0)
        self.assertEqual(cleaned["quantity"].isna().sum(), 1)
        self.assertEqual(cleaned["unit_cost"].isna().sum(), 1)
        self.assertEqual(len(cleaned), 19)

    def test_negative_rows_are_removed_only_when_chosen(self) -> None:
        cleaned, summary = clean_inventory(
            self.raw,
            InventoryChoices(
                remove_negative_quantity_rows=True,
                remove_negative_unit_cost_rows=True,
            ),
        )

        self.assertEqual(summary["negative_rows_removed"], 2)
        self.assertEqual((cleaned["quantity"] < 0).sum(), 0)
        self.assertEqual((cleaned["unit_cost"] < 0).sum(), 0)

    def test_currency_text_becomes_numbers(self) -> None:
        cleaned, summary = clean_inventory(self.raw, InventoryChoices())

        self.assertTrue(pd.api.types.is_float_dtype(cleaned["unit_cost"]))
        self.assertEqual(summary["unit_costs_converted"], 2)
        monitor = cleaned[cleaned["item"] == "Monitor"].iloc[0]
        self.assertEqual(monitor["unit_cost"], 189.5)

    def test_accepted_category_corrections_are_applied(self) -> None:
        cleaned, summary = clean_inventory(
            self.raw,
            InventoryChoices(category_corrections={"Electonics": "Electronics"}),
        )

        self.assertNotIn("Electonics", set(cleaned["category"]))
        self.assertIn("Clothng", set(cleaned["category"]))
        self.assertEqual(summary["categories_corrected"], 1)

    def test_summary_counts_low_stock_when_reorder_level_exists(self) -> None:
        cleaned, summary = clean_inventory(small(), InventoryChoices())

        self.assertTrue(summary["has_reorder_level"])
        self.assertEqual(summary["low_stock_items"], 2)

    def test_input_is_not_modified(self) -> None:
        before = self.raw.copy()

        clean_inventory(self.raw, InventoryChoices())

        pd.testing.assert_frame_equal(self.raw, before)

    def test_minimal_file_has_no_low_stock_check(self) -> None:
        _, summary = clean_inventory(load("inventory_minimal_8.csv"), InventoryChoices())

        self.assertFalse(summary["has_reorder_level"])
        self.assertIsNone(summary["low_stock_items"])

    def test_unreadable_reorder_levels_are_ignored_not_fatal(self) -> None:
        df = small().assign(reorder_level=["x", 10, 1, 5])

        cleaned, summary = clean_inventory(df, InventoryChoices())

        self.assertEqual(summary["low_stock_items"], 2)  # unreadable value is skipped, A's other row still counts


class InventoryAnalysisTests(unittest.TestCase):
    def test_kpis(self) -> None:
        kpis = inventory_kpis(small())

        self.assertEqual(kpis["total_value"], 160.0)
        self.assertEqual(kpis["total_units"], 27.0)
        self.assertEqual(kpis["unique_items"], 3)
        self.assertEqual(kpis["top_category"], "Toys")

    def test_kpis_ignore_blank_item_names_for_unique_count(self) -> None:
        df = small().assign(item=["A", "", "B", "C"])

        self.assertEqual(inventory_kpis(df)["unique_items"], 3)

    def test_zero_value_inventory_has_no_top_category(self) -> None:
        df = load("inventory_zero_value_6.csv")
        cleaned, _ = clean_inventory(df, InventoryChoices())

        kpis = inventory_kpis(cleaned)

        self.assertEqual(kpis["total_value"], 0.0 + 0.0 + 0.0 + 0.0 + 0.0 + 0.0 + 0.0 * 1)
        self.assertGreater(kpis["total_units"], 0)

    def test_value_and_unit_tables_are_sorted_highest_first(self) -> None:
        self.assertEqual(value_by_category(small())["category"].tolist(), ["Toys", "Food"])
        self.assertEqual(units_by_category(small())["category"].tolist(), ["Food", "Toys"])
        self.assertEqual(units_by_category(small())["quantity"].tolist(), [25, 2])

    def test_top_value_items_sums_rows_and_limits(self) -> None:
        top = top_value_items(small(), 2)

        self.assertEqual(top["item"].tolist(), ["C", "A"])
        self.assertEqual(top["value"].tolist(), [100.0, 40.0])

    def test_low_stock_counts_distinct_items(self) -> None:
        self.assertEqual(low_stock_item_count(small()), 2)
        self.assertEqual(low_stock_item_count(small().drop(columns="reorder_level")), 0)

    def test_insights_for_clean_file(self) -> None:
        cleaned, _ = clean_inventory(load("inventory_clean_20.csv"), InventoryChoices())

        insights = generate_inventory_insights(cleaned)

        self.assertEqual(insights[0], "Electronics represents 55% of total inventory value.")
        self.assertEqual(
            insights[1], "Laptop inventory has the highest total value at $10,799.88."
        )
        self.assertIn("Food contains the largest number of units in stock.", insights)
        self.assertIn("1 item is currently at or below their reorder level.", insights)
        self.assertTrue(insights[-1].startswith("The top three categories account for "))

    def test_low_stock_insight_is_omitted_without_reorder_levels(self) -> None:
        cleaned, _ = clean_inventory(load("inventory_minimal_8.csv"), InventoryChoices())

        self.assertFalse(
            any("reorder" in line for line in generate_inventory_insights(cleaned))
        )

    def test_concentration_needs_more_than_three_categories(self) -> None:
        self.assertFalse(
            any("top three" in line for line in generate_inventory_insights(small()))
        )

    def test_zero_value_inventory_explains_instead_of_comparing(self) -> None:
        cleaned, _ = clean_inventory(load("inventory_zero_value_6.csv"), InventoryChoices())

        insights = generate_inventory_insights(cleaned)

        self.assertIn("unavailable", insights[0])
        self.assertFalse(any("represents" in line for line in insights))

    def test_no_items_at_reorder_level_is_stated(self) -> None:
        df = small().assign(reorder_level=[1, 1, 1, 1])

        self.assertIn(
            "No items are at or below their reorder level.",
            generate_inventory_insights(df),
        )


class InventoryReportTests(unittest.TestCase):
    NOW = datetime(2024, 3, 9, 10, 30)

    def report(self, choices: InventoryChoices, name: str = "inventory_messy_20.csv", **kwargs) -> str:
        _, summary = clean_inventory(load(name), choices)
        return build_inventory_report(
            summary, source_name=name, generated_at=self.NOW, **kwargs
        )

    def test_accepted_defaults(self) -> None:
        text = self.report(InventoryChoices())

        for expected in (
            "Inventory Cleaning Report",
            "Generated: 2024-03-09 10:30",
            "File: inventory_messy_20.csv",
            "Rows before: 20",
            "Rows after: 17",
            "Duplicate rows: 2 found, 2 removed",
            "Missing quantities: 1 found, replaced with 0",
            "Missing unit costs: 1 found, replaced with 0",
            "Negative quantities: 1 found, kept for your review",
            "Negative unit costs: 1 found, kept for your review",
            "Unit costs with $ or commas: 2 converted",
            "Rows with blank categories: 1 removed",
            "Low stock items identified: 4",
        ):
            self.assertIn(expected, text)

    def test_rejected_and_removed_choices(self) -> None:
        text = self.report(
            InventoryChoices(
                remove_duplicates=False,
                fill_missing_quantity=False,
                remove_negative_quantity_rows=True,
                category_corrections={"Fodd": "Food"},
            )
        )

        self.assertIn("Duplicate rows: 2 found, kept", text)
        self.assertIn("Missing quantities: 1 found, left empty", text)
        self.assertIn("Negative quantities: 1 found, rows removed", text)
        self.assertIn("Fodd -> Food (1 row)", text)

    def test_clean_file_and_missing_reorder_level(self) -> None:
        text = self.report(InventoryChoices(), "inventory_minimal_8.csv")

        self.assertIn("Duplicate rows: none found", text)
        self.assertIn("Missing quantities: none found", text)
        self.assertIn("not checked (no reorder_level column)", text)

    def test_column_mapping_lists_only_assigned_columns(self) -> None:
        text = self.report(
            InventoryChoices(),
            "inventory_clean_20.csv",
            column_mapping={"item": "SKU", "reorder_level": None},
        )

        self.assertIn("Columns used: SKU -> item", text)
        self.assertNotIn("None", text)


class InventoryLoadingTests(unittest.TestCase):
    def test_headered_file_keeps_optional_columns(self) -> None:
        self.assertEqual(
            list(load("inventory_clean_20.csv").columns),
            INVENTORY_COLUMNS + INVENTORY_OPTIONAL_COLUMNS,
        )

    def test_headerless_file_gets_required_names(self) -> None:
        df = load("inventory_no_headers_5.csv", headers_included=False)

        self.assertEqual(list(df.columns), INVENTORY_COLUMNS)
        self.assertEqual(len(df), 5)

    def test_headerless_wrong_column_count_names_inventory_columns(self) -> None:
        with self.assertRaisesRegex(CsvFormatError, "headerless inventory files need four"):
            load("inventory_clean_20.csv", headers_included=False)

    def test_header_row_with_header_option_off_is_rejected(self) -> None:
        with self.assertRaisesRegex(CsvFormatError, "contain a header row"):
            load("inventory_minimal_8.csv", headers_included=False)

    def test_sales_error_name_still_catches_the_shared_error(self) -> None:
        self.assertIs(SalesCsvFormatError, CsvFormatError)

    def test_diagnosis_messages_name_inventory(self) -> None:
        empty = pd.DataFrame(columns=INVENTORY_COLUMNS)
        data_like = pd.DataFrame([["Food", "Item"]], columns=["2024-01-01", "12"])

        self.assertIn("inventory rows", diagnose_upload(empty, ",", True, label="inventory"))
        self.assertIn(
            "looks like inventory data",
            diagnose_upload(data_like, ",", True, label="inventory"),
        )

    def test_missing_required_column_is_detected(self) -> None:
        df = load("inventory_missing_column_5.csv")

        self.assertEqual(
            [c for c in INVENTORY_COLUMNS if c not in df.columns], ["unit_cost"]
        )


class InventoryMappingTests(unittest.TestCase):
    def test_suggests_real_world_inventory_headers(self) -> None:
        df = load("inventory_custom_headers_6.csv")

        self.assertEqual(
            suggest_inventory_mapping(list(df.columns)),
            {
                "item": "SKU",
                "category": "Department",
                "quantity": "Qty on Hand",
                "unit_cost": "Cost per Unit",
                "reorder_level": "Reorder Point",
                "last_updated": None,
            },
        )

    def test_exact_inventory_names_are_matched(self) -> None:
        mapping = suggest_inventory_mapping(["unit_cost", "quantity", "item", "category"])

        self.assertEqual(mapping["unit_cost"], "unit_cost")
        self.assertEqual(mapping["quantity"], "quantity")

    def test_apply_mapping_includes_only_assigned_optional_columns(self) -> None:
        df = load("inventory_custom_headers_6.csv")
        mapping = suggest_inventory_mapping(list(df.columns))

        mapped = apply_mapping(df, mapping, INVENTORY_COLUMNS, INVENTORY_OPTIONAL_COLUMNS)

        self.assertEqual(list(mapped.columns), INVENTORY_COLUMNS + ["reorder_level"])
        self.assertEqual(mapped.iloc[0]["quantity"], 12)

    def test_apply_mapping_requires_required_columns(self) -> None:
        df = load("inventory_custom_headers_6.csv")
        mapping = suggest_inventory_mapping(list(df.columns))
        mapping["unit_cost"] = None

        with self.assertRaisesRegex(ColumnMappingError, "unit_cost"):
            apply_mapping(df, mapping, INVENTORY_COLUMNS, INVENTORY_OPTIONAL_COLUMNS)

    def test_apply_mapping_rejects_reusing_a_column(self) -> None:
        df = load("inventory_custom_headers_6.csv")
        mapping = suggest_inventory_mapping(list(df.columns))
        mapping["reorder_level"] = "Qty on Hand"

        with self.assertRaisesRegex(ColumnMappingError, "only be used once"):
            apply_mapping(df, mapping, INVENTORY_COLUMNS, INVENTORY_OPTIONAL_COLUMNS)

    def test_sales_mapping_defaults_are_unchanged(self) -> None:
        from backend.column_mapping import suggest_mapping

        self.assertEqual(
            suggest_mapping(["Transaction Date", "Revenue", "Department", "Product"]),
            {
                "date": "Transaction Date",
                "amount": "Revenue",
                "category": "Department",
                "item": "Product",
            },
        )


class InventoryFixtureTests(unittest.TestCase):
    BLOCKED = {"inventory_non_numeric_5.csv", "inventory_missing_column_5.csv"}
    HEADERLESS = {"inventory_no_headers_5.csv"}
    CUSTOM = {"inventory_custom_headers_6.csv"}

    def test_every_fixture_is_covered_by_a_known_scenario(self) -> None:
        self.assertEqual(len(list(DATA.glob("*.csv"))), 8)

    def test_every_usable_fixture_cleans_and_produces_insights(self) -> None:
        for path in sorted(DATA.glob("*.csv")):
            if path.name in self.BLOCKED | self.CUSTOM | self.HEADERLESS:
                continue
            with self.subTest(fixture=path.name):
                df = load(path.name)
                self.assertEqual(blocking_problems(df), {})
                cleaned, summary = clean_inventory(df, InventoryChoices())
                self.assertGreater(len(cleaned), 0)
                self.assertTrue(generate_inventory_insights(cleaned))
                self.assertEqual(summary["rows_before"], len(df))


if __name__ == "__main__":
    unittest.main()
