"""Tests for reviewable cleaning recommendations."""

import unittest

import pandas as pd

from backend.insights import generate_insights
from backend.recommendations import (
    CleaningChoices,
    build_recommendations,
    clean_with_choices,
    suggest_category_corrections,
)
from backend.transformation import calculate_kpis, sales_by_time_period


def messy_df() -> pd.DataFrame:
    """Two duplicates, one missing amount, and one invalid date."""
    return pd.DataFrame(
        {
            "date": [
                "2024-01-01",
                "2024-01-01",
                "2024-01-02",
                "not-a-date",
                "2024-01-04",
            ],
            "amount": ["$10.00", "$10.00", None, "20", "30"],
            "category": ["Food", "Food", "Books", "Food", "Books"],
            "item": ["Coffee", "Coffee", "Novel", "Tea", "Pen"],
        }
    )


class RecommendationTests(unittest.TestCase):
    def test_builds_one_recommendation_per_issue(self) -> None:
        recs = {r.key: r for r in build_recommendations(messy_df())}

        self.assertEqual(set(recs), {"duplicates", "missing_amounts", "invalid_dates"})
        self.assertEqual(recs["duplicates"].count, 1)
        self.assertEqual(recs["duplicates"].impact, "5 rows → 4 rows")
        self.assertEqual(recs["missing_amounts"].count, 1)
        self.assertEqual(recs["invalid_dates"].count, 1)

    def test_previews_show_rows_and_raw_values(self) -> None:
        recs = {r.key: r for r in build_recommendations(messy_df())}

        self.assertEqual(recs["duplicates"].preview, "Rows 2")
        self.assertEqual(recs["missing_amounts"].preview, "Rows 3")
        self.assertEqual(recs["invalid_dates"].preview, "row 4: 'not-a-date'")

    def test_preview_is_limited_with_remaining_count(self) -> None:
        df = pd.DataFrame(
            {
                "date": ["bad"] * 7,
                "amount": [1] * 7,
                "category": ["Food"] * 7,
                "item": ["Tea"] * 7,
            }
        )
        recs = {r.key: r for r in build_recommendations(df)}

        self.assertTrue(recs["invalid_dates"].preview.endswith("and 2 more"))
        self.assertEqual(recs["duplicates"].preview, "Rows 2, 3, 4, 5, 6; and 1 more")

    def test_suggests_corrections_for_misspelled_categories(self) -> None:
        df = pd.read_csv("data/sales/sales_misspelled_categories_20.csv")
        found = {c.original: c.suggestion for c in suggest_category_corrections(df)}

        self.assertEqual(
            found,
            {
                "Electonics": "Electronics",
                "Clothng": "Clothing",
                "Fodd": "Food",
            },
        )

    def test_no_category_suggestions_for_case_or_legitimate_rare_labels(self) -> None:
        df = pd.DataFrame(
            {
                "category": ["Food", "food ", " FOOD", "Books", "Books", "Toys"],
            }
        )
        self.assertEqual(suggest_category_corrections(df), [])

    def test_accepted_corrections_are_applied_and_rejected_are_not(self) -> None:
        raw = pd.read_csv("data/sales/sales_misspelled_categories_20.csv")

        accepted, summary = clean_with_choices(
            raw,
            CleaningChoices(category_corrections={"Electonics": "Electronics"}),
        )
        self.assertNotIn("Electonics", set(accepted["category"]))
        self.assertIn("Clothng", set(accepted["category"]))
        self.assertEqual(summary["categories_corrected"], 1)

        rejected, summary = clean_with_choices(raw, CleaningChoices())
        self.assertIn("Electonics", set(rejected["category"]))
        self.assertEqual(summary["categories_corrected"], 0)

    def test_invalid_date_examples_list_raw_values_with_rows(self) -> None:
        recs = {r.key: r for r in build_recommendations(messy_df())}

        self.assertEqual(recs["invalid_dates"].examples, ("not-a-date (row 4)",))

    def test_clean_data_has_no_recommendations(self) -> None:
        df = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "amount": [5],
                "category": ["Food"],
                "item": ["Tea"],
            }
        )
        self.assertEqual(build_recommendations(df), [])

    def test_accepting_defaults_matches_previous_behavior(self) -> None:
        df, summary = clean_with_choices(messy_df(), CleaningChoices())

        self.assertEqual(len(df), 4)
        self.assertEqual(summary["duplicates_removed"], 1)
        self.assertTrue(df["amount"].notna().all())
        self.assertEqual(summary["date_rows_removed"], 0)
        self.assertEqual(int(df["date"].isna().sum()), 1)

    def test_rejecting_duplicate_removal_keeps_rows(self) -> None:
        df, summary = clean_with_choices(
            messy_df(), CleaningChoices(remove_duplicates=False)
        )

        self.assertEqual(len(df), 5)
        self.assertEqual(summary["duplicates_removed"], 0)

    def test_rejecting_amount_fill_leaves_amount_empty(self) -> None:
        raw = messy_df()
        df, summary = clean_with_choices(
            raw, CleaningChoices(fill_missing_amounts=False)
        )

        self.assertEqual(int(df["amount"].isna().sum()), 1)
        self.assertEqual(summary["missing_amounts_left"], 1)
        self.assertEqual(summary["missing_cells_filled"], 0)
        self.assertEqual(raw["amount"].isna().sum(), 1)

        calculate_kpis(df)
        sales_by_time_period(df)
        generate_insights(df)

    def test_removing_invalid_date_rows_drops_them(self) -> None:
        df, summary = clean_with_choices(
            messy_df(), CleaningChoices(remove_invalid_date_rows=True)
        )

        self.assertEqual(len(df), 3)
        self.assertTrue(df["date"].notna().all())
        self.assertEqual(summary["date_rows_removed"], 1)

    def test_input_is_not_modified(self) -> None:
        raw = messy_df()
        clean_with_choices(raw, CleaningChoices())
        pd.testing.assert_frame_equal(raw, messy_df())


if __name__ == "__main__":
    unittest.main()
