"""Regression coverage for the sales workflow's loading and analysis rules.

The tests exercise CSV header/delimiter handling, data cleaning, adaptive
trend intervals and labels, generated insight wording, and every standard
sales fixture.
"""

from io import StringIO
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
from backend.csv_loader import (
    SalesCsvFormatError,
    load_sales_csv,
)
from backend.load_csv import load_csv
from backend.insights import generate_insights
from backend.transformation import (
    calculate_kpis,
    category_distribution,
    sales_by_category,
    sales_by_time_period,
)
from backend.validation import (
    count_currency_values,
    count_invalid_dates,
    invalid_amount_mask,
    invalid_date_mask,
    validate_columns,
)
from frontend.charts import build_sales_trend_chart


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SALES_DATA = PROJECT_ROOT / "data" / "sales"
REQUIRED_COLUMNS = ["date", "amount", "category", "item"]
INVALID_FIXTURE = "sales_missing_amount_2.csv"
HEADERLESS_FIXTURES = {
    "sales_no_headers_clean_8.csv": (",", 8),
    "sales_no_headers_messy_6.csv": (",", 6),
    "sales_no_headers_semicolon_4.csv": (";", 4),
}
MALFORMED_HEADERLESS_FIXTURE = "sales_no_headers_missing_column_2.csv"


def clean_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the ordered transformations used by the guided app.

    Args:
        df: Raw sales DataFrame to clean. The input is copied before mutation.

    Returns:
        Cleaned sales data with normalized dates, amounts, duplicates, and
        category labels.
    """
    df = clean_missing(df.copy())
    df = clean_types(df)
    df = clean_dates(df, ["date"])
    df = clean_duplicates(df)
    return normalize_categories(df, "category")


class SalesTrendTests(unittest.TestCase):
    """Verify sales CSV loading, cleaning, aggregation, and insight behavior."""

    def test_loads_headerless_fixtures_through_sales_pipeline(self) -> None:
        """Check valid headerless fixtures load and support analysis."""
        for fixture_name, (delimiter, expected_rows) in HEADERLESS_FIXTURES.items():
            fixture = SALES_DATA / fixture_name
            with self.subTest(fixture=fixture_name), fixture.open("rb") as source:
                raw_df = load_sales_csv(
                    source,
                    delimiter=delimiter,
                    headers_included=False,
                )

                self.assertEqual(list(raw_df.columns), REQUIRED_COLUMNS)
                self.assertEqual(len(raw_df), expected_rows)
                self.assertEqual(validate_columns(raw_df, REQUIRED_COLUMNS), [])

                df = clean_sales_data(raw_df)
                self.assertFalse(df.empty)
                self.assertFalse(df.duplicated().any())
                self.assertTrue(df["amount"].notna().all())

                kpis = calculate_kpis(df)
                trend, _ = sales_by_time_period(df)
                self.assertGreater(kpis["transaction_count"], 0)
                self.assertFalse(trend.empty)

        with (SALES_DATA / "sales_no_headers_messy_6.csv").open("rb") as source:
            messy_df = load_sales_csv(
                source,
                delimiter=",",
                headers_included=False,
            )
        cleaned_messy_df = clean_sales_data(messy_df)
        self.assertEqual(len(cleaned_messy_df), 5)
        self.assertEqual(count_invalid_dates(cleaned_messy_df), 1)
        self.assertIn("Electronics", cleaned_messy_df["category"].tolist())

    def test_headerless_fixture_with_wrong_column_count_is_rejected(self) -> None:
        """Reject headerless input that does not have four sales fields."""
        fixture = SALES_DATA / MALFORMED_HEADERLESS_FIXTURE

        with fixture.open("rb") as source:
            with self.assertRaisesRegex(
                SalesCsvFormatError,
                "can't identify which field is missing",
            ):
                load_sales_csv(
                    source,
                    delimiter=",",
                    headers_included=False,
                )

    def test_headered_content_is_rejected_when_header_option_is_off(self) -> None:
        """Detect a standard sales header when the user says it is absent."""
        with self.assertRaisesRegex(
            SalesCsvFormatError,
            "appears to contain a header row",
        ):
            load_sales_csv(
                StringIO(
                    "date,amount,category,item\n"
                    "2024-07-01,14.50,Food,Bread\n"
                ),
                delimiter=",",
                headers_included=False,
            )

    def test_headerless_content_does_not_create_required_column_names(self) -> None:
        """Confirm the headered mode does not silently repair absent headers."""
        df = load_sales_csv(
            StringIO("2024-07-01,14.50,Food,Bread\n"),
            delimiter=",",
            headers_included=True,
        )

        self.assertEqual(
            validate_columns(df, REQUIRED_COLUMNS),
            REQUIRED_COLUMNS,
        )

    def test_loader_preserves_headered_csv_columns(self) -> None:
        """Preserve the four named columns and records of a normal CSV."""
        fixture = SALES_DATA / "sales_sample_10.csv"

        with fixture.open("rb") as source:
            df = load_sales_csv(
                source,
                delimiter=",",
                headers_included=True,
            )

        self.assertEqual(list(df.columns), REQUIRED_COLUMNS)
        self.assertEqual(len(df), 10)

    def test_generic_csv_loader_parses_without_sales_schema_rules(self) -> None:
        """Verify generic path and stream reads do not apply sales rules."""
        path_df = load_csv(SALES_DATA / "sales_sample_10.csv")
        df = load_csv(
            StringIO("2024-07-01,14.50,Food,Bread\n"),
            delimiter=",",
            headers_included=False,
        )

        self.assertEqual(list(path_df.columns), REQUIRED_COLUMNS)
        self.assertEqual(len(path_df), 10)
        self.assertEqual(list(df.columns), [0, 1, 2, 3])
        self.assertEqual(df.iloc[0].tolist(), [
            "2024-07-01",
            14.5,
            "Food",
            "Bread",
        ])

    def test_loader_handles_tab_delimiters_with_and_without_headers(self) -> None:
        """Parse tab-delimited data in both header modes."""
        headerless = load_sales_csv(
            StringIO(
                "2024-07-01\t14.50\tFood\tBread\n"
                "2024-07-02\t21.00\tHome\tLamp\n"
            ),
            delimiter="\t",
            headers_included=False,
        )
        headered = load_sales_csv(
            StringIO(
                "date\tamount\tcategory\titem\n"
                "2024-07-01\t14.50\tFood\tBread\n"
            ),
            delimiter="\t",
            headers_included=True,
        )

        self.assertEqual(list(headerless.columns), REQUIRED_COLUMNS)
        self.assertEqual(headerless.loc[0, "item"], "Bread")
        self.assertEqual(list(headered.columns), REQUIRED_COLUMNS)
        self.assertEqual(headered.loc[0, "amount"], 14.5)

    def test_day_month_year_dates_are_parsed_consistently(self) -> None:
        """Normalize valid day-month-year dates and reject impossible dates."""
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
        """Use daily, weekly, and monthly aggregation at their boundaries."""
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
        """Keep chart axis labels ordered and readable across year changes."""
        cases = [
            ("day", pd.date_range("2025-12-30", periods=4, freq="D"),
             [
                 "Dec 30, 2025", "Dec 31, 2025",
                 "Jan 1, 2026", "Jan 2, 2026",
             ]),
            ("week", pd.date_range("2025-11-24", periods=4, freq="W-MON"),
             [
                 "Nov 24, 2025", "Dec 1, 2025",
                 "Dec 8, 2025", "Dec 15, 2025",
             ]),
            (
                "month",
                pd.date_range("2025-03-01", periods=12, freq="MS"),
                [
                    "Mar 2025", "Apr 2025", "May 2025", "Jun 2025",
                    "Jul 2025", "Aug 2025", "Sep 2025", "Oct 2025",
                    "Nov 2025", "Dec 2025", "Jan 2026", "Feb 2026",
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
                chart = build_sales_trend_chart(trend, frequency)
                chart_spec = chart.to_dict()

                self.assertEqual(
                    chart_spec["encoding"]["x"]["sort"],
                    expected_labels,
                )
                self.assertEqual(
                    chart_spec["encoding"]["x"]["axis"]["values"],
                    expected_labels,
                )
                self.assertEqual(
                    chart.data["tooltip_period"].iloc[0],
                    "March 2025"
                    if frequency == "month"
                    else f"{dates[0]:%B} {dates[0].day}, {dates[0].year}",
                )

    def test_insight_dates_use_readable_month_names(self) -> None:
        """Present insight dates as familiar month-name labels."""
        cases = [
            (
                ["2024-01-01", "2024-01-02"],
                "January 2, 2024",
            ),
            (
                ["2024-01-01", "2024-02-10"],
                "week starting February 5, 2024",
            ),
            (
                ["2024-01-01", "2024-08-01"],
                "August 2024",
            ),
        ]

        for date_values, expected_date in cases:
            with self.subTest(expected_date=expected_date):
                df = pd.DataFrame(
                    {
                        "date": pd.to_datetime(date_values),
                        "amount": [10.0, 20.0],
                        "category": ["Food", "Books"],
                        "item": ["Coffee", "Novel"],
                    }
                )

                insights = generate_insights(df)
                insight_text = " ".join(insights)

                self.assertIn(expected_date, insight_text)
                self.assertNotIn("2024-", insight_text)

    def test_currency_format_count_includes_dollars_and_commas(self) -> None:
        """Count amount values that the cleaning step reformats."""
        df = pd.DataFrame(
            {
                "amount": [
                    "$1,250.00",
                    "2,000.00",
                    "25.00",
                    None,
                ]
            }
        )

        self.assertEqual(count_currency_values(df), 2)

    def test_invalid_amount_and_date_masks_identify_bad_values(self) -> None:
        """Expose exact unparseable values for user-facing validation details."""
        df = pd.DataFrame(
            {
                "amount": ["25.00", "not-a-number", None, "$12.00"],
                "date": [
                    "2024-01-01",
                    "not-a-date",
                    None,
                    "01-02-2024",
                ],
            }
        )

        self.assertEqual(
            invalid_amount_mask(df).tolist(),
            [False, True, False, False],
        )
        self.assertEqual(
            invalid_date_mask(df).tolist(),
            [False, True, True, False],
        )

    def test_all_sales_fixtures_complete_analysis_or_are_blocked(self) -> None:
        """Analyze every standard fixture or check its expected schema error."""
        fixtures = sorted(
            fixture
            for fixture in SALES_DATA.glob("*.csv")
            if not fixture.name.startswith(
                ("sales_no_headers_", "sales_custom_headers_")
            )
        )
        self.assertEqual(len(fixtures), 12)

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
                        "Total sales were",
                        insight_text,
                    )


if __name__ == "__main__":
    unittest.main()
