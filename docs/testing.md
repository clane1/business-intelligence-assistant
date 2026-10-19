# Testing and Sales Test Data

## Automated regression tests

From the repository root, run the automated test suite:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_sales_trend.py" -v
```

The suite verifies date parsing, trend interval boundaries, explicit
chronological labels for daily, weekly, and monthly charts, and analysis
behavior across every standard CSV in `data/sales/`. It tests headerless
loading with comma- and semicolon-delimited fixtures, including a messy file,
and checks that a headerless file with the wrong column count is rejected. It
also checks the generic CSV parser, tab delimiters with and without headers,
mismatched header settings, and the intentionally invalid headered fixture
for the missing required `amount` column. It checks that the single-category
and zero-revenue cases produce sensible insights, that dates in insights use
full month names, and that amounts with dollar signs and thousands separators
are counted for cleaning.

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
| `sales_no_headers_clean_8.csv` | Clean eight-row sales file with no header row. |
| `sales_no_headers_messy_6.csv` | Headerless six-row file with currency values, inconsistent category case, a missing amount, an invalid date, a negative amount, and a duplicate. |
| `sales_no_headers_semicolon_4.csv` | Headerless four-row sales file using semicolons. |
| `sales_no_headers_missing_column_2.csv` | Intentionally invalid headerless file with only three columns. |

## Recorded development verification

On October 18, 2026, all thirteen automated regression tests passed. The existing
eleven standard fixtures completed analysis or were rejected for the expected
missing `amount` column. The three valid headerless fixtures loaded with the
expected columns, passed cleaning, and produced KPI and trend results; the
three-column headerless fixture was rejected with a clear column-count and
delimiter-check message.
The sample pipeline smoke check also passed.

In the browser, the messy headerless file was uploaded with the header option
unchecked and reached validation with six rows, four recognized columns, and
the expected missing-value, invalid-date, duplicate, and currency counts. The
three-column file displayed the explicit format error and did not proceed.
Re-run both commands after changes to data loading, cleaning, transformations,
charting, or insight generation.

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

For valid `sales_no_headers_*.csv` files, turn off the header-row checkbox,
select the fixture's delimiter, and confirm the app recognizes the columns in
the order `date`, `amount`, `category`, `item`. The clean, messy, and
semicolon-delimited files should proceed through cleaning and analysis. The
`sales_no_headers_missing_column_2.csv` fixture should show the four-column
requirement and should not enable progression to validation.

For files with headers, keep the header option on. In either header mode,
select the delimiter that matches the file. A mismatch should show a
parsing/schema message and should not allow cleaning with incorrectly named
columns.

For a final project evaluation, record the Python and package versions, test
date, observed outcomes, and any user-study results. Fixture tests check
technical behavior; they do not, by themselves, establish usability for a
broad user population.
