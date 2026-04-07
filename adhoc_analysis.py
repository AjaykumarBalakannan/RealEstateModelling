"""
adhoc_analysis.py

five on-demand business reports that answer the questions leadership
actually asks on a monday morning. all pull from the sqlite database
via SQL so the logic is transparent and reproducible.

run after generate_data.py and feature_engineering.py.

run:  python adhoc_analysis.py
deps: pip install pandas
"""

import sqlite3
import pandas as pd
import os
from datetime import date

DB  = "data/sage_ventures.db"
OUT = "outputs/adhoc"
os.makedirs(OUT, exist_ok=True)

TODAY = pd.Timestamp(date.today())


def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# ── report 1: delinquency ─────────────────────────────────────────────────────
# "who hasn't paid this month and what's the total exposure?"
# goes to: CFO, Controller

def delinquency_report(conn):
    last_month = pd.read_sql(
        "SELECT MAX(period_month) mo FROM rent_roll", conn
    ).iloc[0]["mo"]

    df = pd.read_sql(f"""
    SELECT
        p.name                                  AS property,
        p.city,
        t.full_name                             AS tenant,
        u.unit_number,
        u.unit_type,
        r.period_month,
        r.amount_due,
        r.amount_paid,
        ROUND(r.amount_due - r.amount_paid, 0)  AS balance_owed,
        r.status,
        t.lease_end
    FROM rent_roll r
    JOIN tenants    t ON r.tenant_id   = t.tenant_id
    JOIN units      u ON r.unit_id     = u.unit_id
    JOIN properties p ON r.property_id = p.property_id
    WHERE r.status IN ('Delinquent','Partial')
      AND r.period_month = '{last_month}'
    ORDER BY balance_owed DESC
    """, conn)

    exposure = df["balance_owed"].sum()
    print(f"  delinquency: {len(df)} accounts, ${exposure:,.0f} total exposure")

    df.to_csv(f"{OUT}/adhoc1_delinquency.csv", index=False)
    return df


# ── report 2: lease expiration pipeline ───────────────────────────────────────
# "how many leases are expiring in the next 90 days and what's the revenue risk?"
# goes to: VP asset management, regional property managers

def lease_expiration(conn):
    # summary by property and bucket
    summary = pd.read_sql("""
    SELECT
        p.name                                        AS property,
        CASE
          WHEN julianday(t.lease_end)-julianday('now') < 0    THEN 'Expired'
          WHEN julianday(t.lease_end)-julianday('now') <= 30  THEN '0-30 Days'
          WHEN julianday(t.lease_end)-julianday('now') <= 60  THEN '31-60 Days'
          ELSE '61-90 Days'
        END                                           AS expiry_bucket,
        COUNT(*)                                      AS units_expiring,
        ROUND(SUM(t.monthly_rent), 0)                 AS revenue_at_risk
    FROM tenants t
    JOIN units      u ON t.unit_id     = u.unit_id
    JOIN properties p ON u.property_id = p.property_id
    WHERE julianday(t.lease_end) - julianday('now') <= 90
      AND t.status = 'Active'
    GROUP BY p.property_id, expiry_bucket
    ORDER BY p.name, expiry_bucket
    """, conn)

    # detailed list for follow-up
    detail = pd.read_sql("""
    SELECT
        p.name                                              AS property,
        p.city,
        t.full_name                                         AS tenant,
        u.unit_number,
        u.unit_type,
        t.monthly_rent,
        t.lease_end,
        CAST(julianday(t.lease_end)-julianday('now') AS INT) AS days_to_expiry,
        CASE
          WHEN julianday(t.lease_end)-julianday('now') < 0    THEN 'Expired'
          WHEN julianday(t.lease_end)-julianday('now') <= 30  THEN '0-30 Days'
          WHEN julianday(t.lease_end)-julianday('now') <= 60  THEN '31-60 Days'
          ELSE '61-90 Days'
        END                                                 AS expiry_bucket,
        t.status
    FROM tenants t
    JOIN units      u ON t.unit_id     = u.unit_id
    JOIN properties p ON u.property_id = p.property_id
    WHERE julianday(t.lease_end) - julianday('now') <= 90
      AND t.status = 'Active'
    ORDER BY days_to_expiry
    """, conn)

    at_risk = detail["monthly_rent"].sum()
    print(f"  lease pipeline: {len(detail)} leases, ${at_risk:,.0f}/mo at risk")

    summary.to_csv(f"{OUT}/adhoc2_lease_expiration.csv",        index=False)
    detail.to_csv( f"{OUT}/adhoc2_lease_expiration_detail.csv", index=False)
    return detail


# ── report 3: loss-to-lease analysis ──────────────────────────────────────────
# "where are we leaving money on the table vs market rent?"
# goes to: CFO, VP asset management

def loss_to_lease(conn):
    df = pd.read_sql("""
    SELECT
        p.name                                          AS property,
        p.city,
        u.unit_type,
        COUNT(u.unit_id)                               AS unit_count,
        ROUND(AVG(u.market_rent), 0)                   AS avg_market_rent,
        ROUND(AVG(t.monthly_rent), 0)                  AS avg_actual_rent,
        ROUND(AVG(u.market_rent - t.monthly_rent), 0)  AS avg_loss_to_lease,
        ROUND(SUM(u.market_rent - t.monthly_rent), 0)  AS total_monthly_gap,
        ROUND(SUM(u.market_rent - t.monthly_rent)*12,0)AS annual_revenue_gap,
        ROUND((AVG(u.market_rent)-AVG(t.monthly_rent))
              /AVG(u.market_rent)*100, 1)               AS loss_pct
    FROM units u
    JOIN properties p ON u.property_id  = p.property_id
    JOIN tenants    t ON u.unit_id      = t.unit_id
                     AND t.status       = 'Active'
    GROUP BY p.property_id, u.unit_type
    ORDER BY annual_revenue_gap DESC
    """, conn)

    total_gap = df["annual_revenue_gap"].sum()
    print(f"  loss-to-lease: ${total_gap:,.0f} annual gap across portfolio")

    df.to_csv(f"{OUT}/adhoc3_loss_to_lease.csv", index=False)
    return df


# ── report 4: maintenance SLA and cost ────────────────────────────────────────
# "which properties are breaching SLA and what's the maintenance spend?"
# goes to: director of operations, regional managers

def maintenance_analysis(conn):
    cost_df = pd.read_sql("""
    SELECT
        p.name                                            AS property,
        p.city,
        m.category,
        m.priority,
        COUNT(m.ticket_id)                               AS total_tickets,
        SUM(CASE WHEN m.status='Open' THEN 1 ELSE 0 END) AS open_tickets,
        ROUND(AVG(
            CASE WHEN m.close_date IS NOT NULL
            THEN julianday(m.close_date)-julianday(m.open_date) END
        ), 1)                                             AS avg_resolution_days,
        ROUND(SUM(m.cost), 0)                             AS total_cost,
        ROUND(AVG(m.cost), 0)                             AS avg_cost_per_ticket
    FROM maintenance m
    JOIN properties p ON m.property_id = p.property_id
    GROUP BY p.property_id, m.category, m.priority
    ORDER BY total_cost DESC
    """, conn)

    # SLA breaches from feature engineering output
    try:
        feat = pd.read_csv("data/feat_maintenance.csv")
        sla_df = feat[feat["sla_breach"]==1].groupby(
            ["name","priority"]
        ).size().reset_index(name="sla_breach_count")
        sla_df.to_csv(f"{OUT}/adhoc4_sla_breaches.csv", index=False)
        print(f"  maintenance: {sla_df['sla_breach_count'].sum()} SLA breaches, ${cost_df['total_cost'].sum():,.0f} total spend")
    except FileNotFoundError:
        # run feature_engineering.py first for SLA detail
        print(f"  maintenance: ${cost_df['total_cost'].sum():,.0f} total spend (run feature_engineering.py for SLA detail)")

    cost_df.to_csv(f"{OUT}/adhoc4_maintenance_cost.csv", index=False)
    return cost_df


# ── report 5: YSR — quarterly revenue trend ───────────────────────────────────
# "how is revenue trending quarter over quarter?"
# YSR = yield summary report — standard multifamily exec report
# goes to: CFO, president

def ysr_revenue_trend(conn):
    # property level
    by_prop = pd.read_sql("""
    SELECT
        p.name                                              AS property,
        CASE
          WHEN CAST(substr(r.period_month,6,2) AS INT) BETWEEN 1 AND 3  THEN 'Q1'
          WHEN CAST(substr(r.period_month,6,2) AS INT) BETWEEN 4 AND 6  THEN 'Q2'
          WHEN CAST(substr(r.period_month,6,2) AS INT) BETWEEN 7 AND 9  THEN 'Q3'
          ELSE 'Q4'
        END || ' ' || substr(r.period_month,1,4)           AS quarter,
        ROUND(SUM(r.amount_due), 0)                        AS gross_potential_rent,
        ROUND(SUM(r.amount_paid), 0)                       AS collected_rent,
        ROUND(SUM(r.amount_due)-SUM(r.amount_paid), 0)     AS uncollected,
        ROUND(SUM(r.amount_paid)*100.0/SUM(r.amount_due),1)AS collection_rate_pct
    FROM rent_roll r
    JOIN properties p ON r.property_id = p.property_id
    GROUP BY p.property_id, quarter
    ORDER BY p.name, quarter
    """, conn)

    # portfolio rollup
    portfolio = by_prop.groupby("quarter").agg(
        gross_potential_rent = ("gross_potential_rent","sum"),
        collected_rent       = ("collected_rent","sum"),
        uncollected          = ("uncollected","sum"),
    ).reset_index()
    portfolio["collection_rate_pct"] = (
        portfolio["collected_rent"] / portfolio["gross_potential_rent"] * 100
    ).round(1)

    print(f"  YSR: {portfolio['quarter'].nunique()} quarters, "
          f"${portfolio['collected_rent'].sum()/1e6:.1f}M total collected")

    # quick print of the trend
    print(f"\n  {'Quarter':<12} {'GPR':>12} {'Collected':>12} {'Rate':>7}")
    print(f"  {'-'*45}")
    for _, row in portfolio.iterrows():
        print(f"  {row['quarter']:<12} ${row['gross_potential_rent']:>10,.0f} "
              f"${row['collected_rent']:>10,.0f} {row['collection_rate_pct']:>6.1f}%")

    by_prop.to_csv(  f"{OUT}/adhoc5_ysr_by_property.csv", index=False)
    portfolio.to_csv(f"{OUT}/adhoc5_ysr_portfolio.csv",   index=False)
    return portfolio


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    conn = connect()

    print("phase 3 — ad hoc analysis")
    print("-" * 30)

    delinquency_report(conn)
    lease_expiration(conn)
    loss_to_lease(conn)
    maintenance_analysis(conn)
    ysr_revenue_trend(conn)

    conn.close()

    print(f"\nall reports → {OUT}/")
    print("done.")


if __name__ == "__main__":
    main()
