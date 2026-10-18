# Business Intelligence Assistant

A guided Streamlit app for checking a sales spreadsheet, fixing common data
issues, and viewing sales totals, charts, and plain-language highlights.

> **Current scope:** Sales Data is the only supported dataset type. CSV files
> must include `date`, `amount`, `category`, and `item` columns. This prototype
> processes data in memory and does not persist uploads to a database.

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

1. Upload a sales CSV.
2. Check which columns are present, review empty cells and unusual dates, and
   preview the uploaded file.
3. Run cleaning when the required columns are present; review the cleaning
   summary and cleaned-data preview.
4. Explore the dashboard and generated insights.

The app can clean amounts that contain dollar signs or commas, fill supported
empty cells, remove repeated rows, and make category names consistent. Use
year-month-day dates such as `2024-01-31` when possible. Dates the app cannot
read are left out of the sales trend and date-related insights, but their
amounts still count in sales totals.
The trend chart groups sales by day, week, or month depending on the date span.

If a file includes negative amounts, they reduce the sales total and may
represent refunds or returns.

## Tests

Run the automated regression tests from the repository root:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_sales_trend.py" -v
```

The tests check date parsing, daily/weekly/monthly trend selection and labels,
and all sales CSV fixtures. The fixture with the missing `amount` column must
be rejected. A separate sample-data smoke check is also available:

```powershell
.\venv\Scripts\python.exe tests\test_pipeline.py
```

## Project documentation

- [Architecture and workflow](docs/architecture.md)
- [Testing and sales fixtures](docs/testing.md)
- [Capstone report draft](docs/capstone_report_draft.md)
- [Formatted report PDF](docs/Business_Intelligence_Assistant_Report.pdf)

Sample and test CSV files are in [data/sales](data/sales/).
