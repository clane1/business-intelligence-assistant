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
    sales_by_date,
    category_distribution
)

# ==========================================
# INSIGHT FUNCTIONS
# ==========================================

from backend.insights import generate_insights

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
# FILE UPLOAD
# ==========================================

uploaded_file = st.file_uploader(
    "Upload CSV File",
    type=["csv"]
)

# ==========================================
# PROCESS FILE
# ==========================================

if uploaded_file is not None:

    # --------------------------------------
    # LOAD DATA
    # --------------------------------------

    df = pd.read_csv(uploaded_file)

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

    # --------------------------------------
    # DEBUG INFO
    # --------------------------------------

    st.subheader("Debug Information")

    st.write("Amount Column Type:")

    st.code(str(df["amount"].dtype))

    st.write("Preview of cleaned dataset:")

    st.dataframe(df.head())

    # --------------------------------------
    # KPI SECTION
    # --------------------------------------

    st.header("📈 Key Performance Indicators")

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

    # --------------------------------------
    # CATEGORY CHART
    # --------------------------------------

    st.header("📊 Sales by Category")

    category_df = sales_by_category(df)

    st.bar_chart(
        category_df.set_index("category")
    )

    # --------------------------------------
    # SALES OVER TIME
    # --------------------------------------

    st.header("📅 Sales Over Time")

    daily_df = sales_by_date(df)

    st.line_chart(
        daily_df.set_index("date")
    )

    # --------------------------------------
    # REVENUE DISTRIBUTION
    # --------------------------------------

    st.header("🥧 Revenue Distribution")

    distribution_df = category_distribution(df)

    st.dataframe(distribution_df)

    # --------------------------------------
    # BUSINESS INSIGHTS
    # --------------------------------------

    st.header("💡 Business Insights")

    insights = generate_insights(df)

    for insight in insights:
        st.write(f"• {insight}")

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