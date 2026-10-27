# Business Intelligence Assistant

A guided Streamlit app for checking a sales spreadsheet, fixing common data
issues, and viewing sales totals, charts, and plain-language highlights.

> **Current scope:** Sales Data is the only supported dataset type. CSV files
> need `date`, `amount`, `category`, and `item` columns. For files without a
> header row, select the no-header option and provide those four columns in
> that exact order. This prototype processes data in memory and does not
> persist uploads to a database.

## Quick start (Windows)

From the repository root, create and activate a virtual environment, install
the app's Python packages, and start Streamlit:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install pandas streamlit altair
python -m streamlit run frontend\streamlit_app_v2.py
```

If PowerShell blocks environment activation, run the commands using the
environment's interpreter directly:

```powershell
.\venv\Scripts\python.exe -m pip install pandas streamlit altair
.\venv\Scripts\python.exe -m streamlit run frontend\streamlit_app_v2.py
```

Open the local URL printed by Streamlit in a browser. To stop the server, press
`Ctrl+C` in the terminal where it is running.

## Use the application

1. Upload a sales CSV. The requirements and an example file are shown below
   the uploader.
2. Check which columns are present, review empty cells and unusual dates, and
   preview the uploaded file. The page is split into **Data summary**, **Data
   quality metrics**, **Recommended actions**, and **Apply fixes**.
3. Review the recommended actions for duplicate rows, missing amounts,
   unreadable dates, and likely misspelled category names (for example
   `Electonics` → `Electronics`). Each shows a preview of the affected rows or
   values. Accept or reject each one, then apply the selected fixes; nothing is
   changed before that. Review the cleaning summary and cleaned-data preview.
4. Explore the dashboard and generated insights. The dashboard summary
   includes **View cleaning report** and **Download Cleaning Report**: a text
   file listing rows before and after, and each issue found with what was done
   about it (including fixes you rejected).

The required columns are `date`, `amount`, `category`, and `item`. If a
headered file uses different names (for example `Transaction Date`, `Revenue`,
`Department`, `Product`), the check page shows a **Match your columns** form
with suggestions filled in. Confirm it and the app uses your columns under the
required names; other columns in the file are not used. If a required value
isn't in your file at all, validation names it, blocks cleaning, and provides a
**Back to Upload Data** action so you can correct the
CSV and upload it again. A missing column is different from an empty cell:
empty cells are listed by column and filled with the app's documented defaults
during cleaning.

When the first row does not contain column names, uncheck **The first row
contains column names**. Headerless files must contain exactly four columns in
this order: `date`, `amount`, `category`, `item`. The selected delimiter still
applies. If a headerless file has a different number of columns, the upload
error reports the number read and the required order. Since there are no
column names, the app cannot identify which field is missing.

CSV parsing is handled by a generic file reader and a sales-specific wrapper:
the generic reader parses the chosen delimiter/header mode, while the sales
wrapper checks the required sales column order and provides upload-specific
format errors.

The app can clean amounts that contain dollar signs or commas, fill supported
empty cells, remove repeated rows, and make category names consistent.
Non-numeric, non-empty amount values cannot be cleaned automatically; the
validation screen reports example values and CSV data-row numbers so they can
be corrected before cleaning. Unreadable dates are reported with example
values and data-row numbers, then excluded from date-based charts and insights;
their amounts still count in sales totals. Use year-month-day dates such as
`2024-01-31` when possible. The trend chart groups sales by day, week, or
month depending on the date span.

If a file includes negative amounts, they reduce the sales total and may
represent refunds or returns.

## Tests

Run the automated tests from the repository root:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_[a-oq-z]*.py"
```

They cover validation and cleaning, recommendations and category suggestions,
column mapping, upload diagnosis, the cleaning report, dashboard calculations,
all sales CSV fixtures, and a headless run of the whole app workflow. A
separate sample-data smoke check is also available:

```powershell
.\venv\Scripts\python.exe tests\test_pipeline.py
```

## Project documentation

- [Architecture and workflow](docs/architecture.md)
- [Testing and sales fixtures](docs/testing.md)
- [Capstone report draft](docs/capstone_report_draft.md)
- [Formatted report PDF](docs/Business_Intelligence_Assistant_Report.pdf)

Sample and test CSV files are in [data/sales](data/sales/).
