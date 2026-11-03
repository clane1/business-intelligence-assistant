# Business Intelligence Assistant for Small Enterprises

- **Author:** Carson Lane
- **Course:** CMPT 496
- **Document status:** Working report draft

> This draft follows the structure and subject matter of the supplied project
> report PDF, updated to describe the current implementation. Before submission,
> verify all citations and replace the testing notes with results from the final
> evaluation.

## Abstract

Small enterprises may collect useful business data without having the
specialized tools or expertise needed to prepare and interpret it. This project
develops a lightweight Business Intelligence Assistant that guides users
through uploading Sales, Inventory, or Expenses data, reviewing validation findings,
cleaning supported issues, and exploring dataset-specific metrics and
visualizations. The prototype is implemented in Python with Streamlit and
pandas. Its workflows include validation, data previews, user-selected
cleaning, dashboards, and generated business insights.

The current application supports Sales CSV files containing `date`, `amount`,
`category`, and `item`; Inventory CSV files containing `item`, `category`,
`quantity`, and `unit_cost`, with optional `reorder_level` and `last_updated`;
and Expenses CSV files containing `date`, `amount`, `category`, and `vendor`.
Validation distinguishes absent required columns from empty cells;
unreadable required numeric values block cleaning, while supported missing
values can be handled through explicit choices. The app does not support
arbitrary business datasets, database integration, persistent uploads, or
forecasting. Development testing uses clean, messy, and structurally invalid
fixtures for all three supported workflows. This report describes the design,
implementation, testing, limitations, and possible future development.

**Keywords:** business intelligence, small enterprises, data quality, data
cleaning, sales analytics, inventory analytics, expense analytics,
self-service analytics

## Table of Contents

1. [Introduction](#1-introduction)
   1. [Literature Review](#11-literature-review)
   2. [Goals of the Project](#12-goals-of-the-project)
2. [Methodology](#2-methodology)
   1. [Overview](#21-overview)
   2. [Application](#22-application)
      1. [Software](#221-software)
      2. [Software Design](#222-software-design)
3. [Results](#3-results)
   1. [Testing](#31-testing)
   2. [Conclusions](#32-conclusions)
   3. [Future Work](#33-future-work)
4. [References](#4-references)
5. [Appendices](#5-appendices)

## 1. Introduction

Business Intelligence (BI) and Business Intelligence and Analytics (BI&A)
support organizational decision-making by helping users collect, transform,
analyze, and visualize business data [1]. Small and medium-sized enterprises
(SMEs) may benefit from these capabilities, but can face cost, infrastructure,
and expertise barriers when adopting traditional BI platforms [2], [3].

Many organizations already store operational information in CSV files.
However, missing values, inconsistent formatting, duplicate records, and
invalid dates can make direct analysis difficult and may reduce confidence in
results. A focused application that explains validation findings and
automates a limited set of cleaning steps can help make basic analysis more
approachable.

This project implements guided BI workflows for Sales, Inventory, and
Expenses CSV files.
Users select a dataset type, upload a file, inspect its structure and
validation results, apply supported cleaning choices, and explore
dataset-specific summaries and generated insights. The application is
intended as a prototype and is not a general-purpose BI platform.

### 1.1 Literature Review

BI&A has developed alongside the growing availability of business data and
the need to support evidence-based decisions [1]. Research on SMEs discusses
potential benefits including improved operational performance, planning, and
competitiveness. Llave's review surveys BI&A components used in SMEs [2],
while Tsiu et al. review data-mining and BI applications and their potential
competitive advantages [3].

Adoption remains challenging for smaller organizations. Limited resources,
technical expertise, infrastructure, and organizational readiness may
constrain implementation [2]–[5]. These issues motivate self-service BI
(SSBI), which aims to let non-specialist users perform analysis without
depending on a dedicated BI team. Research on SSBI highlights usability,
accessibility, visualization, and training as important considerations [8],
[9].

Data quality is also essential for useful analysis. Dirty data can include
missing values, duplicate records, invalid entries, contradictions, and
inconsistent representations [10]. Data-cleaning research describes
validation, standardization, deduplication, and transformation as important
preparation tasks [11]. Broader information-quality work emphasizes
dimensions such as accuracy, completeness, and consistency [12].

This project applies these concepts in deliberately narrow and transparent
Sales, Inventory, and Expenses workflows: it checks defined data contracts, reports
selected quality issues, cleans supported cases, and calculates descriptive
summaries. It demonstrates a working prototype rather than resolving the
broader organizational challenges of BI adoption.

> **Citation work required:** References [4] and [5] in the supplied PDF do
> not identify authors, publication venues, years, or other publication
> details. Verify the intended sources and complete those citations, or remove
> them and their in-text citations. Verify the bibliographic details of all
> references before submission.

### 1.2 Goals of the Project

The goal is to implement a lightweight Business Intelligence Assistant that
helps users analyze supported business datasets through guided self-service
workflows. The project objectives are to:

1. Accept Sales, Inventory, and Expenses data from CSV uploads.
2. Check uploaded data for required columns and selected quality issues.
3. Show an uploaded-data preview and explain validation findings, including
   absent required columns and examples of unreadable values.
4. Clean supported issues and summarize the changes.
5. Present dataset-specific metrics, category summaries, and visualizations.
6. Generate human-readable observations from the cleaned data.
7. Test each workflow using representative valid, messy, and invalid files.

Sales requires `date`, `amount`, `category`, and `item`. Inventory requires
`item`, `category`, `quantity`, and `unit_cost`; `reorder_level` enables
low-stock checks and `last_updated` is optional. Expenses requires `date`,
`amount`, `category`, and `vendor`. Other business data types, database
storage, and forecasting are not current capabilities.

## 2. Methodology

### 2.1 Overview

The application is a Streamlit web application that processes uploaded CSV
data in memory using pandas. Users select Sales, Inventory, or Expenses and
follow a four-stage workflow:

1. **Upload:** The user selects a dataset type and uploads a matching CSV.
2. **Validation:** The application checks required columns, reports selected
   quality metrics, and displays the dataset shape and a preview. If required
   columns are missing or required numeric values are unreadable, cleaning is
   blocked and the user is directed back to upload after correcting the source.
   Empty cells in supported columns are counted separately.
3. **Cleaning:** The application applies supported cleaning operations and
   user-selected fixes, then displays a summary and preview.
4. **Analysis:** The application calculates dataset-specific metrics and
   aggregations, displays charts, and generates insights.

Uploaded and cleaned data are held in Streamlit session state for the
interactive workflow. The current prototype does not store datasets in a
database or provide persistent upload storage. The application architecture
and data flow are described in [the architecture document](./architecture.md).

### 2.2 Application

#### 2.2.1 Software

Python is the primary programming language. pandas is used for CSV data
handling, validation, cleaning, transformation, and aggregation. Streamlit
provides the web interface, workflow controls, and metrics. Altair defines
the date charts, which are rendered in Streamlit. Plotly and
Scikit-learn-based forecasting are not part of the implemented application.
Git and GitHub are used for version control.

#### 2.2.2 Software Design

The application is organized into a presentation layer and backend modules
with separate responsibilities:

- `frontend/streamlit_app_v2.py` implements the Sales upload and staged
  workflow, and routes dataset selection to the other workflow pages.
- `frontend/inventory_pages.py` implements the Inventory upload, check,
  dashboard, and insights screens and the shared dataset-type selector.
- `frontend/expenses_pages.py` implements the Expenses upload, check,
  dashboard, and insights screens.
- `backend/load_csv.py` parses CSV files using the selected delimiter and
  header option without imposing a dataset schema.
- `backend/csv_loader.py` applies each dataset's headerless column order and
  reports incompatible layouts before validation.
- `backend/column_mapping.py` suggests and applies mappings from custom
  header names to required Sales, Inventory, or Expenses fields.
- `backend/validation.py` supports Sales required-column, amount/date, missing
  value, and duplicate checks; `backend/inventory.py` provides Inventory
  numeric checks, recommendations, cleaning, analysis, and insights.
- `backend/expenses.py` reuses compatible Sales cleaning and validation
  behavior while providing expense KPIs, vendor analysis, and spending
  insights.
- `backend/cleaning.py` handles Sales missing-value defaults, amount
  conversion, date parsing, duplicate removal, and category normalization.
- `backend/transformation.py` calculates Sales KPIs and category/date
  aggregations.
- `backend/insights.py` creates human-readable observations from transformed
  Sales data.
- `backend/cleaning_report.py` creates downloadable cleaning reports for all
  supported dataset types.

##### Sales workflow

Sales requires `date`, `amount`, `category`, and `item`. An absent required
column is a schema error: validation names it, blocks cleaning, and directs
the user to correct and upload the CSV again. Non-empty Sales amounts that
cannot be converted to numbers are not guessed or silently replaced;
validation identifies examples and blocks cleaning. Sales dates that are
missing or unreadable are reported but do not block cleaning: those records
remain in non-date totals and are excluded from time-based analysis.

##### Inventory workflow

The Inventory workflow requires `item`, `category`, `quantity`, and
`unit_cost`. The optional `reorder_level` column enables low-stock checks, and
`last_updated` can be retained as an optional descriptive field. Users can
map custom headers before validation. An absent required column is named and
blocks cleaning. Non-empty quantity or unit-cost values that cannot be
converted to numbers also block cleaning; missing quantities and costs can be
filled independently. Negative values are retained unless the user chooses
to remove affected rows.
The dashboard calculates inventory value as `quantity × unit_cost` and
summarizes units, unique items, value by category and item, and low stock when
reorder levels are available.

##### Expenses workflow

Expenses requires `date`, `amount`, `category`, and `vendor`. It uses the same
review and cleaning patterns as Sales for missing or unreadable amounts,
duplicates, invalid dates, currency formatting, and category spelling. The
dashboard reports total and average expenses, record count, largest expense
category, expenses by category and date, category share, and vendor totals.
Insights describe the leading category share, highest trend period, and
largest spending vendor.

All three workflows include cleaning summaries and downloads. Sales provides
revenue-oriented KPIs, category and time-trend analysis; Inventory calculates
value as `quantity × unit_cost`; Expenses summarizes spending and vendors.
Uploads and analyses are not persisted, and arbitrary schemas and predictive
forecasting are not implemented. Detailed behavior and limitations are
documented in [the architecture document](./architecture.md).

## 3. Results

The implemented prototype provides end-to-end paths from Sales, Inventory,
and Expenses CSV uploads to descriptive analysis. Users can see validation
findings and previews before and after cleaning. Dataset-specific dashboards
show revenue metrics and trends, inventory value and low stock, or expense
category and vendor spending. Missing required columns are reported by name,
prevent cleaning, and provide a route back to upload. Unreadable required
numeric values block cleaning; unreadable Sales and Expenses dates remain in
totals while being excluded from date-based results.

These results demonstrate the implemented prototype and its tested scenarios;
they do not establish usability across a broad user population or measurable
business impact. Invalid dates cannot be reliably corrected without more
information, and the current descriptive analytics should not be presented
as forecasting or causal analysis.

### 3.1 Testing

Sales, Inventory, and Expenses fixtures cover clean and messy datasets,
data-quality issues, alternate headers, headerless files, blocking schema and
value errors, and analytical edge cases such as zero revenue and low stock.
The complete fixture inventories and manual test procedures are in
[the testing document](./testing.md).

The current fixture set is summarized below.

| Fixture collection | Test scenarios |
| --- | --- |
| `data/sales/` | Clean and messy sales data, custom and headerless columns, duplicates, missing and invalid values, returns, category spelling, trend spans, and zero-revenue analysis. |
| `data/inventory/` | 100-row clean and messy datasets, standalone missing/negative/duplicate cases, low-stock boundaries, custom and headerless columns, blocking errors, and zero-value analysis. |
| `data/expenses/` | 100-row clean and messy datasets, missing and formatted amounts, invalid dates, duplicates, category spelling, required-column failures, custom and headerless columns, and zero-total analysis. |

On November 2, 2026, the full automated regression suite passed all 170 tests,
and the separate Sales pipeline smoke check completed successfully. The
regression suite exercises all three dataset workflows, including actual
upload and custom-header mapping, cleaning choices, reports, dashboards,
insights, and fixture scenarios. These results are development verification,
not a formal usability study or evidence of business impact. Record the final
Python and package versions and rerun the checks before submission.

For the final evaluation, document:

- The Python and package versions and the commands used.
- Results for each fixture, including expected and observed behavior.
- Any automated test output and failures.
- Screenshots of the main workflow, numbered and captioned if included.
- The scope and limitations of the fixture-based evaluation.
- User-evaluation participants and results, if a user study is conducted.

The test commands and fixture inventory are documented in
[Testing Sales, Inventory, and Expenses](./testing.md).

### 3.2 Conclusions

The project implements a focused assistant for Sales, Inventory, and Expenses
CSV data.
It combines validation, user-selected cleaning, transparent previews,
descriptive metrics, visualizations, and generated insights in guided
workflows. Validation distinguishes missing schema fields from empty cells,
explains which source values require correction, and prevents analysis when
required columns or numeric values are invalid. Automated fixture and UI
checks cover each workflow and its supported behavior.

The system remains limited to three defined CSV schemas and a specific set of
cleaning and analysis rules. It does not currently support persistent
database-backed storage, arbitrary datasets, or forecasting.
Fixture testing verifies selected technical scenarios but does not alone
demonstrate usability or improved business decisions.

### 3.3 Future Work

Potential future work includes evaluating the interface with users, supporting
additional explicitly defined business-data schemas, and refining dashboard
visualizations. Other possibilities include
persistent analysis storage and forecasting with historical data. Each
extension would require a clear data contract and evaluation plan. These
features are proposed future work and are not implemented in the current
prototype.

## 4. References

[1] H. Chen, R. H. L. Chiang, and V. C. Storey, “Business Intelligence and
Analytics: From Big Data to Big Impact,” *MIS Quarterly*, vol. 36, no. 4,
pp. 1165–1188, 2012.

[2] M. R. Llave, “Business Intelligence and Analytics in Small and
Medium-Sized Enterprises: A Systematic Literature Review,” *Procedia Computer
Science*, vol. 121, pp. 194–205, 2017.

[3] S. V. Tsiu, M. Ngobeni, L. Mathabela, and B. Thango, “Applications and
Competitive Advantages of Data Mining and Business Intelligence in SMEs
Performance: A Systematic Review,” *Businesses*, vol. 5, no. 2, 2025.

[4] “Business Intelligence Adoption for Small and Medium Enterprises:
Conceptual Framework.” **Incomplete citation; publication details required.**

[5] “Systematic Review of Factors Influencing Adoption of Business
Intelligence Systems.” **Incomplete citation; publication details required.**

[6] S. Arunatileka, A. Ginige, A. Hol, and R. Lawson, “SMEs Gaining
Competitive Advantage Through eCollaboration,” in *Proceedings of ACIS 2005*,
Sydney, Australia, 2005.

[7] D. Arnott and M. Gibson, “The Evaluation of Business Intelligence: A Case
Study in a Major Financial Institution,” in *Proceedings of ACIS 2005*,
Sydney, Australia, 2005.

[8] M. Durra and G. Al-Naymat, “Self-Service Business Intelligence: Meeting
User Needs in a Data-Rich World,” in *2023 24th International Arab Conference
on Information Technology (ACIT)*, 2023.

[9] C. Lennerholt, J. van Laere, and E. Söderström, “Implementation Challenges
of Self-Service Business Intelligence: A Literature Review,” in *Proceedings
of the Hawaii International Conference on System Sciences*, 2018.

[10] W. Kim, B.-J. Choi, E.-K. Hong, S.-K. Kim, and D. Lee, “A Taxonomy of
Dirty Data,” *Data Mining and Knowledge Discovery*, vol. 7, pp. 81–99, 2003.

[11] E. Rahm and H. H. Do, “Data Cleaning: Problems and Current Approaches,”
*IEEE Data Engineering Bulletin*, vol. 23, no. 4, pp. 3–13, 2000.

[12] C. Batini and M. Scannapieco, *Data and Information Quality: Dimensions,
Principles and Techniques*. Springer, 2016.

## 5. Appendices

- **Appendix A – Code:** Identify the final repository and the relevant
  frontend and backend modules.
- **Appendix B – Diagrams:** Include the architecture/workflow diagram and
  relevant interface figures, with captions and references in the report.
- **Appendix C – Test Data:** Describe the Sales, Inventory, and Expenses
  fixture scenarios and link to the repository's [Sales](../data/sales/),
  [Inventory](../data/inventory/), and [Expenses](../data/expenses/) test
  data. Avoid reproducing large CSV files in the report.
