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
and checks that a headerless file with the wrong column count is rejected with
an explicit explanation that the missing named field cannot be identified
without headers. It also checks the generic CSV parser, tab delimiters with
and without headers, mismatched header settings, and the intentionally
invalid headered fixture for the missing required `amount` column. Validation
mask tests verify which amount/date values are invalid. The suite also checks
that single-category and zero-revenue cases produce sensible insights, dates
in insights use full month names, and amounts with dollar signs and thousands
separators are counted for cleaning.

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

On October 19, 2026, all fourteen automated regression tests passed. All
fifteen bundled sales CSV files were run through the configured sales loader
and validation checks. The ten ordinary/headered fixtures loaded with the
expected schema except `sales_missing_amount_2.csv`, which correctly reported
the missing `amount` column. The three valid headerless fixtures loaded with
the expected four columns, and the malformed three-column headerless fixture
was rejected with its actual column count and the required order. Intentional
data-quality cases reported their empty-cell, invalid-date, duplicate, and
currency-format counts.

Streamlit UI tests confirmed that the missing-column screen names `amount`,
explains that the CSV must be corrected and uploaded again, and returns to the
upload step. They also confirmed that unreadable dates and non-numeric amounts
show example values and one-based CSV data-row numbers, and that non-numeric
amounts block cleaning. The sample pipeline smoke check is available above;
rerun it alongside the regression suite after changes to loading, cleaning,
transformations, charting, or insight generation.

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
`amount` as missing, directs the user to correct and re-upload the CSV, offers
a **Back to Upload Data** action, and prevents cleaning and analysis.

For valid `sales_no_headers_*.csv` files, turn off the header-row checkbox,
select the fixture's delimiter, and confirm the app recognizes the columns in
the order `date`, `amount`, `category`, `item`. The clean, messy, and
semicolon-delimited files should proceed through cleaning and analysis. The
`sales_no_headers_missing_column_2.csv` fixture should report the three
columns read, show the required four-column order, explain that the missing
named field cannot be identified without headers, and not enable progression
to validation.

For files with headers, keep the header option on. In either header mode,
select the delimiter that matches the file. A mismatch should show a
parsing/schema message that names missing columns when they can be identified,
and should not allow cleaning with incorrectly named columns. For validation
examples, check that displayed row numbers refer to one-based CSV data rows
(not counting a header row), and that quoted values identify the problematic
cells.

For a final project evaluation, record the Python and package versions, test
date, observed outcomes, and any user-study results. Fixture tests check
technical behavior; they do not, by themselves, establish usability for a
broad user population.
