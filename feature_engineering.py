"""
=============================================================
 Sage Ventures – Multifamily Analytics
 PHASE 2: Feature Engineering & Enrichment
 Run:    python feature_engineering.py
 Needs:  pip install pandas numpy
 Run AFTER generate_data.py
=============================================================
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import date
import os

DB_PATH  = "data/sage_ventures.db"
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

TODAY = pd.Timestamp(date.today())

def load_tables(conn):
    properties  = pd.read_sql("SELECT * FROM properties",        conn)
    units       = pd.read_sql("SELECT * FROM units",             conn)
    tenants     = pd.read_sql("SELECT * FROM tenants",           conn)
    rent_roll   = pd.read_sql("SELECT * FROM rent_roll",         conn)
    maintenance = pd.read_sql("SELECT * FROM maintenance",       conn)
    occupancy   = pd.read_sql("SELECT * FROM occupancy_monthly", conn)
    return properties, units, tenants, rent_roll, maintenance, occupancy

# ══════════════════════════════════════════════════════════════════════════════
# FEATURE SET 1 — TENANT-LEVEL FEATURES
# ══════════════════════════════════════════════════════════════════════════════
def engineer_tenant_features(tenants, units, rent_roll):
    print("  [1/5] Engineering tenant features...")

    df = tenants.copy()
    df["lease_start"] = pd.to_datetime(df["lease_start"])
    df["lease_end"]   = pd.to_datetime(df["lease_end"])

    # Lease duration & urgency
    df["lease_duration_days"] = (df["lease_end"] - df["lease_start"]).dt.days
    df["days_to_expiry"]      = (df["lease_end"] - TODAY).dt.days
    df["lease_expired"]       = (df["lease_end"] < TODAY).astype(int)

    # Expiry bucket — mirrors real lease pipeline reports
    def expiry_bucket(days):
        if days < 0:   return "Expired"
        if days <= 30:  return "0-30 Days"
        if days <= 60:  return "31-60 Days"
        if days <= 90:  return "61-90 Days"
        return "90+ Days"
    df["expiry_bucket"] = df["days_to_expiry"].apply(expiry_bucket)

    # Lease term category
    df["lease_term_type"] = df["lease_duration_days"].apply(
        lambda d: "Short-Term (<6mo)" if d<180
             else "Standard (6-12mo)" if d<=365
             else "Long-Term (>12mo)"
    )

    # Merge market rent from units → calculate loss to lease per tenant
    df = df.merge(units[["unit_id","market_rent","unit_type","sqft"]], on="unit_id", how="left")
    df["loss_to_lease"]     = df["market_rent"] - df["monthly_rent"]
    df["loss_to_lease_pct"] = ((df["loss_to_lease"] / df["market_rent"]) * 100).round(2)
    df["concession_flag"]   = (df["loss_to_lease_pct"] > 5).astype(int)

    # Payment behaviour from rent_roll
    rr_summary = rent_roll.groupby("tenant_id").agg(
        total_charges   = ("payment_id",   "count"),
        paid_on_time    = ("status",       lambda x: (x=="Paid").sum()),
        partial_count   = ("status",       lambda x: (x=="Partial").sum()),
        delinquent_count= ("status",       lambda x: (x=="Delinquent").sum()),
        total_due       = ("amount_due",   "sum"),
        total_paid      = ("amount_paid",  "sum"),
    ).reset_index()

    rr_summary["collection_rate"]    = (rr_summary["total_paid"] / rr_summary["total_due"] * 100).round(2)
    rr_summary["payment_reliability"] = (rr_summary["paid_on_time"] / rr_summary["total_charges"] * 100).round(2)

    # Delinquency risk score (0-100, higher = more risk)
    rr_summary["delinquency_risk_score"] = (
        (rr_summary["delinquent_count"] * 30) +
        (rr_summary["partial_count"]    * 10) +
        ((100 - rr_summary["payment_reliability"]) * 0.6)
    ).clip(0, 100).round(1)

    rr_summary["risk_tier"] = pd.cut(
        rr_summary["delinquency_risk_score"],
        bins=[-1, 10, 30, 60, 100],
        labels=["Low Risk","Medium Risk","High Risk","Critical"]
    )

    df = df.merge(rr_summary, on="tenant_id", how="left")
    df.to_csv(f"{DATA_DIR}/feat_tenants.csv", index=False)
    print(f"     → {len(df):,} tenant records enriched with {len(df.columns)} features")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE SET 2 — UNIT-LEVEL FEATURES
# ══════════════════════════════════════════════════════════════════════════════
def engineer_unit_features(units, properties, tenants):
    print("  [2/5] Engineering unit features...")

    df = units.copy()
    df = df.merge(properties[["property_id","name","city","property_type","year_built"]], on="property_id", how="left")

    # Vacancy flag and revenue potential
    df["is_vacant"]            = (df["status"] == "Vacant").astype(int)
    df["annual_market_revenue"]= df["market_rent"] * 12
    df["rent_per_sqft"]        = (df["market_rent"] / df["sqft"]).round(2)

    # Property age & renovation flag
    df["property_age"]   = date.today().year - df["year_built"]
    df["needs_attention"]= (df["property_age"] > 8).astype(int)

    # Unit tier based on rent
    df["rent_tier"] = pd.cut(
        df["market_rent"],
        bins=[0, 1500, 2000, 2500, 9999],
        labels=["Economy","Mid-Range","Premium","Luxury"]
    )

    # Occupied units → merge actual rent
    active_tenants = tenants[tenants["status"]=="Active"][["unit_id","monthly_rent"]]
    df = df.merge(active_tenants, on="unit_id", how="left")
    df["actual_rent"]     = df["monthly_rent"].fillna(0)
    df["loss_to_lease"]   = df["market_rent"] - df["actual_rent"]
    df["occupancy_status"]= df["actual_rent"].apply(lambda x: "Occupied" if x > 0 else "Vacant")

    df.drop(columns=["monthly_rent"], inplace=True)
    df.to_csv(f"{DATA_DIR}/feat_units.csv", index=False)
    print(f"     → {len(df):,} unit records enriched with {len(df.columns)} features")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE SET 3 — MAINTENANCE FEATURES
# ══════════════════════════════════════════════════════════════════════════════
def engineer_maintenance_features(maintenance, properties):
    print("  [3/5] Engineering maintenance features...")

    df = maintenance.copy()
    df["open_date"]  = pd.to_datetime(df["open_date"])
    df["close_date"] = pd.to_datetime(df["close_date"])
    df = df.merge(properties[["property_id","name","city"]], on="property_id", how="left")

    # Resolution time
    df["resolution_days"] = (df["close_date"] - df["open_date"]).dt.days
    df["is_open"]         = (df["status"] == "Open").astype(int)
    df["days_open"]       = df["open_date"].apply(
        lambda d: (TODAY - d).days if pd.notna(d) else 0
    )

    # SLA breach flag (Emergency >1d, High >3d, Medium >7d, Low >14d)
    sla_map = {"Emergency":1,"High":3,"Medium":7,"Low":14}
    df["sla_days"] = df["priority"].map(sla_map)
    df["sla_breach"] = (
        (df["is_open"]==1) & (df["days_open"] > df["sla_days"])
    ).astype(int)

    # Cost tier
    df["cost_tier"] = pd.cut(
        df["cost"],
        bins=[-1,0,250,1000,9999],
        labels=["No Cost","Low","Medium","High"]
    )

    df.to_csv(f"{DATA_DIR}/feat_maintenance.csv", index=False)
    print(f"     → {len(df):,} maintenance tickets enriched with {len(df.columns)} features")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE SET 4 — PROPERTY-LEVEL KPI ROLLUP
# ══════════════════════════════════════════════════════════════════════════════
def engineer_property_kpis(properties, units, tenants, rent_roll, maintenance):
    print("  [4/5] Engineering property-level KPI rollup...")

    # Base
    df = properties.copy()

    # Occupancy
    occ = units.merge(
        tenants[tenants["status"]=="Active"][["unit_id","monthly_rent"]],
        on="unit_id", how="left"
    )
    occ_agg = occ.groupby("property_id").agg(
        total_units     = ("unit_id",      "count"),
        occupied_units  = ("monthly_rent", lambda x: x.notna().sum()),
        avg_market_rent = ("market_rent",  "mean"),
        avg_actual_rent = ("monthly_rent", "mean"),
        total_sqft      = ("sqft",         "sum"),
    ).reset_index()
    occ_agg["occupancy_rate"]    = (occ_agg["occupied_units"] / occ_agg["total_units"] * 100).round(1)
    occ_agg["vacancy_rate"]      = (100 - occ_agg["occupancy_rate"]).round(1)
    occ_agg["loss_to_lease_pct"] = ((occ_agg["avg_market_rent"] - occ_agg["avg_actual_rent"])
                                    / occ_agg["avg_market_rent"] * 100).round(2)

    # Revenue (last full month)
    last_month = rent_roll["period_month"].max()
    rev = rent_roll[rent_roll["period_month"]==last_month].groupby("property_id").agg(
        gross_potential_rent = ("amount_due",  "sum"),
        collected_rent       = ("amount_paid", "sum"),
    ).reset_index()
    rev["collection_rate_pct"] = (rev["collected_rent"] / rev["gross_potential_rent"] * 100).round(1)
    rev["uncollected"]         = (rev["gross_potential_rent"] - rev["collected_rent"]).round(0)

    # Maintenance
    maint_agg = maintenance.groupby("property_id").agg(
        total_tickets    = ("ticket_id", "count"),
        open_tickets     = ("status",    lambda x: (x=="Open").sum()),
        total_maint_cost = ("cost",      "sum"),
        avg_resolution   = ("close_date", lambda x: x.notna().sum()),
    ).reset_index()
    maint_agg["cost_per_unit"] = (maint_agg["total_maint_cost"] / properties.set_index("property_id")["total_units"]).round(0)

    # Merge all
    df = df.merge(occ_agg, on="property_id", how="left")
    df = df.merge(rev,      on="property_id", how="left")
    df = df.merge(maint_agg,on="property_id", how="left")

    # Revenue per unit (NOI proxy)
    df["revenue_per_unit"] = (df["collected_rent"] / df["occupied_units"]).round(0)
    df["annual_revenue"]   = (df["collected_rent"] * 12).round(0)

    # Performance score (0-100 composite)
    df["performance_score"] = (
        (df["occupancy_rate"]      * 0.40) +
        (df["collection_rate_pct"] * 0.35) +
        ((100 - df["vacancy_rate"])* 0.25)
    ).round(1)

    df["performance_grade"] = pd.cut(
        df["performance_score"],
        bins=[0,60,70,80,90,100],
        labels=["D","C","B","A","A+"]
    )

    df.to_csv(f"{DATA_DIR}/feat_property_kpis.csv", index=False)
    print(f"     → {len(df):,} property KPI records with {len(df.columns)} features")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE SET 5 — RENT ROLL ENRICHMENT
# ══════════════════════════════════════════════════════════════════════════════
def engineer_rent_roll_features(rent_roll, tenants, units, properties):
    print("  [5/5] Engineering rent roll features...")

    df = rent_roll.copy()
    df["payment_date"] = pd.to_datetime(df["payment_date"])
    df["period_dt"]    = pd.to_datetime(df["period_month"] + "-01")

    # Days to pay
    df["days_to_pay"] = (df["payment_date"] - df["period_dt"]).dt.days

    # Collection flags
    df["is_paid"]       = (df["status"] == "Paid").astype(int)
    df["is_delinquent"] = (df["status"] == "Delinquent").astype(int)
    df["is_partial"]    = (df["status"] == "Partial").astype(int)
    df["balance_owed"]  = (df["amount_due"] - df["amount_paid"]).round(2)

    # Late fee flag (paid after 5th of month)
    df["late_flag"] = (df["days_to_pay"] > 5).astype(int)

    # Quarter
    df["quarter"] = "Q" + df["period_dt"].dt.quarter.astype(str) + \
                    " " + df["period_dt"].dt.year.astype(str)

    # Merge property info
    df = df.merge(properties[["property_id","name","city"]], on="property_id", how="left")
    df = df.merge(units[["unit_id","unit_type"]], on="unit_id", how="left")

    df.to_csv(f"{DATA_DIR}/feat_rent_roll.csv", index=False)
    print(f"     → {len(df):,} rent roll records enriched with {len(df.columns)} features")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    conn = sqlite3.connect(DB_PATH)
    properties, units, tenants, rent_roll, maintenance, occupancy = load_tables(conn)
    conn.close()

    print("\n" + "="*55)
    print("  Sage Ventures — Phase 2: Feature Engineering")
    print("="*55)

    feat_tenants  = engineer_tenant_features(tenants, units, rent_roll)
    feat_units    = engineer_unit_features(units, properties, tenants)
    feat_maint    = engineer_maintenance_features(maintenance, properties)
    feat_props    = engineer_property_kpis(properties, units, tenants, rent_roll, maintenance)
    feat_rr       = engineer_rent_roll_features(rent_roll, tenants, units, properties)

    print("="*55)
    print("  Phase 2 Complete ✓")
    print("  Engineered CSVs → data/feat_*.csv")
    print("="*55)

    # Quick insight print
    print("\n  📊 Key Insights from Feature Engineering:")
    avg_occ  = feat_props["occupancy_rate"].mean()
    avg_ltl  = feat_props["loss_to_lease_pct"].mean()
    sla_bre  = feat_maint["sla_breach"].sum()
    hi_risk  = feat_tenants[feat_tenants["risk_tier"].isin(["High Risk","Critical"])].shape[0]

    print(f"  Portfolio Avg Occupancy     : {avg_occ:.1f}%")
    print(f"  Portfolio Avg Loss-to-Lease : {avg_ltl:.1f}%")
    print(f"  SLA Breaches (open tickets) : {sla_bre}")
    print(f"  High/Critical Risk Tenants  : {hi_risk}")

if __name__ == "__main__":
    main()
