"""
run_pipeline.py

runs all 5 phases in order with one command.
stops immediately if any phase fails so you know what broke.

run:  python run_pipeline.py
"""

import subprocess
import sys
import time


def run(script, label):
    print(f"\n[{label}]")
    start  = time.time()
    result = subprocess.run([sys.executable, script])
    elapsed = round(time.time() - start, 1)

    if result.returncode != 0:
        print(f"  failed — check errors above")
        sys.exit(1)

    print(f"  done in {elapsed}s")


def main():
    print("sage ventures — full analytics pipeline")
    print(f"started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    t0 = time.time()

    run("generate_data.py",       "1/5 data generation")
    run("feature_engineering.py", "2/5 feature engineering")
    run("adhoc_analysis.py",      "3/5 ad hoc analysis")
    run("excel_report.py",        "4/5 excel report")
    run("visualize.py",           "5/5 visualizations")

    total = round(time.time() - t0, 1)
    print(f"\nall done in {total}s")
    print("""
outputs:
  data/sage_ventures.db          sqlite database
  data/feat_*.csv                feature engineered tables
  outputs/adhoc/                 5 ad hoc reports
  outputs/charts/                10 charts (png)
  outputs/SageVentures_*.xlsx    excel report

next: open power bi desktop and load csvs from data/
    """)


if __name__ == "__main__":
    main()
