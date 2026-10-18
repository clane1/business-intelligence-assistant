"""Regression tests for adaptive sales trends and all sales CSV fixtures."""

import unittest
from pathlib import Path

import pandas as pd

from backend.cleaning import (
    clean_dates,
    clean_duplicates,
    clean_missing,
    clean_types,
    normalize_categories,
)
from backend.insights import generate_insights
from backend.transformation import (
    calculate_kpis,
    category_distribution,
    sales_by_category,
    sales_by_time_period,
)
from backend.validation import count_invalid_dates, validate_columns
from frontend.charts import build_sales_trend_chart


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SALES_DATA = PROJECT_ROOT / "data" / "sales"
REQUIRED_COLUMNS = ["date", "amount", "category", "item"]
INVALID_FIXTURE = "sales_missing_amount_2.csv"


def clean_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the same transformations as the Streamlit cleaning workflow."""
    df = clean_missing(df.copy())
    df = clean_types(df)
    df = clean_dates(df, ["date"])
    df = clean_duplicates(df)
    return normalize_categories(df, "category")


class SalesTrendTests(unittest.TestCase):
    def test_day_month_year_dates_are_parsed_consistently(self) -> None:
        df = pd.DataFrame(
            {
                "date": [
                    "01-02-2024",
                    "31-02-2024",
                    "2024-02-29",
                ],
                "amount": [10.0, 20.0, 30.0],
            }
        )

        cleaned = clean_dates(df.copy(), ["date"])

        self.assertEqual(
            cleaned.loc[0, "date"],
            pd.Timestamp("2024-02-01"),
        )
        self.assertTrue(pd.isna(cleaned.loc[1, "date"]))
        self.assertEqual(
            cleaned.loc[2, "date"],
            pd.Timestamp("2024-02-29"),
        )
        self.assertEqual(count_invalid_dates(df), 1)

    def test_selects_granularity_from_date_span(self) -> None:
        cases = [
            (31, "day"),
            (32, "week"),
            (180, "week"),
            (181, "month"),
        ]

        for span_days, expected_frequency in cases:
            with self.subTest(span_days=span_days):
                dates = pd.date_range("2025-01-01", periods=span_days + 1)
                df = pd.DataFrame(
                    {
                        "date": dates,
                        "amount": 1.0,
                    }
                )

                trend, frequency = sales_by_time_period(df)

                self.assertEqual(frequency, expected_frequency)
                self.assertEqual(trend["amount"].sum(), len(df))
                self.assertTrue(trend["date"].is_monotonic_increasing)

    def test_trend_chart_labels_are_explicit_and_chronological(
        self,
    ) -> None:
        cases = [
            ("day", pd.date_range("2025-12-30", periods=4, freq="D"),
             ["Dec 30 '25", "Dec 31 '25", "Jan 01 '26", "Jan 02 '26"]),
            ("week", pd.date_range("2025-11-24", periods=4, freq="W-MON"),
             ["Nov 24 '25", "Dec 01 '25", "Dec 08 '25", "Dec 15 '25"]),
            (
                "month",
                pd.date_range("2025-03-01", periods=12, freq="MS"),
                [
                    "Mar '25", "Apr '25", "May '25", "Jun '25",
                    "Jul '25", "Aug '25", "Sep '25", "Oct '25",
                    "Nov '25", "Dec '25", "Jan '26", "Feb '26",
                ],
            ),
        ]

        for frequency, dates, expected_labels in cases:
            with self.subTest(frequency=frequency):
                trend = pd.DataFrame(
                    {
                        "date": dates,
                        "amount": [float(i) for i in range(1, len(dates) + 1)],
                    }
                )
                chart_spec = build_sales_trend_chart(
                    trend,
                    frequency,
                ).to_dict()

                self.assertEqual(
                    chart_spec["encoding"]["x"]["sort"],
                    expected_labels,
                )
                self.assertEqual(
                    chart_spec["encoding"]["x"]["axis"]["values"],
                    expected_labels,
                )

    def test_all_sales_fixtures_complete_analysis_or_are_blocked(self) -> None:
        fixtures = sorted(SALES_DATA.glob("*.csv"))
        self.assertEqual(len(fixtures), 11)

        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                raw_df = pd.read_csv(fixture)
                missing_columns = validate_columns(raw_df, REQUIRED_COLUMNS)

                if fixture.name == INVALID_FIXTURE:
                    self.assertEqual(missing_columns, ["amount"])
                    continue

                self.assertEqual(missing_columns, [])
                df = clean_sales_data(raw_df)

                self.assertFalse(df.empty)
                self.assertFalse(df.duplicated().any())
                self.assertTrue(df["amount"].notna().all())
                self.assertTrue(df["category"].ne("").all())

                trend, frequency = sales_by_time_period(df)
                valid_sales = df.dropna(subset=["date"])
                self.assertFalse(trend.empty)
                self.assertAlmostEqual(
                    trend["amount"].sum(),
                    valid_sales["amount"].sum(),
                    places=2,
                )

                date_span = (
                    valid_sales["date"].max() - valid_sales["date"].min()
                ).days
                expected_frequency = (
                    "day"
                    if date_span <= 31
                    else "week"
                    if date_span <= 180
                    else "month"
                )
                self.assertEqual(frequency, expected_frequency)

                kpis = calculate_kpis(df)
                self.assertEqual(
                    kpis["transaction_count"],
                    len(df),
                )
                self.assertAlmostEqual(
                    kpis["total_sales"],
                    round(df["amount"].sum(), 2),
                )
                self.assertAlmostEqual(
                    sales_by_category(df)["amount"].sum(),
                    df["amount"].sum(),
                )

                distribution = category_distribution(df)
                if kpis["total_sales"] == 0:
                    self.assertTrue(distribution["percentage"].eq(0).all())
                else:
                    self.assertAlmostEqual(
                        distribution["percentage"].sum(),
                        100.0,
                        places=1,
                    )

                insights = generate_insights(df)
                self.assertTrue(insights)
                self.assertTrue(all(isinstance(item, str) for item in insights))
                insight_text = " ".join(insights)
                if fixture.name == "sales_single_category_50.csv":
                    self.assertIn(
                        "All recorded sales came from Books; "
                        "no category comparison is available.",
                        insight_text,
                    )
                    self.assertNotIn(
                        "Sales were highest for",
                        insight_text,
                    )
                    self.assertNotIn(
                        "Sales were lowest for",
                        insight_text,
                    )
                if kpis["total_sales"] == 0:
                    self.assertIn(
                        "There are no sales amounts to compare by category.",
                        insight_text,
                    )
                    self.assertIn(
                        "There are no sales amounts to compare over time.",
                        insight_text,
                    )
                    self.assertIn(
                        "Category shares are unavailable because total sales are zero.",
                        insight_text,
                    )
                else:
                    expected_wording = {
                        "day": "Sales were highest on",
                        "week": "had the most sales",
                        "month": "Sales were highest in",
                    }[frequency]
                    self.assertIn(expected_wording, insight_text)
                    self.assertIn(
                        "Recorded sales totaled",
                        insight_text,
                    )


if __name__ == "__main__":
    unittest.main()
