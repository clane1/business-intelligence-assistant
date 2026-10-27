"""Tests for dashboard aggregation and plain-language insights."""

import unittest

import pandas as pd

from backend.insights import generate_insights
from backend.transformation import (
    calculate_kpis,
    category_distribution,
    sales_by_category,
    sales_by_date,
)


def sales() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02"]),
            "amount": [10.0, 30.0, 60.0],
            "category": ["Food", "Books", "Food"],
            "item": ["Tea", "Novel", "Cake"],
        }
    )


class TransformationTests(unittest.TestCase):
    def test_kpis(self) -> None:
        self.assertEqual(
            calculate_kpis(sales()),
            {"total_sales": 100.0, "average_sale": 33.33, "transaction_count": 3},
        )

    def test_kpis_treat_unparseable_amounts_as_zero(self) -> None:
        df = sales()
        df["amount"] = df["amount"].astype(object)
        df.loc[0, "amount"] = None

        kpis = calculate_kpis(df)

        self.assertEqual(kpis["total_sales"], 90.0)
        self.assertEqual(kpis["transaction_count"], 3)

    def test_sales_by_category_is_sorted_highest_first(self) -> None:
        result = sales_by_category(sales())

        self.assertEqual(result["category"].tolist(), ["Food", "Books"])
        self.assertEqual(result["amount"].tolist(), [70.0, 30.0])

    def test_sales_by_date_is_chronological(self) -> None:
        result = sales_by_date(sales().iloc[::-1])

        self.assertEqual(result["amount"].tolist(), [40.0, 60.0])

    def test_category_distribution_percentages_sum_to_100(self) -> None:
        result = category_distribution(sales())

        self.assertAlmostEqual(result["percentage"].sum(), 100.0)

    def test_category_distribution_with_zero_sales_has_zero_shares(self) -> None:
        df = sales()
        df["amount"] = 0.0

        self.assertEqual(category_distribution(df)["percentage"].tolist(), [0.0, 0.0])


class InsightTests(unittest.TestCase):
    def test_insights_are_non_empty_text(self) -> None:
        insights = generate_insights(sales())

        self.assertTrue(insights)
        self.assertTrue(all(isinstance(line, str) and line for line in insights))

    def test_insights_mention_top_category(self) -> None:
        self.assertTrue(any("Food" in line for line in generate_insights(sales())))

    def test_zero_revenue_data_does_not_fail(self) -> None:
        df = sales()
        df["amount"] = 0.0

        self.assertIsInstance(generate_insights(df), list)


if __name__ == "__main__":
    unittest.main()
