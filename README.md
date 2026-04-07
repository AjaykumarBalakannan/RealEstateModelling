# Sage Ventures — Multifamily Analytics Pipeline

> End-to-end analytics workflow simulating the data infrastructure,
> reporting, and business intelligence of a multifamily real estate portfolio.
> Built to demonstrate SQL, Python, Power BI, and Excel automation skills
> for a Junior Data Analyst role in multifamily operations.

---

## Run the Full Pipeline (One Command)

```bash
pip install faker pandas numpy openpyxl matplotlib seaborn
python run_pipeline.py
```

---

## Architecture

```
run_pipeline.py                  ← Master automation script
│
├── Phase 1: generate_data.py    → SQLite DB + raw CSVs
├── Phase 2: feature_engineering.py → 15+ engineered features
├── Phase 3: adhoc_analysis.py   → 5 business reports
├── Phase 4: excel_report.py     → 7-sheet Excel workbook
└── Phase 5: visualize.py        → 10 automated charts
```

---

## Data Model

```
properties ──< units ──< tenants ──< rent_roll
properties ──< maintenance
properties ──< occupancy_monthly
```

---

## Tech Stack

Python | SQLite | SQL | Pandas | openpyxl | Matplotlib | Power BI

---

## Key Findings

- Portfolio avg occupancy: 67% (target 93%)
- Annual loss-to-lease: $2.14M
- Delinquency exposure: $19,864 (current month)
- SLA breaches: 533 open tickets past threshold
- Top property: Fieldside Grande Ph1 — Grade A

---

*Built as a portfolio project demonstrating multifamily analytics and BI automation.*
