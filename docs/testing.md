# Testing and Sales Test Data

## Automated regression tests

From the repository root, run the automated test suite:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_sales_trend.py" -v
```

The suite verifies date parsing, trend interval boundaries, explicit
chronological labels for daily, weekly, and monthly charts, and analysis
behavior across every CSV in `data/sales/`. It checks the intentionally invalid
fixture for the missing required `amount` column. It also checks that the
single-category and zero-revenue cases produce sensible insights.

## Pipeline smoke check

Run the separate print-based sample pipeline check:

```powershell
.\venv\Scripts\python.exe tests\test_pipeline.py
```

It loads `data/sales/sales_sample_10.csv`, applies the cleaning functions,
calculates metrics and aggregations, and prints generated insights. This is a
small smoke check; the automated regression suite covers a broader set of
cases.

## Fixture inventory

| File | Scenario |
| --- | --- |
| `sales_sample_10.csv` | Small, ordinary sales dataset; used by the smoke script. |
| `sales_clean_100.csv` | Clean dataset with 100 rows. |
| `sales_clean_1000.csv` | Clean dataset with 1,000 rows. |
| `sales_messy_11.csv` | Small dataset with mixed data-quality issues. |
| `sales_messy_1000.csv` | Larger messy dataset with missing values, duplicate rows, inconsistent category capitalization/spelling, malformed dates, and formatted amounts. |
| `sales_returns_100.csv` | Sales data including return/negative-amount cases. |
| `sales_single_category_50.csv` | Dataset with a single category. |
| `sales_validation_issues_5.csv` | Small dataset for validation and cleaning scenarios. |
| `sales_yearly_trend_365.csv` | Daily records spanning a year for date-oriented analysis. |
| `sales_zero_revenue_12.csv` | Zero-revenue edge case for safe KPI, chart, and insight behavior. |
| `sales_missing_amount_2.csv` | Intentionally invalid schema: required `amount` column is omitted. |

## Recorded development verification

On October 17, 2026, all eleven fixtures were exercised in the Streamlit
workflow. Ten valid files completed upload, validation, cleaning, dashboard,
and insights. The intentionally invalid file reported the missing `amount`
column and kept cleaning disabled. The browser check also confirmed readable,
chronological axes and matching day/week/month insight wording.

The four automated regression tests and the sample pipeline smoke check
passed again on October 18, 2026. The browser workflow was also checked with
the 100-row clean fixture after the wording changes; it completed through the
dashboard and showed a weekly trend with ordered date labels. Re-run both
commands after changes to data cleaning, transformations, charting, or
insight generation.

## Suggested manual evaluation procedure

For each valid fixture:

1. Upload the file in the Streamlit app.
2. Confirm the required-column check passes and the preview/shape are shown.
3. Review validation counts and proceed to cleaning.
4. Confirm the cleaning summary and cleaned preview appear.
5. Confirm the dashboard and insights load without an error.
6. For the zero-revenue fixture, confirm the UI explains unavailable revenue
   comparisons instead of failing.

For `sales_missing_amount_2.csv`, confirm that validation identifies
`amount` as missing and prevents progression to cleaning and analysis.

For a final project evaluation, record the Python and package versions, test
date, observed outcomes, and any user-study results. Fixture tests check
technical behavior; they do not, by themselves, establish usability for a
broad user population.
