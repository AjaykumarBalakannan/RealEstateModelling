"""
sage_ventures_docs.py

Quick script to auto-generate the monthly analytics doc.
Pulls live numbers straight from the DB so i dont have
to update it manually every month.

Ajaykumar Balakannan | ajayport@umd.edu
Last updated: Apr 2026
"""

import sqlite3
import pandas as pd
import os
from datetime import date

# paths
DB  = "data/sage_ventures.db"
OUT = "outputs/SageVentures_Technical_Documentation.md"
os.makedirs("outputs", exist_ok=True)

today = date.today().strftime("%B %d, %Y")


def connect():
    return sqlite3.connect(DB)


# pull the high-level numbers for the summary section
def portfolio_stats(conn):
    stats = {}

    stats["n_props"]    = conn.execute("SELECT COUNT(*) FROM properties").fetchone()[0]
    stats["n_units"]    = conn.execute("SELECT COUNT(*) FROM units").fetchone()[0]
    stats["n_tenants"]  = conn.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
    stats["n_payments"] = conn.execute("SELECT COUNT(*) FROM rent_roll").fetchone()[0]
    stats["n_tickets"]  = conn.execute("SELECT COUNT(*) FROM maintenance").fetchone()[0]

    stats["avg_occ"] = conn.execute(
        "SELECT ROUND(AVG(occupancy_rate),1) FROM occupancy_monthly"
    ).fetchone()[0]

    stats["avg_mkt_rent"] = conn.execute(
        "SELECT ROUND(AVG(market_rent),0) FROM units"
    ).fetchone()[0]

    # total rent from active tenants only
    stats["monthly_rev"] = conn.execute(
        "SELECT ROUND(SUM(monthly_rent),0) FROM tenants WHERE status='Active'"
    ).fetchone()[0]

    last = conn.execute("SELECT MAX(period_month) FROM rent_roll").fetchone()[0]
    stats["last_month"] = last

    stats["coll_rate"] = conn.execute(
        f"SELECT ROUND(SUM(amount_paid)*100.0/SUM(amount_due),1) FROM rent_roll WHERE period_month='{last}'"
    ).fetchone()[0]

    # these come from feature_engineering.py output
    # if that hasnt been run yet just skip them
    try:
        stats["open_tickets"] = conn.execute(
            "SELECT SUM(is_open) FROM feat_maintenance"
        ).fetchone()[0]
        stats["sla_breaches"] = conn.execute(
            "SELECT SUM(sla_breach) FROM feat_maintenance"
        ).fetchone()[0]
    except Exception:
        stats["open_tickets"] = "N/A - run feature_engineering.py"
        stats["sla_breaches"] = "N/A - run feature_engineering.py"

    return stats


# property level rollup
def property_table(conn):
    q = """
    SELECT
        p.name,
        p.city,
        p.property_type,
        p.total_units,
        COUNT(t.tenant_id)                               AS occupied,
        ROUND(COUNT(t.tenant_id)*100.0/p.total_units, 1) AS occ_pct,
        ROUND(AVG(u.market_rent), 0)                     AS avg_mkt_rent,
        ROUND(SUM(t.monthly_rent), 0)                    AS monthly_rev
    FROM properties p
    JOIN units u
        ON p.property_id = u.property_id
    LEFT JOIN tenants t
        ON u.unit_id = t.unit_id AND t.status = 'Active'
    GROUP BY p.property_id
    ORDER BY monthly_rev DESC
    """
    return pd.read_sql(q, conn)


# top 10 delinquent accounts this month
def delinquency_table(conn):
    last = conn.execute("SELECT MAX(period_month) FROM rent_roll").fetchone()[0]
    q = f"""
    SELECT
        p.name                                 AS property,
        t.full_name                            AS tenant,
        u.unit_type,
        ROUND(r.amount_due - r.amount_paid, 0) AS balance_owed,
        r.status
    FROM rent_roll r
    JOIN tenants    t ON r.tenant_id   = t.tenant_id
    JOIN units      u ON r.unit_id     = u.unit_id
    JOIN properties p ON r.property_id = p.property_id
    WHERE r.status IN ('Delinquent', 'Partial')
      AND r.period_month = '{last}'
    ORDER BY balance_owed DESC
    LIMIT 10
    """
    return pd.read_sql(q, conn)


# 30/60/90 day lease expiration counts
def lease_buckets(conn):
    row = conn.execute("""
    SELECT
        SUM(CASE WHEN julianday(lease_end) - julianday('now') BETWEEN 0  AND 30 THEN 1 ELSE 0 END),
        SUM(CASE WHEN julianday(lease_end) - julianday('now') BETWEEN 31 AND 60 THEN 1 ELSE 0 END),
        SUM(CASE WHEN julianday(lease_end) - julianday('now') BETWEEN 61 AND 90 THEN 1 ELSE 0 END),
        ROUND(SUM(
            CASE WHEN julianday(lease_end) - julianday('now') BETWEEN 0 AND 90
            THEN monthly_rent ELSE 0 END
        ), 0)
    FROM tenants WHERE status = 'Active'
    """).fetchone()
    return {"d30": int(row[0]), "d60": int(row[1]),
            "d90": int(row[2]), "at_risk": row[3]}


# maintenance spend by category
def maint_cost(conn):
    q = """
    SELECT
        category,
        COUNT(ticket_id)                                AS tickets,
        SUM(CASE WHEN status='Open' THEN 1 ELSE 0 END)  AS open_tickets,
        ROUND(AVG(
            CASE WHEN close_date IS NOT NULL
            THEN julianday(close_date) - julianday(open_date) END
        ), 1)                                           AS avg_days_to_close,
        ROUND(SUM(cost), 0)                             AS total_cost
    FROM maintenance
    GROUP BY category
    ORDER BY total_cost DESC
    """
    return pd.read_sql(q, conn)


def to_md(df):
    return df.to_markdown(index=False)


def main():
    conn = connect()

    s     = portfolio_stats(conn)
    props = property_table(conn)
    delq  = delinquency_table(conn)
    lp    = lease_buckets(conn)
    maint = maint_cost(conn)

    doc = f"""# Sage Ventures — Multifamily Analytics
## Technical Documentation & Operational Report

**Generated:** {today}
**Script:** generate_docs.py
**Database:** {DB}

---

## 1. Purpose

Technical reference for the Sage Ventures multifamily analytics pipeline.
Covers data model, KPI definitions, report specs and current operational numbers.

Auto-generated from the live database — do not edit manually.
To refresh: `python generate_docs.py`

---

## 2. Portfolio Snapshot — {today}

| Metric | Value |
|---|---|
| Properties | {s['n_props']} |
| Total Units | {s['n_units']:,} |
| Active Tenants | {s['n_tenants']:,} |
| Rent Records (15 months) | {s['n_payments']:,} |
| Maintenance Tickets | {s['n_tickets']:,} |
| Portfolio Avg Occupancy | {s['avg_occ']}% |
| Avg Market Rent | ${s['avg_mkt_rent']:,.0f}/mo |
| Total Monthly Revenue | ${s['monthly_rev']:,.0f} |
| Collection Rate ({s['last_month']}) | {s['coll_rate']}% |
| Open Tickets | {s['open_tickets']} |
| SLA Breaches | {s['sla_breaches']} |

---

## 3. Data Model

### Tables

```
properties
    property_id (PK), name, city, zip, property_type,
    total_units, year_built

units
    unit_id (PK), property_id (FK), unit_number, unit_type,
    sqft, market_rent, floor, status

tenants
    tenant_id (PK), unit_id (FK), full_name, email, phone,
    lease_start, lease_end, monthly_rent, deposit, status

rent_roll
    payment_id (PK), tenant_id (FK), unit_id (FK),
    property_id (FK), period_month, amount_due,
    amount_paid, payment_date, status

maintenance
    ticket_id (PK), unit_id (FK), property_id (FK),
    category, priority, open_date, close_date, cost, status

occupancy_monthly
    occ_id (PK), property_id (FK), period_month,
    total_units, occupied_units, occupancy_rate,
    avg_market_rent, avg_actual_rent
```

### Relationships

```
properties  1 --< units              on property_id
units       1 --< tenants            on unit_id
tenants     1 --< rent_roll          on tenant_id
properties  1 --< maintenance        on property_id
properties  1 --< occupancy_monthly  on property_id
```

---

## 4. KPI Definitions

Single source of truth — if a definition changes here,
update the Power BI DAX measure too.

**Occupancy Rate**
```
occupied_units / total_units * 100
target: 93%
```

**Loss-to-Lease**
```
per unit:  market_rent - monthly_rent
portfolio: SUM(market_rent - monthly_rent) / SUM(market_rent) * 100
flag if > 5% for a property
```

**Collection Rate**
```
SUM(amount_paid) / SUM(amount_due) * 100
target: > 96% monthly
```

**Delinquency Risk Score**
```
score = (delinquent_months * 30)
      + (partial_months * 10)
      + ((100 - payment_reliability_pct) * 0.6)

clipped to 0-100

tiers:
  0-10   low risk
  11-30  medium risk
  31-60  high risk
  61+    critical
```

**SLA Thresholds**
```
emergency : resolve within 1 day
high      : 3 days
medium    : 7 days
low       : 14 days

breach = ticket still open past its threshold
```

**Performance Score**
```
(occupancy_rate * 0.40) + (collection_rate * 0.35) + ((100 - vacancy_rate) * 0.25)

A+ 90-100  A 80-90  B 70-80  C 60-70  D <60
```

---

## 5. Report Specifications

**Rent Roll**
- monthly, run on 1st
- source: rent_roll + tenants + units + properties
- key fields: unit, tenant, market rent, actual rent, loss-to-lease,
  amount due, paid, balance, status
- sent to: CFO, Controller, Regional Managers

**YSR (Yield Summary Report)**
- quarterly
- source: rent_roll grouped by quarter
- key fields: quarter, GPR, collected, uncollected, collection rate
- sent to: CFO, President, VP Asset Management

**Lease Expiration Pipeline**
- weekly
- source: tenants filtered to lease_end within 90 days
- buckets: 0-30, 31-60, 61-90 days
- key fields: property, tenant, unit, lease_end, days left, rent, risk tier
- sent to: Regional Managers, VP Asset Management

**Delinquency Report**
- monthly, run on 5th (after grace period)
- source: rent_roll WHERE status IN (Delinquent, Partial)
- key fields: property, tenant, unit, amount due, paid, balance
- sent to: CFO, Controller, Regional Managers

**Maintenance SLA Report**
- weekly
- source: maintenance WHERE status = Open
- key fields: property, category, priority, days open, sla breach flag
- sent to: Director of Operations, Regional Managers

---

## 6. Property Performance — {today}

{to_md(props)}

---

## 7. Lease Expiration Pipeline

| Bucket | Units | At-Risk Revenue |
|---|---|---|
| 0-30 days | {lp['d30']} | see detail report |
| 31-60 days | {lp['d60']} | see detail report |
| 61-90 days | {lp['d90']} | see detail report |
| total | {lp['d30']+lp['d60']+lp['d90']} | ${lp['at_risk']:,.0f}/mo |

Full detail: `outputs/adhoc/adhoc2_lease_expiration_detail.csv`

---

## 8. Delinquency — Top 10 ({s['last_month']})

{to_md(delq)}

Full report: `outputs/adhoc/adhoc1_delinquency.csv`

---

## 9. Maintenance Cost by Category

{to_md(maint)}

Full report: `outputs/adhoc/adhoc4_maintenance_cost.csv`

---

## 10. Scripts

| Script | what it does | run after |
|---|---|---|
| run_pipeline.py | runs everything | - |
| generate_data.py | builds db + raw csvs | - |
| feature_engineering.py | calculated columns | generate_data.py |
| adhoc_analysis.py | 5 business reports | feature_engineering.py |
| excel_report.py | formatted excel workbook | adhoc_analysis.py |
| visualize.py | 10 charts as png | feature_engineering.py |
| generate_docs.py | this document | generate_data.py |

suggested refresh schedule:
- weekly  → adhoc_analysis.py
- monthly → excel_report.py, generate_docs.py
- on demand → visualize.py

---

## 11. Data Governance Notes

- market rents benchmarked against HUD FMR baltimore-columbia-towson MSA 2024
- occupancy rate enforced between 0-100% in feature layer
- amount_paid validated to never exceed amount_due
- kpi definitions in section 4 are the single source of truth
- any definition change must be updated here AND in the power bi dax measure

---

*auto-generated by generate_docs.py — do not edit manually*
*ajayport@umd.edu*
"""

    with open(OUT, "w") as f:
        f.write(doc)

    conn.close()

    print(f"\ndone. saved to {OUT}")
    print(f"  properties : {s['n_props']}")
    print(f"  units      : {s['n_units']:,}")
    print(f"  tenants    : {s['n_tenants']:,}")
    print(f"  occ rate   : {s['avg_occ']}%")
    print(f"  collection : {s['coll_rate']}%")


if __name__ == "__main__":
    main()
