"""
streamlit_app.py

Business Intelligence Assistant

CMPT 496 Capstone Project

This application allows users to:

1. Upload CSV files
2. Validate data
3. Clean data
4. Generate KPIs
5. Display charts
6. Generate business insights

Author: Carson Lane
"""

# ==========================================
# IMPORTS
# ==========================================

import os
import sys
import pandas as pd
import streamlit as st

# ==========================================
# SESSION STATE
# ==========================================

if "upload_complete" not in st.session_state:
    st.session_state.upload_complete = False

if "validation_complete" not in st.session_state:
    st.session_state.validation_complete = False

if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False

if "dataset_type" not in st.session_state:
    st.session_state.dataset_type = "Sales Data"
    
    
# ==========================================
# RESET ANALYSIS
# ==========================================

if st.button("🔄 Start New Analysis"):

    st.session_state.upload_complete = False
    st.session_state.validation_complete = False
    st.session_state.analysis_complete = False

    st.session_state.dataset_type = "Sales Data"

    st.rerun()
    
# ==========================================
# PROJECT PATH SETUP
# ==========================================
#
# Allows frontend to access backend modules
#
# Project structure:
#
# business-intelligence-assistant/
# ├── backend/
# ├── frontend/
# ├── data/
# └── tests/
#
# ==========================================

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

# ==========================================
# TRANSFORMATION FUNCTIONS
# ==========================================

from backend.transformation import (
    calculate_kpis,
    sales_by_category,
    sales_by_time_period,
    category_distribution
)

# ==========================================
# INSIGHT FUNCTIONS
# ==========================================

from backend.insights import generate_insights
from frontend.charts import render_sales_trend

# ==========================================
# VALIDATION FUNCTIONS
# ==========================================

from backend.validation import (
    validate_columns,
    validate_missing,
    validate_types
)

# ==========================================
# CLEANING FUNCTIONS
# ==========================================

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
    page_title="Business Intelligence Assistant",
    page_icon="📊",
    layout="wide"
)

# ==========================================
# HEADER
# ==========================================

st.title("📊 Business Intelligence Assistant")

st.markdown(
    """
Upload a CSV dataset to automatically generate:

- Key Performance Indicators (KPIs)
- Charts and visualisations
- Business insights

This prototype is being developed as part of CMPT 496.
"""
)

# ==========================================
# DATASET CONFIGURATION
# ==========================================

st.header("Dataset Configuration")

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

if dataset_type != "Sales Data":

    st.warning(
        "Only Sales Data is currently implemented. Other dataset types are planned for future development."
    )

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

# ==========================================
# FILE UPLOAD
# ==========================================

uploaded_file = st.file_uploader(
    "Upload CSV File",
    type=["csv"]
)


# ==========================================
# WORKFLOW STATUS
# ==========================================

st.sidebar.header("Workflow Status")

st.sidebar.write(
    f"Upload: {'✅' if st.session_state.upload_complete else '❌'}"
)

st.sidebar.write(
    f"Validation: {'✅' if st.session_state.validation_complete else '❌'}"
)

st.sidebar.write(
    f"Analysis: {'✅' if st.session_state.analysis_complete else '❌'}"
)

# ==========================================
# PROCESS FILE
# ==========================================

if uploaded_file is not None:

    # --------------------------------------
    # LOAD DATA
    # --------------------------------------

    delimiter_map = {
    "Comma": ",",
    "Tab": "\t",
    "Semicolon": ";"
    }

    # Pandas expects header=None when the uploaded file has no header row.
    header_value = 0 if headers_included else None

    df = pd.read_csv(
        uploaded_file,
        sep=delimiter_map[delimiter],
        header=header_value
    )

    st.session_state.upload_complete = True

    st.success("CSV file uploaded successfully.")


    # --------------------------------------
    # VALIDATION
    # --------------------------------------

    st.header("✅ Validation Results")

    required_columns = [
        "date",
        "amount",
        "category",
        "item"
    ]

    missing_columns = validate_columns(
        df,
        required_columns
    )
    

    if missing_columns:
        st.error(
            f"Missing required columns: {missing_columns}"
        )
        st.stop()

    st.success("Required columns found.")
    st.session_state.validation_complete = True

    st.subheader("Missing Values")

    st.dataframe(
        validate_missing(df).rename("Missing Count")
    )

    st.subheader("Data Type Issues")

    type_issues = validate_types(df)

    if type_issues:
        st.json(type_issues)
    else:
        st.write("No type issues detected.")

    # --------------------------------------
    # CLEANING PIPELINE
    # --------------------------------------

    st.header("🧹 Data Cleaning")

    df = clean_missing(df)

    df = clean_types(df)

    df = clean_dates(df, ["date"])

    df = clean_duplicates(df)

    df = normalize_categories(
        df,
        "category"
    )

    st.success("Dataset cleaned successfully.")
    
    st.session_state.analysis_complete = True

    # --------------------------------------
    # DEBUG INFO
    # --------------------------------------

    with st.expander("Debug Information"):

        st.write("Amount Column Type:")

        st.code(str(df["amount"].dtype))

        st.write("Preview of cleaned dataset:")

        st.dataframe(df.head())

    # --------------------------------------
    # KPI SECTION
    # --------------------------------------

    st.header("📈 Sales summary")

    kpis = calculate_kpis(df)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total sales",
        f"${kpis['total_sales']:.2f}"
    )

    col2.metric(
        "Average sale",
        f"${kpis['average_sale']:.2f}"
    )

    col3.metric(
        "Sales records",
        kpis["transaction_count"]
    )

    # --------------------------------------
    # CATEGORY CHART
    # --------------------------------------

    st.header("📊 Sales by product category (dollars)")

    category_df = sales_by_category(df)

    st.bar_chart(
        category_df.set_index("category")
    )

    # --------------------------------------
    # SALES OVER TIME
    # --------------------------------------

    st.header("📅 Sales Over Time")

    trend_df, trend_frequency = sales_by_time_period(df)

    if trend_df.empty:
        st.info("No valid dates are available for a sales trend.")
    else:
        frequency_labels = {
            "day": "Daily",
            "week": "Weekly",
            "month": "Monthly",
        }
        st.subheader(f"{frequency_labels[trend_frequency]} Sales Trend")
        period_name = {
            "day": "day",
            "week": "week",
            "month": "month",
        }[trend_frequency]
        st.caption(
            f"Each point is the sales total for one {period_name}. "
            "The chart groups sales by day, week, or month based on the "
            "dates in your file."
        )
        render_sales_trend(trend_df, trend_frequency)

    # --------------------------------------
    # REVENUE DISTRIBUTION
    # --------------------------------------

    st.header("🥧 Share of total sales by category")

    distribution_df = category_distribution(df)

    st.dataframe(
        distribution_df.rename(
            columns={
                "category": "Category",
                "amount": "Sales total ($)",
                "percentage": "Share of total (%)",
            }
        )
    )

    # --------------------------------------
    # BUSINESS INSIGHTS
    # --------------------------------------

    st.header("💡 Your sales insights")

    insights = generate_insights(df)

    for insight in insights:
        st.write(f"• {insight}")
        
    # ======================================
    # DOWNLOAD RESULTS
    # ======================================

    st.header("📥 Download cleaned data and insights")

    csv_data = df.to_csv(index=False)

    st.download_button(
        label="Download Cleaned CSV",
        data=csv_data,
        file_name="cleaned_data.csv",
        mime="text/csv"
    )

    insight_text = "\n".join(insights)

    st.download_button(
        label="Download Insights",
        data=insight_text,
        file_name="business_insights.txt",
        mime="text/plain"
    )    

    # --------------------------------------
    # DATA PREVIEW
    # --------------------------------------

    with st.expander(
        "View Cleaned Dataset"
    ):
        st.dataframe(df)

# ==========================================
# NO FILE UPLOADED
# ==========================================

else:

    st.info(
        "Upload a CSV file to begin analysis."
    )