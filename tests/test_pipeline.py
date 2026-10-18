"""
test_pipeline.py

Tests the entire Business Intelligence pipeline.

Pipeline:

CSV
 ↓
Transformation
 ↓
Insights

This file is used for development testing
before integrating Streamlit.
"""

import sys
import os
import pandas as pd

# Add project root to Python path
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

# Import project modules
from backend.cleaning import (
    clean_missing,
    clean_types,
    clean_dates,
    clean_duplicates,
    normalize_categories
)

from backend.transformation import (
    calculate_kpis,
    sales_by_category,
    sales_by_date,
    category_distribution
)

from backend.insights import generate_insights


print("\n===================================")
print("BUSINESS INTELLIGENCE PIPELINE TEST")
print("===================================\n")

# Run this script from the project root so the relative data path resolves.
df = pd.read_csv("data/sales/sales_sample_10.csv")

print("Dataset loaded successfully.\n")

# Apply the same cleaning steps used by the application before analysis.
df = clean_missing(df)
df = clean_types(df)
df = clean_dates(df, ["date"])
df = clean_duplicates(df)
df = normalize_categories(df, "category")

# ----------------------------
# KPI TEST
# ----------------------------

print("=== KPI SUMMARY ===")
print(calculate_kpis(df))

# ----------------------------
# CATEGORY TEST
# ----------------------------

print("\n=== SALES BY CATEGORY ===")
print(sales_by_category(df))

# ----------------------------
# DATE TEST
# ----------------------------

print("\n=== SALES BY DATE ===")
print(sales_by_date(df))

# ----------------------------
# DISTRIBUTION TEST
# ----------------------------

print("\n=== CATEGORY DISTRIBUTION ===")
print(category_distribution(df))

# ----------------------------
# INSIGHTS TEST
# ----------------------------

print("\n=== BUSINESS INSIGHTS ===")

for insight in generate_insights(df):
    print(f"• {insight}")

print("\nPipeline test completed successfully.")