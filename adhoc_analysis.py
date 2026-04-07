"""
=============================================================
 Sage Ventures – Multifamily Analytics
 PHASE 3: Ad Hoc Analysis Engine
 Run:    python adhoc_analysis.py
 Needs:  pip install pandas
 Run AFTER Phase 1 & 2
=============================================================
 Simulates the 5 most common "walk-up" business questions
 a CFO, VP Asset Management, or Property Manager would ask.
=============================================================
"""

import sqlite3
import pandas as pd
import os
from datetime import date

DB_PATH    = "data/sage_ventures.db"
OUTPUT_DIR = "outputs/adhoc"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TODAY = pd.Timestamp(date.today())

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ══════════════════════════════════════════════════════════════════════════════
# AD HOC 1: Delinquency Report
# Business Q: "Who hasn't paid this month and what's our exposure?"
# Asked by: CFO, Controller (Rob Wright / Moshe Herzog at Sage)
# ══════════════════════════════════════════════════════════════════════════════
def adhoc_delinquency_report(conn):
    print("\n  [AD HOC 1] Delinquency Report — last available month")
    query = """
    SELECT
        p.name                              AS property,
        p.city,
        t.full_name                         AS tenant,
        u.unit_number,
        u.unit_type,
        r.period_month,
        r.amount_due,
        r.amount_paid,
        ROUND(r.amount_due - r.amount_paid,2) AS balance_owed,
        r.status                            AS payment_status,
        t.lease_end                         AS lease_end
    FROM rent_roll r
    JOIN tenants t    ON r.tenant_id  = t.tenant_id
    JOIN units u      ON r.unit_id    = u.unit_id
    JOIN properties p ON r.property_id= p.property_id
    WHERE r.status IN ('Delinquent','Partial')
      AND r.period_month = (SELECT MAX(period_month) FROM rent_roll)
    ORDER BY balance_owed DESC
    """
    df = pd.read_sql(query, conn)
    total_exposure = df["balance_owed"].sum()
    print(f"     → {len(df)} delinquent/partial accounts | Total exposure: ${total_exposure:,.0f}")
    df.to_csv(f"{OUTPUT_DIR}/adhoc1_delinquency.csv", index=False)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# AD HOC 2: Lease Expiration Pipeline
# Business Q: "What's our renewal risk in the next 90 days?"
# Asked by: VP Asset Management, Regional Property Managers
# ══════════════════════════════════════════════════════════════════════════════
def adhoc_lease_expiration(conn):
    print("\n  [AD HOC 2] Lease Expiration Pipeline — next 90 days")
    query = """
    SELECT
        p.name                                    AS property,
        p.city,
        t.full_name                               AS tenant,
        u.unit_number,
        u.unit_type,
        t.monthly_rent,
        t.lease_end,
        CAST(julianday(t.lease_end) -
             julianday('now') AS INTEGER)         AS days_to_expiry,
        CASE
          WHEN julianday(t.lease_end) - julianday('now') < 0   THEN 'Expired'
          WHEN julianday(t.lease_end) - julianday('now') <= 30 THEN '0-30 Days'
          WHEN julianday(t.lease_end) - julianday('now') <= 60 THEN '31-60 Days'
          ELSE '61-90 Days'
        END                                       AS expiry_bucket,
        t.status                                  AS tenant_status
    FROM tenants t
    JOIN units u      ON t.unit_id      = u.unit_id
    JOIN properties p ON u.property_id  = p.property_id
    WHERE julianday(t.lease_end) - julianday('now') <= 90
      AND t.status = 'Active'
    ORDER BY days_to_expiry ASC
    """
    df = pd.read_sql(query, conn)
    at_risk_rev = df["monthly_rent"].sum()
    print(f"     → {len(df)} leases expiring | At-risk monthly revenue: ${at_risk_rev:,.0f}")
    summary = df.groupby(["property","expiry_bucket"]).agg(
        units_expiring=("tenant","count"),
        revenue_at_risk=("monthly_rent","sum")
    ).reset_index()
    summary.to_csv(f"{OUTPUT_DIR}/adhoc2_lease_expiration.csv", index=False)
    df.to_csv(f"{OUTPUT_DIR}/adhoc2_lease_expiration_detail.csv", index=False)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# AD HOC 3: Loss-to-Lease Analysis
# Business Q: "Where are we leaving money on the table vs market rent?"
# Asked by: VP Asset Management, CFO
# ══════════════════════════════════════════════════════════════════════════════
def adhoc_loss_to_lease(conn):
    print("\n  [AD HOC 3] Loss-to-Lease Analysis — by property & unit type")
    query = """
    SELECT
        p.name                                          AS property,
        p.city,
        u.unit_type,
        COUNT(u.unit_id)                               AS unit_count,
        ROUND(AVG(u.market_rent),0)                    AS avg_market_rent,
        ROUND(AVG(t.monthly_rent),0)                   AS avg_actual_rent,
        ROUND(AVG(u.market_rent - t.monthly_rent),0)   AS avg_loss_to_lease,
        ROUND(SUM(u.market_rent - t.monthly_rent),0)   AS total_monthly_gap,
        ROUND(SUM(u.market_rent - t.monthly_rent)*12,0)AS annual_revenue_gap,
        ROUND((AVG(u.market_rent)-AVG(t.monthly_rent))
              /AVG(u.market_rent)*100,1)               AS loss_pct
    FROM units u
    JOIN properties p ON u.property_id  = p.property_id
    JOIN tenants t    ON u.unit_id      = t.unit_id
    WHERE t.status = 'Active'
    GROUP BY p.property_id, u.unit_type
    ORDER BY annual_revenue_gap DESC
    """
    df = pd.read_sql(query, conn)
    total_annual_gap = df["annual_revenue_gap"].sum()
    print(f"     → Total annual loss-to-lease: ${total_annual_gap:,.0f}")
    df.to_csv(f"{OUTPUT_DIR}/adhoc3_loss_to_lease.csv", index=False)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# AD HOC 4: Maintenance SLA & Cost Analysis
# Business Q: "Which properties are bleeding on maintenance? Any SLA breaches?"
# Asked by: Director of Operations (Roy Zimmerman at Sage)
# ══════════════════════════════════════════════════════════════════════════════
def adhoc_maintenance_analysis(conn):
    print("\n  [AD HOC 4] Maintenance SLA & Cost Analysis")
    query = """
    SELECT
        p.name                                        AS property,
        p.city,
        m.category,
        m.priority,
        COUNT(m.ticket_id)                            AS total_tickets,
        SUM(CASE WHEN m.status='Open' THEN 1 ELSE 0 END) AS open_tickets,
        ROUND(AVG(CASE WHEN m.close_date IS NOT NULL
                  THEN julianday(m.close_date)-julianday(m.open_date)
                  END),1)                             AS avg_resolution_days,
        ROUND(SUM(m.cost),0)                          AS total_cost,
        ROUND(AVG(m.cost),0)                          AS avg_cost_per_ticket
    FROM maintenance m
    JOIN properties p ON m.property_id = p.property_id
    GROUP BY p.property_id, m.category, m.priority
    ORDER BY total_cost DESC
    """
    df = pd.read_sql(query, conn)

    # SLA breaches from feature-engineered file
    try:
        feat_maint = pd.read_csv("data/feat_maintenance.csv")
        sla_breaches = feat_maint[feat_maint["sla_breach"]==1].groupby(
            ["name","priority"]
        ).size().reset_index(name="sla_breach_count")
        sla_breaches.to_csv(f"{OUTPUT_DIR}/adhoc4_sla_breaches.csv", index=False)
        print(f"     → {sla_breaches['sla_breach_count'].sum()} SLA breaches found")
    except FileNotFoundError:
        print("     → Run Phase 2 for SLA breach detail")

    total_cost = df["total_cost"].sum()
    print(f"     → Total maintenance spend: ${total_cost:,.0f}")
    df.to_csv(f"{OUTPUT_DIR}/adhoc4_maintenance_cost.csv", index=False)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# AD HOC 5: YSR — Year-over-Quarter Revenue Trend
# Business Q: "How is revenue trending quarter over quarter?"
# Asked by: CFO, President (Sam Dinovitz at Sage)
# ══════════════════════════════════════════════════════════════════════════════
def adhoc_ysr_revenue_trend(conn):
    print("\n  [AD HOC 5] YSR — Quarterly Revenue Trend (Yield Summary Report)")
    query = """
    SELECT
        p.name                                          AS property,
        CASE
          WHEN substr(r.period_month,6,2) IN ('01','02','03') THEN 'Q1'
          WHEN substr(r.period_month,6,2) IN ('04','05','06') THEN 'Q2'
          WHEN substr(r.period_month,6,2) IN ('07','08','09') THEN 'Q3'
          ELSE 'Q4'
        END || ' ' || substr(r.period_month,1,4)       AS quarter,
        ROUND(SUM(r.amount_due),0)                     AS gross_potential_rent,
        ROUND(SUM(r.amount_paid),0)                    AS collected_rent,
        ROUND(SUM(r.amount_due)-SUM(r.amount_paid),0)  AS uncollected,
        ROUND(SUM(r.amount_paid)*100.0/SUM(r.amount_due),1) AS collection_rate_pct,
        COUNT(DISTINCT r.tenant_id)                    AS active_tenants
    FROM rent_roll r
    JOIN properties p ON r.property_id = p.property_id
    GROUP BY p.property_id, quarter
    ORDER BY p.name, quarter
    """
    df = pd.read_sql(query, conn)

    # Portfolio-level quarterly rollup
    portfolio = df.groupby("quarter").agg(
        gross_potential_rent = ("gross_potential_rent","sum"),
        collected_rent       = ("collected_rent","sum"),
        uncollected          = ("uncollected","sum"),
    ).reset_index()
    portfolio["collection_rate_pct"] = (
        portfolio["collected_rent"] / portfolio["gross_potential_rent"] * 100
    ).round(1)

    print(f"     → {df['quarter'].nunique()} quarters of revenue data across {df['property'].nunique()} properties")
    df.to_csv(f"{OUTPUT_DIR}/adhoc5_ysr_by_property.csv", index=False)
    portfolio.to_csv(f"{OUTPUT_DIR}/adhoc5_ysr_portfolio.csv", index=False)

    print("\n     Portfolio Quarterly Trend:")
    print(f"     {'Quarter':<12} {'GPR':>12} {'Collected':>12} {'Rate':>8}")
    print(f"     {'-'*46}")
    for _, row in portfolio.iterrows():
        print(f"     {row['quarter']:<12} ${row['gross_potential_rent']:>10,.0f} "
              f"${row['collected_rent']:>10,.0f} {row['collection_rate_pct']:>6.1f}%")

    return df


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("\n" + "="*55)
    print("  Sage Ventures — Phase 3: Ad Hoc Analysis Engine")
    print("="*55)

    conn = connect()

    adhoc_delinquency_report(conn)
    adhoc_lease_expiration(conn)
    adhoc_loss_to_lease(conn)
    adhoc_maintenance_analysis(conn)
    adhoc_ysr_revenue_trend(conn)

    conn.close()

    print("\n" + "="*55)
    print("  Phase 3 Complete ✓")
    print(f"  All reports → outputs/adhoc/")
    print("="*55)

if __name__ == "__main__":
    main()
