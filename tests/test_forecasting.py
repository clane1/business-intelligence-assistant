"""Sales forecast calculations, chart, and guided workflow tests."""

import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from backend.forecasting import (
    FORECAST_COLUMNS,
    INSUFFICIENT_DATA_MESSAGE,
    generate_forecast_insight,
    generate_sales_forecast,
)
from backend.recommendations import CleaningChoices, clean_with_choices
from frontend.charts import build_sales_forecast_chart


ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "frontend" / "streamlit_app_v2.py")
LEGACY_APP = str(ROOT / "frontend" / "streamlit_app.py")


class ForecastTests(unittest.TestCase):
    def test_calendar_offsets_daily_totals_and_exact_horizon(self) -> None:
        sales = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-01", "2024-01-03", "bad", "2024-01-04"],
            "amount": [4.0, 6.0, 30.0, 100.0, None],
        })
        original = sales.copy(deep=True)
        forecast = generate_sales_forecast(sales)
        pd.testing.assert_frame_equal(sales, original)
        self.assertEqual(list(forecast.columns), FORECAST_COLUMNS)
        self.assertEqual(len(forecast), 32)
        historical = forecast.dropna(subset=["historical_sales"])
        future = forecast.dropna(subset=["forecast_sales"])
        self.assertEqual(historical["historical_sales"].tolist(), [10.0, 30.0])
        self.assertEqual(len(future), 30)
        self.assertEqual(future["date"].iloc[0], pd.Timestamp("2024-01-04"))
        self.assertEqual(future["date"].iloc[-1], pd.Timestamp("2024-02-02"))
        self.assertGreater(future["date"].max(), historical["date"].max())
        self.assertAlmostEqual(future["forecast_sales"].iloc[0], 40.0)
        self.assertAlmostEqual(future["forecast_sales"].iloc[-1], 330.0)
        self.assertTrue(historical["forecast_sales"].isna().all())
        self.assertTrue(future["historical_sales"].isna().all())

    def test_clean_fixture_generates_forecast(self) -> None:
        sales = pd.read_csv(ROOT / "data" / "sales" / "sales_clean_100.csv")
        forecast = generate_sales_forecast(sales)
        self.assertFalse(forecast.empty)
        self.assertEqual(forecast["forecast_sales"].notna().sum(), 30)

    def test_forecast_across_cleaned_sales_fixtures(self) -> None:
        fixtures = [
            "sales_sample_10.csv",
            "sales_clean_100.csv",
            "sales_clean_1000.csv",
            "sales_messy_11.csv",
            "sales_messy_1000.csv",
            "sales_returns_100.csv",
            "sales_single_category_50.csv",
            "sales_yearly_trend_365.csv",
            "sales_zero_revenue_12.csv",
        ]
        for name in fixtures:
            with self.subTest(fixture=name):
                raw = pd.read_csv(ROOT / "data" / "sales" / name)
                sales, _ = clean_with_choices(raw, CleaningChoices())
                usable = sales.dropna(subset=["date", "amount"]).copy()
                usable["date"] = usable["date"].dt.normalize()
                expected = usable.groupby("date", as_index=False)["amount"].sum()
                forecast = generate_sales_forecast(sales)
                self.assertGreaterEqual(len(expected), 2)
                historical = forecast.dropna(subset=["historical_sales"])
                future = forecast.dropna(subset=["forecast_sales"])
                self.assertEqual(historical["date"].tolist(), expected["date"].tolist())
                for actual, total in zip(historical["historical_sales"], expected["amount"]):
                    self.assertAlmostEqual(actual, total)
                self.assertEqual(len(future), 30)
                last_date = expected["date"].max()
                self.assertEqual(future["date"].iloc[0], last_date + pd.Timedelta(days=1))
                self.assertEqual(future["date"].iloc[-1], last_date + pd.Timedelta(days=30))
                self.assertTrue(future["forecast_sales"].notna().all())
                if name == "sales_zero_revenue_12.csv":
                    self.assertTrue((future["forecast_sales"] == 0).all())
                    self.assertIn("stable", generate_forecast_insight(forecast))

    def test_insufficient_dates_return_empty_with_message(self) -> None:
        for dates, amounts in [
            ([], []),
            (["bad"], [1]),
            (["2024-01-01", "2024-01-01"], [1, 2]),
            (["2024-01-01", "2024-01-02"], [1, None]),
        ]:
            with self.subTest(dates=dates, amounts=amounts):
                result = generate_sales_forecast(pd.DataFrame({
                    "date": dates, "amount": amounts,
                }))
                self.assertTrue(result.empty)
                self.assertEqual(list(result.columns), FORECAST_COLUMNS)
                self.assertEqual(generate_forecast_insight(result), INSUFFICIENT_DATA_MESSAGE)

    def test_direction_and_stability_insights(self) -> None:
        for amounts, phrase in [
            ([10, 20], "increase"),
            ([20, 10], "declining"),
            ([10, 10], "stable"),
            ([0, 0], "stable"),
            ([-10, -20], "declining"),
        ]:
            with self.subTest(amounts=amounts):
                sales = pd.DataFrame({
                    "date": ["2024-01-01", "2024-01-02"],
                    "amount": amounts,
                })
                self.assertIn(phrase, generate_forecast_insight(generate_sales_forecast(sales)))

    def test_chart_contains_both_series_and_colors(self) -> None:
        sales = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02"],
            "amount": [10, 20],
        })
        chart = build_sales_forecast_chart(generate_sales_forecast(sales))
        spec = chart.to_dict()
        color = spec["encoding"]["color"]["scale"]
        self.assertEqual(color["domain"], ["Historical", "Forecast"])
        self.assertEqual(color["range"], ["#1f77b4", "#ff7f0e"])
        self.assertEqual(set(chart.data["series"]), {"Historical", "Forecast"})
        self.assertEqual(len(chart.data), 32)

    def test_sales_dashboard_and_insights_show_forecast_or_message(self) -> None:
        for dates, expected in [
            (["2024-01-01", "2024-01-02"], "projected to increase"),
            (["2024-01-01", "2024-01-01"], "Insufficient data"),
        ]:
            with self.subTest(dates=dates):
                app = AppTest.from_file(APP, default_timeout=60).run()
                app.session_state["clean_df"] = pd.DataFrame({
                    "date": pd.to_datetime(dates),
                    "amount": [10.0, 20.0],
                    "category": ["Food", "Food"],
                    "item": ["A", "B"],
                })
                app.session_state["current_step"] = 3
                app.run()
                self.assertFalse(app.exception)
                self.assertTrue(any(header.value == "Forecast" for header in app.header))
                self.assertTrue(any(expected in info.value for info in app.info))
                app.session_state["current_step"] = 4
                app.run()
                self.assertFalse(app.exception)
                self.assertTrue(any(expected in item.value for item in app.success))

    def test_original_sales_app_displays_forecast(self) -> None:
        app = AppTest.from_file(LEGACY_APP, default_timeout=60).run()
        csv_path = ROOT / "data" / "sales" / "sales_clean_100.csv"
        app.file_uploader[0].upload(csv_path.name, csv_path.read_bytes(), "text/csv")
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any(header.value == "Forecast" for header in app.header))
        self.assertTrue(any("next 30 days" in info.value for info in app.info))


if __name__ == "__main__":
    unittest.main()
