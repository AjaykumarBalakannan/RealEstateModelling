# Sage Ventures — Multifamily Analytics
## Technical Documentation & Operational Report

**Generated:** April 07, 2026
**Script:** generate_docs.py
**Database:** data/sage_ventures.db

---

## 1. Purpose

Technical reference for the Sage Ventures multifamily analytics pipeline.
Covers data model, KPI definitions, report specs and current operational numbers.

Auto-generated from the live database — do not edit manually.
To refresh: `python generate_docs.py`

---

## 2. Portfolio Snapshot — April 07, 2026

| Metric | Value |
|---|---|
| Properties | 8 |
| Total Units | 2,047 |
| Active Tenants | 1,609 |
| Rent Records (15 months) | 8,239 |
| Maintenance Tickets | 2,514 |
| Portfolio Avg Occupancy | 87.2% |
| Avg Market Rent | $2,105/mo |
| Total Monthly Revenue | $2,737,489 |
| Collection Rate (2025-02) | 96.6% |
| Open Tickets | N/A - run feature_engineering.py |
| SLA Breaches | N/A - run feature_engineering.py |

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

## 6. Property Performance — April 07, 2026

| name                     | city           | property_type      |   total_units |   occupied |   occ_pct |   avg_mkt_rent |   monthly_rev |
|:-------------------------|:---------------|:-------------------|--------------:|-----------:|----------:|---------------:|--------------:|
| Mills Crossing           | Owings Mills   | Townhome/Apartment |           312 |        207 |      66.3 |           2208 |        425322 |
| Fieldside Grande Ph1     | Pikesville     | Luxury Apartment   |           287 |        210 |      73.2 |           2050 |        406493 |
| Cedar Ridge Commons      | Ellicott City  | Garden Apartment   |           310 |        215 |      69.4 |           2019 |        404512 |
| Duvall Westside          | Laurel         | Luxury Apartment   |           287 |        198 |      69   |           2055 |        383926 |
| Riverfront Flats         | Frederick      | Mid-Rise Apartment |           260 |        179 |      68.8 |           1999 |        336387 |
| Avenue Grand             | Baltimore      | Mid-Rise Apartment |           224 |        146 |      65.2 |           1989 |        272909 |
| Townes at Heritage Hills | Glen Burnie    | Townhome           |           198 |        119 |      60.1 |           2415 |        268435 |
| Overlook at Bulle Rock   | Havre de Grace | Condominium        |           180 |        116 |      64.4 |           2195 |        239505 |

---

## 7. Lease Expiration Pipeline

| Bucket | Units | At-Risk Revenue |
|---|---|---|
| 0-30 days | 4 | see detail report |
| 31-60 days | 4 | see detail report |
| 61-90 days | 0 | see detail report |
| total | 8 | $16,138/mo |

Full detail: `outputs/adhoc/adhoc2_lease_expiration_detail.csv`

---

## 8. Delinquency — Top 10 (2025-02)

| property                 | tenant           | unit_type   |   balance_owed | status     |
|:-------------------------|:-----------------|:------------|---------------:|:-----------|
| Townes at Heritage Hills | Stephanie Bolton | 3BR/2BA     |           2744 | Delinquent |
| Mills Crossing           | Tracy Blackwell  | 3BR/2BA     |           2435 | Delinquent |
| Avenue Grand             | Michelle Barrett | 2BR/2BA     |           2074 | Delinquent |
| Mills Crossing           | Jennifer Chen    | 2BR/1BA     |           2010 | Delinquent |
| Cedar Ridge Commons      | Donald Mays      | 1BR/1BA     |           1804 | Delinquent |
| Avenue Grand             | Michael Neal     | 1BR/1BA     |           1733 | Delinquent |
| Mills Crossing           | Steven Huang     | 1BR/1BA     |           1557 | Delinquent |
| Riverfront Flats         | Robert Serrano   | 1BR/1BA     |           1553 | Delinquent |
| Overlook at Bulle Rock   | Emily Potter     | 2BR/2BA     |           1031 | Partial    |
| Avenue Grand             | Patricia Smith   | 2BR/2BA     |            983 | Partial    |

Full report: `outputs/adhoc/adhoc1_delinquency.csv`

---

## 9. Maintenance Cost by Category

| category     |   tickets |   open_tickets |   avg_days_to_close |   total_cost |
|:-------------|----------:|---------------:|--------------------:|-------------:|
| Flooring     |       354 |             63 |                22.3 |       391936 |
| Electrical   |       384 |             95 |                23.1 |       387244 |
| Plumbing     |       368 |             76 |                22.6 |       380263 |
| Pest Control |       355 |             78 |                24.1 |       354734 |
| Appliance    |       342 |             60 |                22.7 |       353303 |
| General      |       360 |             81 |                23.7 |       351465 |
| HVAC         |       351 |             86 |                23.4 |       334002 |

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
