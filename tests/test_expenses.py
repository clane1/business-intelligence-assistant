"""Backend tests for Expenses loading, cleaning, metrics, and insights."""

import unittest
from io import StringIO
from pathlib import Path

import pandas as pd

from backend.cleaning_report import build_expenses_report
from backend.column_mapping import apply_mapping, suggest_expenses_mapping
from backend.csv_loader import (
    EXPENSES_COLUMNS,
    CsvFormatError,
    load_expenses_csv,
)
from backend.expenses import (
    CleaningChoices,
    build_expenses_recommendations,
    clean_expenses,
    expenses_by_category,
    expenses_by_vendor,
    expenses_kpis,
    expense_trend,
    generate_expense_insights,
    spending_by_category,
)
from backend.validation import (
    count_currency_values,
    count_duplicates,
    count_invalid_dates,
    count_missing_amounts,
    invalid_amount_mask,
    validate_columns,
)
from backend.recommendations import suggest_category_corrections
from frontend.charts import (
    build_expenses_trend_chart,
    format_cleaned_preview,
)

DATA = Path(__file__).resolve().parents[1] / "data" / "expenses"


def load(name: str, *, headers_included: bool = True) -> pd.DataFrame:
    """Load a checked-in Expenses CSV fixture."""
    return load_expenses_csv(
        DATA / name,
        delimiter=",",
        headers_included=headers_included,
    )


def small_expenses() -> pd.DataFrame:
    """Return expenses with known monthly, category, and vendor totals."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2024-01-05", "2024-02-05", "2024-03-05", "2024-07-06"]
            ),
            "amount": [50.0, 25.0, 100.0, 25.0],
            "category": [
                "Office Supplies",
                "Travel",
                "Office Supplies",
                "Travel",
            ],
            "vendor": ["Acme", "Northstar", "Acme", "City Transit"],
        }
    )


class ExpensesLoadingTests(unittest.TestCase):
    """Verify Expenses loader behavior and custom header mapping."""

    def test_headered_and_headerless_files_have_expense_schema(self) -> None:
        headered = load("expenses_clean_100.csv")
        headerless = load("expenses_no_headers.csv", headers_included=False)

        self.assertEqual(list(headered.columns), EXPENSES_COLUMNS)
        self.assertEqual(list(headerless.columns), EXPENSES_COLUMNS)
        self.assertEqual(len(headered), 100)
        self.assertEqual(validate_columns(headerless, EXPENSES_COLUMNS), [])

    def test_headerless_file_with_wrong_column_count_is_rejected(self) -> None:
        with self.assertRaisesRegex(CsvFormatError, "headerless expenses files"):
            load_expenses_csv(
                StringIO("2026-01-01,10,Office Supplies\n"),
                delimiter=",",
                headers_included=False,
            )

    def test_custom_expense_headers_are_suggested_and_applied(self) -> None:
        df = load("expenses_custom_headers.csv")
        mapping = suggest_expenses_mapping(list(df.columns))

        self.assertEqual(
            mapping,
            {
                "date": "Transaction Date",
                "amount": "Expense",
                "category": "Department",
                "vendor": "Supplier",
            },
        )
        mapped = apply_mapping(df, mapping, EXPENSES_COLUMNS)

        self.assertEqual(list(mapped.columns), EXPENSES_COLUMNS)
        self.assertEqual(mapped.iloc[0]["vendor"], "Acme Office")

    def test_missing_vendor_is_detected(self) -> None:
        df = load("expenses_missing_column.csv")

        self.assertEqual(validate_columns(df, EXPENSES_COLUMNS), ["vendor"])


class ExpensesCleaningTests(unittest.TestCase):
    """Verify blocking validations and accepted/rejected cleaning choices."""

    def test_amount_validation_distinguishes_empty_from_unreadable(self) -> None:
        df = load("expenses_invalid_amount.csv")

        self.assertEqual(count_missing_amounts(df), 0)
        self.assertEqual(int(invalid_amount_mask(df).sum()), 1)
        self.assertEqual(
            build_expenses_recommendations(df),
            [],
        )

    def test_recommendations_detect_duplicates_and_missing_amounts(self) -> None:
        self.assertEqual(count_duplicates(load("expenses_duplicates.csv")), 1)
        self.assertEqual(count_missing_amounts(load("expenses_missing_amount.csv")), 1)

    def test_messy_fixture_cleans_with_expense_schema_and_report(self) -> None:
        source = load("expenses_messy_100.csv")
        before = source.copy()
        recommendations = build_expenses_recommendations(source)
        cleaned, summary = clean_expenses(source, CleaningChoices())

        invalid_date_recommendation = next(
            r for r in recommendations if r.key == "invalid_dates"
        )
        missing_amount_recommendation = next(
            r for r in recommendations if r.key == "missing_amounts"
        )
        self.assertIn("expense trend", invalid_date_recommendation.impact.lower())
        self.assertIn("expenses", missing_amount_recommendation.impact.lower())
        self.assertEqual(count_duplicates(source), 2)
        self.assertEqual(count_missing_amounts(source), 1)
        self.assertEqual(count_invalid_dates(source), 1)
        self.assertEqual(count_currency_values(source), 2)
        self.assertIn("vendor", cleaned.columns)
        self.assertNotIn("item", cleaned.columns)
        self.assertIn("Office Supllies", cleaned["category"].tolist())
        self.assertFalse(cleaned.duplicated().any())
        self.assertTrue(pd.api.types.is_numeric_dtype(cleaned["amount"]))
        pd.testing.assert_frame_equal(source, before)

        report = build_expenses_report(summary, source_name="messy.csv")
        self.assertIn("Expenses Cleaning Report", report)
        self.assertIn("File: messy.csv", report)
        self.assertIn("excluded from expense trends", report)

    def test_duplicates_can_be_kept_when_removal_is_rejected(self) -> None:
        raw = load("expenses_duplicates.csv")

        cleaned, summary = clean_expenses(
            raw,
            CleaningChoices(remove_duplicates=False),
        )

        self.assertEqual(count_duplicates(cleaned), 1)
        self.assertEqual(summary["duplicates_removed"], 0)

    def test_missing_amount_can_be_left_empty_or_filled(self) -> None:
        raw = load("expenses_missing_amount.csv")
        kept, kept_summary = clean_expenses(
            raw,
            CleaningChoices(fill_missing_amounts=False),
        )
        filled, filled_summary = clean_expenses(raw, CleaningChoices())

        self.assertEqual(kept["amount"].isna().sum(), 1)
        self.assertEqual(kept_summary["missing_amounts_left"], 1)
        self.assertEqual(filled["amount"].isna().sum(), 0)
        self.assertEqual(filled_summary["missing_amounts_filled"], 1)

    def test_invalid_dates_can_be_kept_or_removed(self) -> None:
        raw = pd.DataFrame(
            {
                "date": ["2024-01-01", "not-a-date"],
                "amount": [10, 20],
                "category": ["Office Supplies", "Travel"],
                "vendor": ["A", "B"],
            }
        )
        kept, _ = clean_expenses(raw, CleaningChoices())
        removed, summary = clean_expenses(
            raw,
            CleaningChoices(remove_invalid_date_rows=True),
        )

        self.assertEqual(count_invalid_dates(kept), 1)
        self.assertEqual(kept["amount"].sum(), 30)
        self.assertEqual(len(removed), 1)
        self.assertEqual(summary["date_rows_removed"], 1)


class ExpensesAnalysisTests(unittest.TestCase):
    """Verify expense KPIs, chart tables, and generated insight content."""

    def test_kpis_category_shares_vendor_totals_and_trend(self) -> None:
        df = small_expenses()
        kpis = expenses_kpis(df)
        distribution = spending_by_category(df).set_index("category")
        vendors = expenses_by_vendor(df).set_index("vendor")
        trend, frequency = expense_trend(df)

        self.assertEqual(
            kpis,
            {
                "total_expenses": 200.0,
                "average_expense": 50.0,
                "expense_records": 4,
                "largest_expense_category": "Office Supplies",
            },
        )
        self.assertEqual(distribution.loc["Office Supplies", "percentage"], 75.0)
        self.assertEqual(vendors.loc["Acme", "amount"], 150.0)
        self.assertEqual(frequency, "month")
        self.assertEqual(trend.loc[trend["amount"].idxmax(), "date"].month, 3)
        self.assertEqual(
            expenses_by_category(df).iloc[0]["category"],
            "Office Supplies",
        )

    def test_insights_include_category_month_and_vendor(self) -> None:
        insights = generate_expense_insights(small_expenses())

        self.assertEqual(
            insights[0],
            "Office Supplies accounts for 75% of total expenses.",
        )
        self.assertIn("Expenses were highest in March 2024", insights[1])
        self.assertIn("Acme represents the largest spending source", insights[2])

    def test_category_corrections_can_be_applied(self) -> None:
        raw = load("expenses_messy_100.csv")
        corrections = {
            suggestion.original: suggestion.suggestion
            for suggestion in suggest_category_corrections(raw)
        }

        self.assertIn("Office Supllies", corrections)
        cleaned, summary = clean_expenses(
            raw,
            CleaningChoices(category_corrections=corrections),
        )

        self.assertNotIn("Office Supllies", cleaned["category"].tolist())
        self.assertGreater(summary["categories_corrected"], 0)

    def test_zero_expenses_do_not_create_false_shares_or_vendor_rank(self) -> None:
        cleaned, _ = clean_expenses(
            load("expenses_zero_total.csv"),
            CleaningChoices(),
        )

        self.assertEqual(expenses_kpis(cleaned)["largest_expense_category"], None)
        self.assertTrue(
            spending_by_category(cleaned)["percentage"].eq(0).all()
        )
        insights = generate_expense_insights(cleaned)
        self.assertIn("shares are unavailable", insights[0])
        self.assertIn("no vendor expenses", insights[2])

    def test_cleaned_preview_formats_date_without_midnight_time(self) -> None:
        preview = format_cleaned_preview(small_expenses())

        self.assertEqual(preview.loc[0, "date"], "January 5, 2024")
        self.assertNotIn("00:00", preview.loc[0, "date"])

    def test_expense_trend_chart_labels_axis_and_tooltip(self) -> None:
        trend, frequency = expense_trend(small_expenses())

        chart = build_expenses_trend_chart(trend, frequency).to_dict()

        self.assertEqual(chart["encoding"]["y"]["title"], "Expenses")
        self.assertEqual(
            chart["encoding"]["tooltip"][1]["title"],
            "Expenses",
        )

    def test_clean_fixture_collection_is_analyzable_or_blocked_as_expected(self) -> None:
        blocked = {"expenses_invalid_amount.csv", "expenses_missing_column.csv"}
        for path in sorted(DATA.glob("*.csv")):
            if path.name in blocked or path.name == "expenses_custom_headers.csv":
                continue
            with self.subTest(fixture=path.name):
                raw = load(path.name, headers_included=path.name != "expenses_no_headers.csv")
                if path.name == "expenses_invalid_amount.csv":
                    self.assertTrue(invalid_amount_mask(raw).any())
                    continue
                cleaned, _ = clean_expenses(raw, CleaningChoices())
                self.assertGreater(len(cleaned), 0)
                self.assertEqual(list(cleaned.columns), EXPENSES_COLUMNS)
                self.assertTrue(generate_expense_insights(cleaned))


if __name__ == "__main__":
    unittest.main()