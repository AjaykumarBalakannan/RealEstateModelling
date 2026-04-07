"""
=============================================================
 Sage Ventures – Multifamily Analytics
 MASTER PIPELINE — Runs everything in one command
 Run:  python run_pipeline.py
=============================================================
"""

import subprocess
import sys
import time
import os

def run(script, label):
    print(f"\n{'='*55}")
    print(f"  ▶  {label}")
    print(f"{'='*55}")
    start = time.time()
    result = subprocess.run(
        [sys.executable, script],
        capture_output=False
    )
    elapsed = round(time.time() - start, 1)
    if result.returncode == 0:
        print(f"  ✓  Completed in {elapsed}s")
    else:
        print(f"  ✗  FAILED — check errors above")
        sys.exit(1)

def main():
    print("\n" + "="*55)
    print("  SAGE VENTURES — FULL ANALYTICS PIPELINE")
    print("  Automated End-to-End Run")
    print("="*55)
    print(f"  Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    start_total = time.time()

    run("generate_data.py",       "Phase 1 — Data Generation (SQLite + CSVs)")
    run("feature_engineering.py", "Phase 2 — Feature Engineering (Pandas)")
    run("adhoc_analysis.py",      "Phase 3 — Ad Hoc Analysis (5 reports)")
    run("excel_report.py",        "Phase 4 — Excel Report (7 sheets)")
    run("visualize.py",           "Phase 5 — Visualizations (10 charts)")

    total = round(time.time() - start_total, 1)

    print("\n" + "="*55)
    print("  PIPELINE COMPLETE ✓")
    print(f"  Total runtime: {total}s")
    print("="*55)
    print("""
  Outputs generated:
  data/
    ├── sage_ventures.db         SQLite database
    ├── properties.csv           Raw tables
    ├── units.csv
    ├── tenants.csv
    ├── rent_roll.csv
    ├── maintenance.csv
    ├── occupancy_monthly.csv
    ├── feat_property_kpis.csv   Feature engineered
    ├── feat_tenants.csv
    ├── feat_units.csv
    ├── feat_maintenance.csv
    └── feat_rent_roll.csv

  outputs/
    ├── adhoc/                   5 ad hoc reports
    ├── charts/                  10 automated charts
    └── SageVentures_Analytics_Report_YYYYMMDD.xlsx
    """)
    print("  Next step: open Power BI Desktop")
    print("  → load CSVs from data/ folder")
    print("="*55)

if __name__ == "__main__":
    main()
