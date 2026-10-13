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
    validate_types
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

    with st.expander(
        "View Required CSV Format"
    ):

        st.code(
            """
date,amount,category,item
2024-01-01,25.48,Electronics,Mouse
2024-01-02,15.99,Food,Coffee
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
    if st.button(
        
        "Clean Dataset & Continue"
    ):

        df = clean_missing(df)

        df = clean_types(df)

        df = clean_dates(
            df,
            ["date"]
        )

        df = clean_duplicates(df)

        df = normalize_categories(
            df,
            "category"
        )

        st.session_state.clean_df = df

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
    #
    # Future versions may include:
    #
    #     - Highest Sale
    #     - Lowest Sale
    #     - Top Category
    #     - Revenue Growth
    #
    # --------------------------------------

    kpis = calculate_kpis(df)

    col1, col2, col3 = st.columns(3)

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

    st.header("Sales by Category")

    category_df = sales_by_category(df)

    st.bar_chart(
        category_df.set_index("category")
    )

    st.header("Sales Over Time")

    daily_df = sales_by_date(df)

    st.line_chart(
        daily_df.set_index("date")
    )

    st.header("Revenue Distribution")

    distribution_df = category_distribution(df)

    st.dataframe(distribution_df)

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