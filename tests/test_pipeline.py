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

# Load sample dataset
df = pd.read_csv("data/sample_data.csv")

print("Dataset loaded successfully.\n")

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