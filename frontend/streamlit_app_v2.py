"""
streamlit_app_v2.py

Business Intelligence Assistant

CMPT 496 Capstone Project

Version 2

This version follows the guided workflow
shown in the Figma prototype.

Workflow:

1. Upload Data
2. Validation
3. Dashboard
4. Insights

Users cannot skip ahead until previous
steps have been completed.
"""

# ==========================================
# IMPORTS
# ==========================================

import os
import sys
import pandas as pd
import streamlit as st

# ==========================================
# PROJECT PATH SETUP
# ==========================================

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            ".."
        )
    )
)

# ==========================================
# BACKEND MODULES
# ==========================================

from backend.transformation import (
    calculate_kpis,
    sales_by_category,
    sales_by_date,
    category_distribution
)

from backend.insights import (
    generate_insights
)

from backend.validation import (
    validate_columns,
    validate_missing,
    validate_types,
    count_invalid_dates,
    count_duplicates,
    count_currency_values
)

from backend.cleaning import (
    clean_missing,
    clean_types,
    clean_dates,
    clean_duplicates,
    normalize_categories
)

# ==========================================
# PAGE SETTINGS
# ==========================================

st.set_page_config(
    page_title="Clarity",
    page_icon="📊",
    layout="wide"
)

st.markdown(
    """
<style>

/* Sidebar */

section[data-testid="stSidebar"] {
    background-color: #0b2f1d;
}

/* Sidebar text */

section[data-testid="stSidebar"] * {
    color: white;
}

/* Sidebar buttons */

section[data-testid="stSidebar"] .stButton button {
    color: white !important;
    background-color: #174229;
    border: 1px solid #ffffff33;
    border-radius: 10px;
}

section[data-testid="stSidebar"] .stButton button p {
    color: white !important;
    font-weight: 600;
}

/* Hover effect */

section[data-testid="stSidebar"] .stButton button:hover {
    background-color: #1c5433;
}

/* Links and tables */

a {
    text-decoration: none;
    color: #464feb;
}

div[data-testid="stMarkdownContainer"] table th,
div[data-testid="stMarkdownContainer"] table td {
    border: 1px solid #e6e6e6;
}

div[data-testid="stMarkdownContainer"] table th {
    background-color: #f5f5f5;
    color: #263238 !important;
    font-weight: 600;
}

/* KPI cards */

[data-testid="metric-container"] {
    border: 1px solid #d9ded8;
    border-radius: 12px;
    padding: 15px;
}

</style>
""",
    unsafe_allow_html=True
)

# ==========================================
# SESSION STATE VARIABLES
# ==========================================
#
# Streamlit reruns the entire script whenever
# a user interacts with the application.
#
# Session State allows information to remain
# available between workflow steps.
#
# These variables control:
#
# current_step
#     Tracks which workflow screen is active
#
# raw_df
#     Stores the uploaded dataset before
#     cleaning and transformation
#
# clean_df
#     Stores the cleaned dataset after the
#     validation and cleaning stages
#
# dataset_type
#     Stores the selected analysis type
#     chosen by the user
#
# ==========================================

if "current_step" not in st.session_state:
    st.session_state.current_step = 1

if "raw_df" not in st.session_state:
    st.session_state.raw_df = None

if "clean_df" not in st.session_state:
    st.session_state.clean_df = None

if "cleaning_summary" not in st.session_state:
    st.session_state.cleaning_summary = None

if "dataset_type" not in st.session_state:
    st.session_state.dataset_type = "Sales Data"

# ==========================================
# WORKFLOW SIDEBAR
# ==========================================
#
# The sidebar functions as a workflow guide.
#
# Users complete the application in stages:
#
# Step 1 -> Upload Data
# Step 2 -> Validation
# Step 3 -> Dashboard
# Step 4 -> Insights
#
# Later stages remain locked until previous
# stages have been completed.
#
# This prevents users from skipping critical
# processing steps and mirrors the workflow
# proposed in the Figma prototype.
#
# ==========================================

with st.sidebar:

    st.title("Clarity")

    st.markdown(
        "### Analysis Workflow"
    )

    # ----------------------
    # STEP 1
    # ----------------------

    if st.button(
        "01 Upload Data",
        use_container_width=True
    ):
        st.session_state.current_step = 1

    # ----------------------
    # STEP 2
    # ----------------------

    if st.session_state.current_step >= 2:

        if st.button(
            "02 Validation",
            use_container_width=True
        ):
            st.session_state.current_step = 2

    else:
        st.caption("🔒 Validation")

    # ----------------------
    # STEP 3
    # ----------------------

    if st.session_state.current_step >= 3:

        if st.button(
            "03 Dashboard",
            use_container_width=True
        ):
            st.session_state.current_step = 3

    else:
        st.caption("🔒 Dashboard")

    # ----------------------
    # STEP 4
    # ----------------------

    if st.session_state.current_step >= 4:

        if st.button(
            "04 Insights",
            use_container_width=True
        ):
            st.session_state.current_step = 4

    else:
        st.caption("🔒 Insights")

    st.divider()

    # ----------------------
    # RESET
    # ----------------------

    if st.button(
        "🔄 Start New Analysis",
        use_container_width=True
    ):

        st.session_state.current_step = 1
        st.session_state.raw_df = None
        st.session_state.clean_df = None
        st.session_state.cleaning_summary = None
        st.session_state.dataset_type = "Sales Data"

        st.rerun()

# ==========================================
# STEP 1 - DATA UPLOAD
# ==========================================
#
# Purpose:
#     Collect user data and dataset settings.
#
# Functions:
#     - Select dataset type
#     - Configure CSV options
#     - Upload CSV file
#     - Store uploaded data in Session State
#
# Output:
#     raw_df
#
# Once a valid file is uploaded, users are
# permitted to continue to the validation
# stage.
#
# ==========================================


if st.session_state.current_step == 1:

    st.subheader(
        "Step 1 of 4"
    )

    st.title(
        "Prepare your business data"
    )

    st.write(
        "Select the dataset type and upload a CSV file."
    )

    # --------------------------------------
    # DATASET TYPE SELECTION
    # --------------------------------------
    #
    # Allows users to specify what kind of
    # business dataset is being analysed.
    #
    # Currently:
    #     Sales Data is supported
    #
    # Future versions may support:
    #     Inventory Data
    #     Expense Data
    #     Customer Data
    #
    # --------------------------------------

    dataset_type = st.selectbox(
        "Dataset Type",
        [
            "Sales Data",
            "Inventory Data",
            "Expense Data",
            "Customer Data"
        ]
    )

    st.session_state.dataset_type = dataset_type

    # --------------------------------------
    # CSV IMPORT SETTINGS
    # --------------------------------------
    #
    # Allows users to specify how their file
    # is structured.
    #
    # First row contains headers:
    #     Determines whether column names
    #     exist in the first row.
    #
    # Delimiter:
    #     Defines how columns are separated.
    #
    # Common examples:
    #
    # Comma:
    #     date,amount,category
    #
    # Semicolon:
    #     date;amount;category
    #
    # Tab:
    #     date amount category
    #
    # --------------------------------------


    headers_included = st.checkbox(
        "First row contains headers",
        value=True
    )

    delimiter = st.selectbox(
        "Delimiter",
        [
            "Comma",
            "Tab",
            "Semicolon"
        ]
    )

    # --------------------------------------
    # REQUIRED CSV FORMAT
    # --------------------------------------
    #
    # Provides users with clear guidance on
    # the expected structure of the dataset.
    #
    # This reduces validation errors and helps
    # users prepare compatible CSV files.
    #
    # --------------------------------------

    st.markdown(
        """
    ### Sales Data Requirements

    The current version of the application expects a Sales Data CSV.

    """
    )

    st.info(
        "Use YYYY-MM-DD when possible (for example, 2024-01-31). "
        "Other common formats may be accepted, but dates that cannot be "
        "parsed will be excluded from timeline charts and daily insights."
    )

    st.markdown(
        """
    Required columns:

    | Column | Description | Example |
    |----------|----------|----------|
    | date | Transaction date | 2024-01-01 |
    | amount | Sale amount | 25.48 |
    | category | Product category | Electronics |
    | item | Product name | Mouse |

    ### Example Dataset
    """
    )

    st.code(
        """
    date,amount,category,item
    2024-01-01,25.48,Electronics,Mouse
    2024-01-02,15.99,Food,Coffee
    2024-01-03,63.99,Clothing,Jacket
    2024-01-04,119.99,Electronics,Monitor
    """
    )

    # --------------------------------------
    # FILE UPLOAD
    # --------------------------------------
    #
    # Uploads the dataset and converts it into
    # a Pandas DataFrame.
    #
    # The DataFrame is saved in Session State
    # so it can be reused by later workflow
    # stages without requiring additional
    # uploads.
    #
    # --------------------------------------


    uploaded_file = st.file_uploader(
        "Upload CSV File",
        type=["csv"]
    )

    if uploaded_file is not None:
        # Convert user-friendly delimiter names
        # into values understood by Pandas.
        #
        # Example:
        #
        # "Comma" -> ","
        # "Tab" -> "\t"
        #


        delimiter_map = {
            "Comma": ",",
            "Tab": "\t",
            "Semicolon": ";"
        }

        header_value = (
            0 if headers_included
            else None
        )

        df = pd.read_csv(
            uploaded_file,
            sep=delimiter_map[delimiter],
            header=header_value
        )
        
        # Store uploaded dataset so that it can
        # be accessed by validation, cleaning,
        # dashboard, and insight-generation
        # modules later in the workflow.

        st.session_state.raw_df = df
        st.session_state.cleaning_summary = None

        st.success(
            "Dataset uploaded successfully."
        )
        
        # Once the dataset has been uploaded
        # successfully, the user may proceed
        # to the validation stage.
        #
        # Updating current_step causes the
        # application to render Step 2.

        if st.button(
            "Continue to Validation"
        ):
            st.session_state.current_step = 2
            st.rerun()
            
# ==========================================
# STEP 2 - VALIDATION
# ==========================================
#
# Purpose:
#     Evaluate dataset quality before
#     cleaning and analysis.
#
# Validation checks include:
#
#     - Required columns
#     - Missing values
#     - Data type issues
#
# Results are presented to the user before
# any cleaning operations are performed.
#
# ==========================================
if st.session_state.current_step == 2:

    st.subheader(
        "Step 2 of 4"
    )

    st.title(
        "Validate your dataset"
    )

    df = st.session_state.raw_df
    
    # Required fields for the Sales Data
    # workflow.
    #
    # Future dataset types may require
    # different column definitions.

    required_columns = [
        "date",
        "amount",
        "category",
        "item"
    ]

    # Verify that all mandatory fields
    # exist within the uploaded dataset.
    missing_columns = validate_columns(
        df,
        required_columns
    )

    st.header("Validation Results")

    if missing_columns:
        st.error(
            f"Missing columns: {missing_columns}"
        )
    else:
        st.success(
            "Required columns found."
        )

    # --------------------------------------
    # VALIDATION SUMMARY
    # --------------------------------------
    #
    # Provides a high-level overview of
    # dataset quality before cleaning.
    #
    # This helps users quickly understand
    # the condition of the uploaded file.
    #
    # --------------------------------------

    total_missing = validate_missing(df).sum()

    invalid_dates = (
        count_invalid_dates(df)
        if "date" in df.columns
        else "N/A"
    )
    duplicate_rows = count_duplicates(df)
    currency_values = (
        count_currency_values(df)
        if "amount" in df.columns
        else "N/A"
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Rows",
        len(df)
    )

    col2.metric(
        "Missing Values",
        total_missing
    )

    col3.metric(
        "Invalid Dates",
        invalid_dates
    )

    col4.metric(
        "Duplicates",
        duplicate_rows
    )

    col5.metric(
        "Currency Values",
        currency_values
    )

    if "date" in df.columns and invalid_dates > 0:
        st.warning(
            f"Invalid Dates Found: {invalid_dates}\n\n"
            "These records will be included in KPI calculations "
            "but excluded from time-based visualisations."
        )

    st.subheader(
        "Missing Values"
    )

    st.dataframe(
        # Identify missing or empty values that
        # may affect downstream processing.
        validate_missing(df)
    )

    st.subheader(
        "Data Type Issues"
    )
    
    # Inspect columns for possible data
    # type inconsistencies.
    #
    # Example:
    #     Text appearing in numeric fields.


    issues = validate_types(df)

    if issues:
        st.json(issues)

    else:
        st.success(
            "No type issues detected."
        )


    # Execute the cleaning pipeline.
    #
    # The cleaning module performs:
    #
    #     Missing value handling
    #     Data type correction
    #     Date normalisation
    #     Duplicate removal
    #     Category standardisation
    #
    # The cleaned data is stored in Session
    # State and the user advances to the
    # Dashboard stage.
    invalid_amounts = (
        issues.get("amount") == "Non-numeric values detected"
    )
    if missing_columns:
        st.info("Add the missing required columns before cleaning this dataset.")
    elif invalid_amounts:
        st.error("Correct non-numeric amount values before cleaning this dataset.")

    if st.button(
        "Clean Dataset & Continue",
        disabled=bool(missing_columns or invalid_amounts)
    ):

        rows_before = len(df)
        missing_cells_before = int(df[required_columns].isna().sum().sum())
        invalid_dates_before = count_invalid_dates(df)
        df = df.copy()

        df = clean_missing(df)

        df = clean_types(df)

        df = clean_dates(
            df,
            ["date"]
        )

        rows_before_deduplication = len(df)
        df = clean_duplicates(df)
        duplicates_removed = rows_before_deduplication - len(df)

        rows_before_category_filter = len(df)
        df = normalize_categories(
            df,
            "category"
        )
        category_rows_removed = rows_before_category_filter - len(df)

        if df.empty:
            st.error(
                "No rows remain after cleaning. Check that the dataset "
                "contains usable category values."
            )
        else:
            st.session_state.clean_df = df
            st.session_state.cleaning_summary = {
                "rows_before": rows_before,
                "rows_after": len(df),
                "duplicates_removed": duplicates_removed,
                "category_rows_removed": category_rows_removed,
                "missing_cells_filled": missing_cells_before,
                "invalid_dates": invalid_dates_before,
            }
            st.session_state.current_step = 3
            st.rerun()

# ==========================================
# STEP 3 - DASHBOARD
# ==========================================
#
# Purpose:
#     Generate visual analytics from the
#     cleaned dataset.
#
# Dashboard features:
#
#     - KPI summaries
#     - Category analysis
#     - Sales trend analysis
#     - Revenue distribution
#
# Data source:
#     clean_df
#
# Output:
#     KPI cards
#     Charts
#     Downloadable cleaned dataset
#
# ==========================================

if st.session_state.current_step == 3:

    st.subheader(
        "Step 3 of 4"
    )

    st.title(
        "Business Dashboard"
    )
    
    # Retrieve the cleaned dataset produced
    # during Step 2. The dashboard should
    # always operate on cleaned data rather
    # than the originally uploaded dataset.

    df = st.session_state.clean_df

    # --------------------------------------
    # KPI GENERATION
    # --------------------------------------
    #
    # KPI (Key Performance Indicator)
    # calculations provide a high-level
    # summary of business performance.
    #
    # Current KPIs:
    #
    #     - Total Sales
    #     - Average Sale Value
    #     - Transaction Count
    #     - Top Category
    #
    # Future versions may include:
    #
    #     - Highest Sale
    #     - Lowest Sale
    #     - Revenue Growth
    #
    # --------------------------------------

    kpis = calculate_kpis(df)
    category_df = sales_by_category(df)

    if st.session_state.cleaning_summary:
        summary = st.session_state.cleaning_summary
        st.subheader("Cleaning Summary")
        st.success(
            f"Cleaning complete. Rows: {summary['rows_before']} before, "
            f"{summary['rows_after']} after. "
            f"Duplicates removed: {summary['duplicates_removed']}. "
            f"Rows removed for blank or repeated-header categories: "
            f"{summary['category_rows_removed']}. "
            f"Missing cells filled: {summary['missing_cells_filled']}. "
            f"Invalid or missing dates found: {summary['invalid_dates']}; "
            "these remain unavailable for time-based analysis."
        )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Sales",
        f"${kpis['total_sales']:.2f}"
    )

    col2.metric(
        "Average Sale",
        f"${kpis['average_sale']:.2f}"
    )

    col3.metric(
        "Transactions",
        kpis["transaction_count"]
    )

    col4.metric(
        "Top Category",
        category_df.iloc[0]["category"].title()
    )

    invalid_date_rows = int(df["date"].isna().sum())
    if invalid_date_rows:
        st.info(
            f"{invalid_date_rows} record(s) have invalid or missing dates. "
            "They are included in KPI calculations but excluded from "
            "time-based visualisations."
        )

    st.header("Sales by Category")

    if category_df["amount"].ne(0).any():
        st.bar_chart(
            category_df.set_index("category")
        )
    else:
        st.info("No non-zero sales are available to compare by category.")

    daily_df = sales_by_date(df)

    if daily_df.empty:
        st.header("Daily Sales Trend")
        st.info("No valid dates are available for the daily sales trend.")
    else:
        date_min = daily_df["date"].min()
        date_max = daily_df["date"].max()

        st.header(
            f"Daily Sales Trend ({date_min:%Y-%m-%d} to {date_max:%Y-%m-%d})"
        )

        if daily_df["amount"].ne(0).any():
            st.line_chart(
                daily_df.set_index("date")
            )
        else:
            st.info("No non-zero sales are available for the daily trend.")

    st.header("Revenue Distribution")

    distribution_df = category_distribution(df)

    if kpis["total_sales"] != 0:
        st.bar_chart(
            distribution_df.set_index("category")["percentage"]
        )
    else:
        st.info("Revenue shares are unavailable because total sales net to zero.")
    st.dataframe(
        distribution_df,
        hide_index=True,
        use_container_width=True
    )

    # Download cleaned dataset

    csv_data = df.to_csv(index=False)

    st.download_button(
        label="Download Cleaned CSV",
        data=csv_data,
        file_name="cleaned_data.csv",
        mime="text/csv"
    )

    if st.button(
        "Continue to Insights"
    ):

        st.session_state.current_step = 4

        st.rerun()
        
# ==========================================
# STEP 4 - BUSINESS INSIGHTS
# ==========================================
#
# Purpose:
#     Convert analytical results into
#     human-readable business observations.
#
# Rather than displaying only charts and
# numbers, this stage explains what the
# results mean in plain language.
#
# Features:
#
#     - Business insights
#     - Revenue observations
#     - Category performance analysis
#     - Downloadable insight report
#     - Future placeholders for saving
#       and comparing analyses
#
# Data Source:
#     clean_df
#
# Output:
#     Human-readable business insights
#
# ==========================================

if st.session_state.current_step == 4:

    st.subheader(
        "Step 4 of 4"
    )

    st.title(
        "Business Insights"
    )

    st.write(
        "Review automatically generated "
        "business observations based on "
        "the uploaded dataset."
    )

    # --------------------------------------
    # LOAD CLEAN DATASET
    # --------------------------------------
    #
    # Insights should always be generated
    # from the cleaned dataset created during
    # Step 2.
    #
    # This ensures insight generation uses
    # standardized, validated data.
    #
    # --------------------------------------

    df = st.session_state.clean_df

    invalid_date_rows = int(df["date"].isna().sum())
    if invalid_date_rows:
        st.info(
            f"{invalid_date_rows} record(s) have invalid or missing dates. "
            "They are included in KPI calculations but excluded from "
            "time-based insights."
        )

    # --------------------------------------
    # GENERATE INSIGHTS
    # --------------------------------------
    #
    # The insights module examines KPI
    # results and category performance in
    # order to create readable business
    # observations.
    #
    # Example:
    #
    #     Electronics generated the highest
    #     revenue.
    #
    #     2024-01-04 recorded the highest
    #     daily sales.
    #
    # --------------------------------------

    insights = generate_insights(df)

    # --------------------------------------
    # DISPLAY INSIGHTS
    # --------------------------------------
    #
    # Display each generated insight as a
    # separate bullet point.
    #
    # --------------------------------------

    st.header(
        "Key Findings"
    )

    for insight in insights:

        st.success(
            insight
        )

    # --------------------------------------
    # INSIGHT DOWNLOAD
    # --------------------------------------
    #
    # Convert all generated insights into a
    # downloadable report that can be shared
    # outside the application.
    #
    # --------------------------------------

    insight_text = "\n".join(insights)

    st.header(
        "Export Results"
    )

    st.download_button(
        label="Download Insights Report",
        data=insight_text,
        file_name="business_insights.txt",
        mime="text/plain"
    )

    # --------------------------------------
    # FUTURE FEATURES
    # --------------------------------------
    #
    # These buttons currently act as
    # placeholders for future functionality.
    #
    # Planned future features:
    #
    #     Save Analysis
    #     Compare Analyses
    #     Historical Dashboard Comparison
    #     Forecasting
    #
    # --------------------------------------

    st.header(
        "Future Features"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.button(
            "Save Analysis (Future)"
        )

    with col2:

        st.button(
            "Compare Results (Future)"
        )

    # --------------------------------------
    # WORKFLOW COMPLETE
    # --------------------------------------
    #
    # Inform users that all workflow stages
    # have been completed successfully.
    #
    # --------------------------------------

    st.success(
        "Workflow complete. "
        "Business intelligence analysis "
        "has been generated successfully."
    )       